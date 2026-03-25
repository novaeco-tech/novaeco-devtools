import argparse
import os
import re
import sys

from rich.console import Console

console = Console()

# Define the files and regex patterns used to find and replace the version
# Format: (File Path, Regex Match Pattern, Regex Replacement Template)
TARGETS = [
    # --- DevTools ---
    ("novaeco-cli/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    (
        ".github/workflows/shared-component-lint.yml",
        r"(image: ghcr\.io/novaeco-tech/novaeco-dev-unified:v)[0-9\.]+",
        r"\g<1>{}",
    ),
    (
        ".github/workflows/shared-component-lint.yml",
        r"(uses: novaeco-tech/novaeco-devtools/\.github/actions/setup-novaeco@v)[0-9\.]+",
        r"\g<1>{}",
    ),
    # Python Layers
    ("pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("api/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("client/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("core/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("domain/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("service/pyproject.toml", r'^(version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    # C++ Core Layer
    ("core/CMakeLists.txt", r"(project\s*\(.*?VERSION\s+)[0-9\.]+", r"\g<1>{}"),
    ("core/conanfile.py", r'^(\s*version\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    # Documentation & Node Frontends
    ("docs/conf.py", r'^(\s*release\s*=\s*")[^"]+(")', r"\g<1>{}\g<2>"),
    ("package.json", r'^(\s*"version"\s*:\s*")[^"]+(")', r"\g<1>{}\g<2>"),
]


def register_subcommand(subparsers):
    examples = """Examples:
  # Bump the patch version (e.g., 0.1.0 -> 0.1.1) across all files
  novaeco bump patch

  # Bump the minor version (e.g., 0.1.1 -> 0.2.0)
  novaeco bump minor
  
  # Set a specific exact version
  novaeco bump 2.0.0
"""
    parser = subparsers.add_parser(
        "bump",
        help="Bump the semantic version across all configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    parser.add_argument("increment", help="major, minor, patch, or an explicit version string (e.g. 1.2.3)")


def get_current_version():
    """Reads the root pyproject.toml as the Single Source of Truth."""
    if not os.path.exists("pyproject.toml"):
        console.print("[bold red]❌ Error:[/bold red] pyproject.toml not found in the root directory.")
        sys.exit(1)

    with open("pyproject.toml", "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r'^version\s*=\s*"([^"]+)"', line.strip())
            if match:
                return match.group(1)

    console.print("[bold red]❌ Error:[/bold red] Could not find version string in root pyproject.toml.")
    sys.exit(1)


def compute_new_version(current, increment):
    # If the user passed an exact version like "1.2.3", just use it
    if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", increment):
        return increment

    try:
        major, minor, patch = map(int, current.split("."))
    except ValueError:
        console.print(f"[bold red]❌ Error:[/bold red] Current version '{current}' is not a valid SemVer (X.Y.Z).")
        sys.exit(1)

    if increment == "major":
        return f"{major + 1}.0.0"
    elif increment == "minor":
        return f"{major}.{minor + 1}.0"
    elif increment == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        console.print(f"[bold red]❌ Error:[/bold red] Invalid increment '{increment}'. \
                      Use major, minor, patch, or an explicit version.")
        sys.exit(1)


def execute(args):
    current_version = get_current_version()
    new_version = compute_new_version(current_version, args.increment)

    console.print(f"\n[bold blue]🚀 Bumping Version: {current_version} -> {new_version}[/bold blue]\n")

    files_updated = 0
    for filepath, regex, repl in TARGETS:
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Execute the regex replacement
        new_content, count = re.subn(regex, repl.format(new_version), content, flags=re.MULTILINE)

        if count > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            console.print(f"   [green]✅ Updated:[/green] {filepath}")
            files_updated += 1

    if files_updated == 0:
        console.print("[yellow]⚠️  No files were updated. Make sure you are in the repository root.[/yellow]")
    else:
        console.print(f"\n[bold green]✨ Successfully bumped {files_updated} files to {new_version}![/bold green]")
