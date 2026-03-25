import argparse
import glob
import os
import shutil
import subprocess
import sys

from rich.console import Console

console = Console()


def register_subcommand(subparsers):
    examples = """Examples:
  # Clean all workspace build artifacts, test caches, and dist folders
  novaeco clean all

  # Clean only the C++ build artifacts
  novaeco clean core
  
  # Clean all artifacts AND purge the system pip/conan caches
  novaeco clean all --caches
"""
    parser = subparsers.add_parser(
        "clean",
        help="Remove build artifacts, test caches, and generated files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    parser.add_argument(
        "target",
        choices=["all", "api", "core", "python", "docs", "tests", "web"],
        help="The specific component or layer to clean",
    )

    parser.add_argument(
        "--caches", action="store_true", help="Aggressively purge global system caches (Pip, Conan, NPM)"
    )


def remove_path(path: str):
    """Safely removes a file or directory, printing the action."""
    if os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            console.print(f"   [red]🗑️ Deleted:[/red] {path}")
        except Exception as e:
            console.print(f"   [yellow]⚠️ Failed to delete {path}: {e}[/yellow]")


def remove_glob(pattern: str, recursive: bool = False):
    """Removes files/directories matching a glob pattern."""
    for path in glob.glob(pattern, recursive=recursive):
        remove_path(path)


# --- Cleanup Routines ---


def clean_api():
    console.print("\n[bold blue]🧹 Cleaning API Layer...[/bold blue]")
    remove_path("api/src")  # Generated Protobufs
    remove_path("api/build")
    remove_glob("api/*.egg-info")


def clean_core():
    console.print("\n[bold blue]🧹 Cleaning C++ Core Layer...[/bold blue]")
    remove_path("core/build")
    remove_path("core/CMakeUserPresets.json")
    remove_path("_skbuild")  # scikit-build-core temp dir
    remove_glob("core/*.so")  # Compiled Python extensions
    remove_glob("core/*.dylib")
    remove_glob("*.so")  # Catch-all for extensions built at root


def clean_python():
    console.print("\n[bold blue]🧹 Cleaning Python Layers (Domain, Service, Client)...[/bold blue]")
    for layer in ["domain", "service", "client"]:
        remove_path(f"{layer}/build")

    # Catch root level python artifacts AND recursively find any deeply nested
    # artifacts (like novaeco-cli/src/*.egg-info)
    remove_path("build")
    remove_glob("**/*.egg-info", recursive=True)
    remove_glob("**/__pycache__", recursive=True)
    remove_glob("**/*.pyc", recursive=True)


def clean_docs():
    console.print("\n[bold blue]🧹 Cleaning Documentation...[/bold blue]")
    remove_path("docs/build")
    remove_path("docs/source/reports/_generated")

    # NOTE: We no longer blanket-delete docs/source/modules/*/
    # to protect statically tracked placeholders like kernel_placeholder.

    # Root level report files
    for report in [
        "bandit_report.json",
        "benchmark_results.txt",
        "coverage_summary.txt",
        "coverage.xml",
        "nosetests.xml",
    ]:
        remove_path(report)


def clean_tests():
    console.print("\n[bold blue]🧹 Cleaning Test Caches...[/bold blue]")
    # Use recursive globs so it catches caches inside sub-folders like novaeco-cli/
    remove_glob("**/.pytest_cache", recursive=True)
    remove_glob("**/.mypy_cache", recursive=True)
    remove_glob("**/.ruff_cache", recursive=True)
    remove_path(".coverage")
    remove_glob(".coverage.*")
    remove_path("htmlcov")


def clean_web():
    console.print("\n[bold blue]🧹 Cleaning Web/Node Layer...[/bold blue]")
    remove_path("node_modules")
    remove_path(".next")
    remove_path("build")
    remove_glob("*.log")


def clean_caches():
    console.print("\n[bold magenta]🔥 Purging System Caches...[/bold magenta]")

    # Pip Cache
    try:
        subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=True, stdout=subprocess.DEVNULL)
        console.print("   [red]🗑️ Purged:[/red] Pip Cache")
    except Exception:
        console.print("   [yellow]⚠️ Failed to purge Pip cache.[/yellow]")

    # Conan Cache
    try:
        # Conan 2 command to clear downloaded packages and build folders
        subprocess.run(["conan", "cache", "clean", "*", "--build", "--download"], check=True, stdout=subprocess.DEVNULL)
        console.print("   [red]🗑️ Purged:[/red] Conan Cache")
    except Exception:
        console.print("   [yellow]⚠️ Failed to purge Conan cache.[/yellow]")


def execute(args):
    target = args.target

    if target in ["api", "all"]:
        clean_api()
    if target in ["core", "all"]:
        clean_core()
    if target in ["python", "all"]:
        clean_python()
    if target in ["docs", "all"]:
        clean_docs()
    if target in ["tests", "all"]:
        clean_tests()
    if target in ["web", "all"]:
        clean_web()

    if target == "all":
        console.print("\n[bold blue]🧹 Cleaning Release Artifacts...[/bold blue]")
        remove_path("dist")
        remove_path("dist_test")
        remove_glob("*.whl")
        remove_glob("*.tar.gz")

    if args.caches:
        clean_caches()

    console.print("\n[bold green]✨ Workspace is clean![/bold green]")
