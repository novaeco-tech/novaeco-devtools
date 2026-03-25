import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from typing import Optional

import requests
from rich.console import Console

console = Console()
GITHUB_ORG = "novaeco-tech"


def register_subcommand(subparsers):
    examples = """Examples:
  # Auto-discover and install all upstream dependencies from pyproject.toml / conanfile.py
  novaeco deps sync
  
  # Explicitly install a specific component's latest release
  novaeco deps install novaeco-auth
  
  # Explicitly install a specific version
  novaeco deps install novaeco-auth --version v0.1.0
"""
    parser = subparsers.add_parser(
        "deps",
        help="Manage ecosystem dependencies (Wheels & Conan packages)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    subs = parser.add_subparsers(dest="deps_command", required=True)

    # --- Sync Command ---
    subs.add_parser("sync", help="Auto-discover and install internal dependencies")

    # --- Install Command ---
    p_install = subs.add_parser("install", help="Explicitly install a component")
    p_install.add_argument("component", help="Component name (e.g., novaeco-auth)")
    p_install.add_argument("--version", help="Specific tag (e.g., v0.1.0). Defaults to latest.", default=None)


def get_github_token():
    """Retrieves the GH token from Env or Local CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        console.print("[bold red]❌ Error:[/bold red] Could not find GITHUB_TOKEN and 'gh auth token' failed.")
        sys.exit(1)


def get_current_repo_name() -> str:
    """Determines the current repository name by parsing the root pyproject.toml."""
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            for line in f:
                match = re.search(r'^name\s*=\s*"([^"]+)"', line.strip())
                if match:
                    return match.group(1)

    # Fallback if no pyproject.toml exists at root
    name = os.path.basename(os.getcwd())
    if name in ["gateway", "auth", "broker", "risk"]:
        return f"novaeco-{name}"
    return name


def get_repo_name(package_name: str) -> str:
    """Maps a sub-package (novaeco-auth-client) to its parent repo (novaeco-auth)."""
    return re.sub(r"-(client|api|domain|core|service)$", "", package_name)


def download_asset(url: str, dest_path: str, token: str):
    """Downloads a binary asset from GitHub."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/octet-stream"}
    with requests.get(url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def execute_install(component: str, version: Optional[str] = None):
    """Fetches and installs wheels and conan packages for a component."""
    token = get_github_token()

    # Determine API Endpoint
    if version:
        api_url = f"https://api.github.com/repos/{GITHUB_ORG}/{component}/releases/tags/{version}"
    else:
        api_url = f"https://api.github.com/repos/{GITHUB_ORG}/{component}/releases/latest"

    console.print(f"\n🔍 Fetching release data for [bold cyan]{component}[/bold cyan]...")

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 404:
        console.print(f"[bold red]❌ Release not found for {component}.[/bold red]")
        sys.exit(1)
    response.raise_for_status()

    release_data = response.json()
    tag_name = release_data["tag_name"]
    assets = release_data.get("assets", [])

    console.print(f"📦 Found Release: [bold green]{tag_name}[/bold green] ({len(assets)} assets)")

    # Use tempfile instead of hardcoded /tmp
    import tempfile

    tmp_dir = os.path.join(tempfile.gettempdir(), f"novaeco_deps_{component}_{tag_name}")
    os.makedirs(tmp_dir, exist_ok=True)

    wheels = []
    conan_tarball = None

    # Filter Assets
    for asset in assets:
        name = asset["name"]
        if name.endswith(".whl"):
            wheels.append(asset)
        elif name.endswith("-conan.tar.gz"):
            conan_tarball = asset

    # --- 1. Install Conan (C++) ---
    if conan_tarball:
        console.print(f"   ⬇️  Downloading C++ Core: {conan_tarball['name']}...")
        tar_path = os.path.join(tmp_dir, conan_tarball["name"])
        download_asset(conan_tarball["url"], tar_path, token)

        console.print(f"   🔧 Restoring {conan_tarball['name']} to local Conan cache...")
        try:
            # Let Conan 2 handle the precise extraction and database indexing
            subprocess.run(["conan", "cache", "restore", tar_path], check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]❌ Failed to restore Conan package:[/bold red] {e}")
            sys.exit(1)
    else:
        console.print("   ℹ️  No Conan artifacts found. Skipping C++ core.")

    # --- 2. Install Wheels (Python) ---
    if wheels:
        for wheel in wheels:
            console.print(f"   ⬇️  Downloading Python SDK: {wheel['name']}...")
            wheel_path = os.path.join(tmp_dir, wheel["name"])
            download_asset(wheel["url"], wheel_path, token)

            console.print(f"   🐍 pip install {wheel['name']}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", wheel_path],
                check=True,
                stdout=subprocess.DEVNULL,
            )
    else:
        console.print("   ℹ️  No Wheel artifacts found. Skipping Python SDKs.")

    # Cleanup
    shutil.rmtree(tmp_dir)
    console.print(f"✅ Successfully installed [bold cyan]{component}[/bold cyan]!")


def execute_sync():
    """Scans local project to discover internal dependencies and installs them."""
    console.print("\n[bold blue]🔄 Scanning workspace for internal dependencies...[/bold blue]")

    current_repo = get_current_repo_name()
    deps_to_install = {}

    # 1. Parse Python files (pyproject.toml)
    for toml_file in glob.glob("**/pyproject.toml", recursive=True):
        if "novaeco-devtools" in toml_file:
            continue  # Skip self

        with open(toml_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip commented lines!
                if line.startswith("#"):
                    continue

                # Looks for "novaeco-auth-client>=0.1.0" or ==0.1.0
                matches = re.findall(r'"(novaeco-[a-zA-Z0-9-]+)[>=~^]+([0-9\.]+)"', line)
                for pkg_name, version in matches:
                    repo_name = get_repo_name(pkg_name)
                    # SELF-AWARENESS: Skip the current repository
                    if repo_name != current_repo:
                        deps_to_install[repo_name] = f"v{version}"

    # 2. Parse C++ files (core/conanfile.py)
    if os.path.exists("core/conanfile.py"):
        with open("core/conanfile.py", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip commented lines!
                if line.startswith("#"):
                    continue

                # Looks for self.requires("novaeco-risk-core/0.1.0")
                matches = re.findall(r'self\.requires\("([^/]+)/([^\"]+)"\)', line)
                for pkg_name, version in matches:
                    if pkg_name.startswith("novaeco-"):
                        repo_name = get_repo_name(pkg_name)
                        # SELF-AWARENESS: Skip the current repository
                        if repo_name != current_repo:
                            deps_to_install[repo_name] = f"v{version}"

    if not deps_to_install:
        console.print("✅ No internal upstream dependencies found. You're good to go!")
        return

    # 3. Execute Installations
    console.print(f"📋 Found {len(deps_to_install)} upstream dependencies to sync:")
    for repo, ver in deps_to_install.items():
        console.print(f"   - {repo} ({ver})")

    for repo, ver in deps_to_install.items():
        execute_install(repo, ver)


def execute(args):
    if args.deps_command == "sync":
        execute_sync()
    elif args.deps_command == "install":
        execute_install(args.component, args.version)
