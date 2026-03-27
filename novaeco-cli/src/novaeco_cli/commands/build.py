import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from rich.console import Console

console = Console()


def register_subcommand(subparsers):
    examples = """Examples:
  # Build everything in the correct dependency order
  novaeco build all

  # Build only the C++ core
  novaeco build core
  
  # Build only the Protobuf API contracts
  novaeco build api

  # Build documentation (all perspectives)
  novaeco build docs

  # Build specific documentation perspective
  novaeco build docs internal
"""
    parser = subparsers.add_parser(
        "build",
        help="Build fractal component artifacts (Core, API, Domain, Service, Client, Docs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    build_subs = parser.add_subparsers(dest="build_command", required=True)

    # Register fractal layers
    build_subs.add_parser("all", help="Build all layers in dependency order")
    build_subs.add_parser("api", help="Compile Protobufs and build API wheel")
    build_subs.add_parser("core", help="Compile C++ engine and build Extension wheel")
    build_subs.add_parser("domain", help="Build Domain logic wheel")
    build_subs.add_parser("service", help="Build Service wiring wheel")
    build_subs.add_parser("client", help="Build Client SDK wheel")

    # Web/Node
    p_web = build_subs.add_parser("web", help="Package Web/Node Projects")
    p_web.add_argument("--build-dir", default="build", help="Directory where npm output is generated")
    p_web.add_argument("--out-dir", default="dist", help="Output directory for the final tarball (Output)")

    # Documentation
    p_docs = build_subs.add_parser("docs", help="Build Sphinx documentation perspectives")
    p_docs.add_argument(
        "perspective",
        nargs="?",
        choices=["all", "public", "partner", "internal"],
        default="all",
        help="Which perspective to build (default: all)",
    )


# --- Utilities ---


def get_service_name():
    """Determines the current repository name dynamically without hardcoded lists."""

    # 1. Try Python's pyproject.toml (PEP-621 standard)
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            for line in f:
                match = re.search(r'^name\s*=\s*"([^"]+)"', line.strip())
                if match:
                    return match.group(1)

    # 2. Try Node's package.json (For web/frontend services)
    if os.path.exists("package.json"):
        import json

        try:
            with open("package.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data:
                    return data["name"]
        except Exception:
            pass

    # 3. Try Git remote origin (Handles C++ only repos and /workspace mounts)
    try:
        res = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=True
        )
        url = res.stdout.strip()
        if url:
            # Extracts 'novaeco-gateway' from 'git@github.com:novaeco-tech/novaeco-gateway.git'
            return url.split("/")[-1].replace(".git", "")
    except Exception:
        pass

    # 4. Final Fallback (Local directory name)
    name = os.path.basename(os.getcwd())
    if name == "workspace":
        console.print(
            "[bold red]❌ Error:[/bold red] Running in a DevContainer (/workspace) but "
            "cannot determine the project name. Missing pyproject.toml, package.json, or Git config."
        )
        sys.exit(1)

    return name


def run_cmd(cmd, cwd=None, env=None):
    """Runs a shell command with error handling."""
    try:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError:
        console.print(f"[bold red]❌ Command Failed:[/bold red] {' '.join(cmd)}")
        sys.exit(1)


# --- Layer Builders ---


def build_api():
    """Compiles Protobufs and builds the API wheel."""
    service_name = get_service_name()
    package_name = f"{service_name.replace('-', '_')}_api"
    api_dir = "api"
    proto_dir = os.path.join(api_dir, "proto", "v1")
    target_src_dir = os.path.join(api_dir, "src", package_name, "v1")

    if not os.path.exists(proto_dir):
        console.print(f"⚠️  No protos found in {proto_dir}. Skipping API build.")
        return

    console.print(f"\n[bold blue]⚙️  Building API Layer ({service_name})...[/bold blue]")

    # 1. Create target directories
    os.makedirs(target_src_dir, exist_ok=True)
    Path(os.path.join(api_dir, "src", package_name, "__init__.py")).touch()
    Path(os.path.join(target_src_dir, "__init__.py")).touch()

    # 2. Compile Protos
    protos = glob.glob(os.path.join(proto_dir, "*.proto"))
    console.print("   [dim]Compiling Protobufs...[/dim]")
    run_cmd(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{os.path.join(api_dir, 'proto', 'v1')}",
            f"--python_out={target_src_dir}",
            f"--grpc_python_out={target_src_dir}",
        ]
        + protos
    )

    # 3. Patch relative imports in generated gRPC code
    console.print("   [dim]Patching relative imports...[/dim]")
    for filepath in glob.glob(os.path.join(target_src_dir, "*_pb2_grpc.py")):
        with open(filepath, "r") as f:
            content = f.read()
        content = re.sub(r"import (\w+_pb2)", r"from . import \1", content)
        with open(filepath, "w") as f:
            f.write(content)

    # 4. Build Wheel
    console.print("   [dim]Packaging API Wheel...[/dim]")
    run_cmd([sys.executable, "-m", "build", api_dir, "--outdir", "dist"])
    console.print("✅ API Layer built successfully.")


