import os
import shutil
import tarfile

import requests

# Configuration constants
GITHUB_ORG = "novaeco-tech"
# Map 'short names' in manifest to 'repo names' if they differ.
# If they are the same (e.g. 'novaeco-broker' -> 'novaeco-broker'), this can be simple.
REPO_MAP = {
    "broker": "novaeco-broker",
    "market": "novaeco-market-model",
    "risk": "novaeco-risk",
    # Add other mappings here
}


def register_subcommand(subparsers):
    parser = subparsers.add_parser("docs", help="Documentation management")
    docs_subs = parser.add_subparsers(dest="docs_command", required=True)

    hydrate = docs_subs.add_parser("hydrate", help="Fetch and unpack service documentation")
    hydrate.add_argument("--output", default="docs/source/modules", help="Target directory for modules")
    hydrate.add_argument("--manifest", default="versions.txt", help="Path to version manifest")
    hydrate.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub PAT for private repos")


def parse_manifest(manifest_path):
    """
    Parses a simple key-value file:
    broker: v1.2.0
    risk: v0.1.0
    """
    modules = {}
    if not os.path.exists(manifest_path):
        print(f"⚠️  Manifest not found at {manifest_path}. Skipping hydration.")
        return modules

    with open(manifest_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, version = line.split(":")
                modules[key.strip()] = version.strip()
    return modules


def download_artifact(repo_name, version, token, dest_dir):
    """
    Constructs URL based on:
    https://github.com/novaeco-tech/{repo}/releases/download/{repo}-docs-{version}/docs.tar.gz
    """
    # 1. Construct Tag Name
    tag_name = f"{repo_name}-docs-{version}"

    # 2. Construct Asset URL (GitHub Releases standard download path)
    filename = "docs.tar.gz"
    url = f"https://github.com/{GITHUB_ORG}/{repo_name}/releases/download/{tag_name}/{filename}"

    print(f"   ⬇️  Fetching {repo_name} @ {tag_name}...")

    headers = {"Accept": "application/octet-stream"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            tar_path = os.path.join(dest_dir, f"{repo_name}.tar.gz")
            with open(tar_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return tar_path
    except requests.exceptions.HTTPError as e:
        print(f"      ❌ HTTP Error: {e} (URL: {url})")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def execute_hydrate(args):
    print(f"🌊 Hydrating documentation from manifest: {args.manifest}")

    # 1. Clean Output Directory (preserve index.rst)
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    for item in os.listdir(args.output):
        if item == "index.rst":
            continue
        path = os.path.join(args.output, item)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # 2. Parse Versions
    modules = parse_manifest(args.manifest)

    # 3. Process Each Module
    for short_name, version in modules.items():
        repo_name = REPO_MAP.get(short_name, short_name)

        # Create a specific folder for this module (e.g., docs/source/modules/broker)
        module_dir = os.path.join(args.output, short_name)
        os.makedirs(module_dir, exist_ok=True)

        # Download
        tar_path = download_artifact(repo_name, version, args.token, module_dir)

        # Extract
        if tar_path:
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    # Security: Sanitize members to prevent Zip Slip
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory

                    safe_members = []
                    for member in tar.getmembers():
                        member_path = os.path.join(module_dir, member.name)
                        if not is_within_directory(module_dir, member_path):
                            print(f"      ⚠️  Skipping suspicious file: {member.name}")
                            continue
                        safe_members.append(member)

                    tar.extractall(path=module_dir, members=safe_members)  # nosec B202

                print(f"      ✅ Extracted to {module_dir}")
                os.remove(tar_path)  # Cleanup

            except Exception as e:
                print(f"      ❌ Extraction Failed: {e}")
        else:
            # Create placeholder if download failed (to prevent Sphinx build error)
            with open(os.path.join(module_dir, "index.rst"), "w") as f:
                f.write(
                    f"{short_name}\n{'='*len(short_name)}\n\n"
                    f".. warning::\n   Failed to download docs for ``{repo_name}`` ({version})."
                )

    print("✨ Hydration complete.")


def execute(args):
    if args.docs_command == "hydrate":
        execute_hydrate(args)