def build_core():
    """Builds the C++ Conan library and the Python Extension Wheel."""
    if not os.path.exists("core"):
        console.print("⚠️  No 'core' directory found. Skipping C++ build.")
        return

    console.print("\n[bold blue]🔧 Building C++ Core Layer...[/bold blue]")

    # 1. Conan Setup & Build
    console.print("   [dim]Running Conan install...[/dim]")
    run_cmd(["conan", "profile", "detect", "--force"], cwd="core")
    run_cmd(
        ["conan", "install", ".", "--build=missing", "-s", "compiler.cppstd=20", "-s", "build_type=Release"], cwd="core"
    )

    # 2. Package Python Wheel (Scikit-Build-Core)
    console.print("   [dim]Packaging Core Python Wheel...[/dim]")
    # We pass BUILD_TESTS=OFF so the production wheel doesn't require GTest
    env = os.environ.copy()
    toolchain = os.path.abspath("core/build/Release/generators/conan_toolchain.cmake")
    run_cmd(
        [
            sys.executable,
            "-m",
            "build",
            "core",
            "--outdir",
            "dist",
            "-Ccmake.define.BUILD_TESTS=OFF",
            f"-Ccmake.define.CMAKE_TOOLCHAIN_FILE={toolchain}",
        ],
        env=env,
    )

    console.print("✅ Core Layer built successfully.")


def build_python_layer(layer_name):
    """Builds standard Python wheels for Domain, Service, or Client."""
    if not os.path.exists(layer_name):
        console.print(f"⚠️  Directory '{layer_name}' not found. Skipping.")
        return

    console.print(f"\n[bold blue]📦 Building {layer_name.capitalize()} Layer...[/bold blue]")
    run_cmd([sys.executable, "-m", "build", layer_name, "--outdir", "dist"])
    console.print(f"✅ {layer_name.capitalize()} Layer built successfully.")


def build_web(args):
    """Builds Node.js / React frontends."""
    if not shutil.which("npm"):
        console.print("[bold red]❌ Error:[/bold red] 'npm' not found. Run this in a Node container.")
        sys.exit(1)

    console.print("\n[bold blue]🌍 Building Web Project...[/bold blue]")
    run_cmd(["npm", "ci"])
    run_cmd(["npm", "run", "build"])

    dist_dir = args.out_dir 
    os.makedirs(dist_dir, exist_ok=True)
    tar_name = f"{get_service_name()}.tar.gz"
    tar_path = os.path.join(dist_dir, tar_name)

    console.print(f"   [dim]Packaging {args.build_dir} to {tar_name}...[/dim]")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(args.build_dir, arcname=".")

    console.print("✅ Web Layer packaged successfully.")


def build_docs(perspective):
    """Builds Sphinx documentation for specified perspectives."""
    if not os.path.exists("docs/source"):
        console.print("⚠️  No 'docs/source' directory found. Skipping.")
        return

    perspectives = ["public", "partner", "internal"] if perspective == "all" else [perspective]

    for p in perspectives:
        console.print(f"\n[bold blue]📚 Building Docs ({p.capitalize()} Perspective)...[/bold blue]")

        # Ensure target directory exists
        os.makedirs(f"docs/build/{p}", exist_ok=True)

        cmd = [
            "sphinx-build",
            "-W",
            "--keep-going",  # Treat warnings as errors, but finish the build to show all errors
            "-b",
            "html",  # Build HTML
            "-t",
            p,  # Inject the perspective tag (e.g., -t public)
            "docs/source",
            f"docs/build/{p}",
        ]
        run_cmd(cmd)

    console.print("✅ Documentation built successfully in docs/build/")


def execute(args):
    # Ensure dist folder exists and is clean-ish
    os.makedirs("dist", exist_ok=True)

    cmd = args.build_command

    if cmd == "all":
        # Strict order mandated by Fractal Architecture dependencies
        build_api()
        build_core()
        build_python_layer("client")
        build_python_layer("domain")
        build_python_layer("service")
        console.print("\n[bold green]🎉 All Fractal Layers built successfully! Check the ./dist folder.[/bold green]")
    elif cmd == "api":
        build_api()
    elif cmd == "core":
        build_core()
    elif cmd in ["domain", "service", "client"]:
        build_python_layer(cmd)
    elif cmd == "web":
        build_web(args)
    elif cmd == "docs":
        build_docs(args.perspective)
