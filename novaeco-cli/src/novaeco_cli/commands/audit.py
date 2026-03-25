import glob
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

# --- Regex Patterns for Traceability ---
# Matches: :id: REQ_GATEWAY_FUNCTIONAL_0001 or :id: NEED_DATA_0001
REQ_DEF_PATTERN = re.compile(r":id:\s*([A-Z]+_[A-Z_]+_\d{4})")

# Matches: @pytest.mark.requirement("REQ_ID") OR @requirement("REQ_ID")
PY_TEST_VERIFY_PATTERN = re.compile(r'@(?:pytest\.mark\.)?requirement\(\s*["\']([A-Z]+_[A-Z_]+_\d{4})["\']\s*\)')

# Matches: // REQ_KERNEL_PERFORMANCE_0001 or // NEED_DATA_0001
CPP_TEST_VERIFY_PATTERN = re.compile(r"//\s*([A-Z]+_[A-Z_]+_\d{4})")

# Matches Gherkin tags: @USECASE_QA_0001
FEATURE_TEST_VERIFY_PATTERN = re.compile(r'@([A-Z]+_[A-Z_]+_\d{4})')


def register_subcommand(subparsers):
    parser = subparsers.add_parser("audit", help="Autonomous Governance tools for structure and traceability")
    audit_subs = parser.add_subparsers(dest="audit_command", required=True)

    # Command 1: Structure & Drift
    p_structure = audit_subs.add_parser("structure", help="Detect file structure and content drifting")
    p_structure.add_argument("target", nargs="?", default=".", help="Directory to check")

    # Command 2: Traceability
    p_trace = audit_subs.add_parser("traceability", help="V-Model Decomposition and Traceability")
    p_trace.add_argument("target", nargs="?", default=".", help="Directory to check")
    p_trace.add_argument("--global", action="store_true", dest="is_global", help="Run in Global L1-L5 mode (QA Repo)")


# ==============================================================================
# 1. Structural & Content Drift Detection
# ==============================================================================


def load_schema(path):
    """Attempts to load the schema locally, falls back to the GitHub API for DevContainers."""
    # 1. Try Local (Works on Host Machine)
    local_schema_path = os.path.join(
        path, "..", "novaeco", "docs", "source", "architecture", "templates", "component-schema.yaml"
    )
    if os.path.exists(local_schema_path):
        with open(local_schema_path, "r") as f:
            return yaml.safe_load(f)

    # 2. Try GitHub API (Works in DevContainers & CI)
    console.print("[dim]   Schema not found locally. Fetching from remote (novaeco-tech/novaeco)...[/dim]")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            console.print("[bold red]❌ Error:[/bold red] GITHUB_TOKEN not found. Required to fetch private schema.")
            sys.exit(1)

    # Use the GitHub API raw media type to get the file contents
    url = (
        "https://api.github.com/repos/novaeco-tech/novaeco/contents/docs/source/architecture/templates/component-schema.yaml"
    )
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3.raw"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return yaml.safe_load(resp.text)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] Failed to fetch schema from GitHub: {e}")
        sys.exit(1)


def audit_structure(path):
    path = os.path.abspath(path)
    console.print(f"\n[bold blue]🔍 Auditing Structure & Drift ({os.path.basename(path)})...[/bold blue]")

    # Dynamically load the schema
    schema = load_schema(path)

    failed = False

    # A. Check Directories
    console.print("[bold]1. Checking Directory Structure...[/bold]")
    for dir_req in schema["directories"]["required"]:
        target_dir = os.path.join(path, dir_req)
        if not os.path.exists(target_dir):
            console.print(f"   [red]❌ Missing Directory:[/red] {dir_req}")
            failed = True

    # B. Check Files
    console.print("\n[bold]2. Checking Required Files...[/bold]")
    for file_req in schema["files"]["required"]:
        target_file = os.path.join(path, file_req)
        if not os.path.exists(target_file):
            console.print(f"   [red]❌ Missing File:[/red] {file_req}")
            failed = True

    # C. Content Drift (Check if workflows match DevTools standards)
    console.print("\n[bold]3. Checking Content Drift (Caller Workflows)...[/bold]")
    for rule in schema.get("content_rules", []):
        target_file = os.path.join(path, rule["path"])
        if not os.path.exists(target_file):
            console.print(f"   [red]❌ Missing Workflow:[/red] {rule['path']}")
            failed = True
            continue

        with open(target_file, "r") as f:
            content = f.read()
            if rule["must_contain"] not in content:
                console.print(
                    f"   [red]❌ Content Drift Detected in {rule['path']}:[/red] "
                    f"       Does not use standard DevTools caller workflow."
                )
                failed = True
            else:
                console.print(f"   [green]✅ Content OK:[/green] {rule['path']}")

    if failed:
        console.print("\n[bold red]🛑 Structural Audit Failed. Component has drifted from Golden Schema.[/bold red]")
        sys.exit(1)
    else:
        console.print("\n[bold green]✨ Component Structure complies with ADR_KERNEL_0014.[/bold green]")


# ==============================================================================
# 2. V-Model Traceability & Implicit Traceability
# ==============================================================================


def audit_traceability(path, is_global=False):
    path = os.path.abspath(path)
    mode = "GLOBAL (L1-L5)" if is_global else "LOCAL (L3-L5)"
    console.print(f"\n[bold blue]🔍 Auditing V-Model Traceability [{mode}]...[/bold blue]")

    definitions = {}
    verifications = defaultdict(list)

    # 1. Scan for Definitions (.rst files)
    doc_pattern = os.path.join(path, "**", "*.rst") if not is_global else os.path.join(path, "..", "**", "*.rst")
    for file_path in glob.glob(doc_pattern, recursive=True):
        if "_generated" in file_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = REQ_DEF_PATTERN.search(line)
                    if match:
                        definitions[match.group(1)] = os.path.relpath(file_path, path)
        except Exception:
            continue

    # 2. Scan for Verifications (Python, C++, and Gherkin Features)
    code_pattern = os.path.join(path, "**", "*.*") if not is_global else os.path.join(path, "..", "**", "*.*")
    for file_path in glob.glob(code_pattern, recursive=True):
        if not (file_path.endswith(".py") or file_path.endswith(".cpp") or file_path.endswith(".hpp") or file_path.endswith(".feature")):
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Find Python tests
                if file_path.endswith(".py"):
                    for req_id in PY_TEST_VERIFY_PATTERN.findall(content):
                        verifications[req_id].append(os.path.relpath(file_path, path))
                
                # Find C++ tests/logic
                if file_path.endswith(".cpp") or file_path.endswith(".hpp"):
                    for req_id in CPP_TEST_VERIFY_PATTERN.findall(content):
                        verifications[req_id].append(os.path.relpath(file_path, path))
                        
                # Find BDD Feature tags
                if file_path.endswith(".feature"):
                    for req_id in FEATURE_TEST_VERIFY_PATTERN.findall(content):
                        verifications[req_id].append(os.path.relpath(file_path, path))
                        
        except Exception:
            continue

    # 3. Render the Master Traceability Matrix
    table = Table(title="Traceability Matrix")
    table.add_column("Requirement ID", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Verified By", style="green")

    orphaned_reqs = 0
    dangling_tests = 0

    for req_id in sorted(definitions.keys()):
        tests = verifications.get(req_id, [])
        if tests:
            table.add_row(req_id, "[bold green]VERIFIED[/bold green]", f"{len(tests)} references")
        else:
            table.add_row(req_id, "[bold red]ORPHANED[/bold red]", "-")
            orphaned_reqs += 1

    # Check for tests that point to non-existent requirements
    for req_id, test_files in verifications.items():
        if req_id not in definitions:
            table.add_row(req_id, "[bold yellow]DANGLING TEST[/bold yellow]", f"Found in {test_files[0]}")
            dangling_tests += 1

    console.print(table)

    # 4. Implicit Traceability (Dead Code / Coverage Check)
    untested_files = check_implicit_traceability(path)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"   Requirements Defined: {len(definitions)}")
    console.print(f"   Orphaned Requirements: [red]{orphaned_reqs}[/red]")
    console.print(f"   Dangling Test Links: [yellow]{dangling_tests}[/yellow]")
    console.print(f"   Untested Source Files (Implicit Drift): [magenta]{untested_files}[/magenta]")

    if orphaned_reqs > 0 or dangling_tests > 0 or untested_files > 0:
        console.print("\n[bold red]🛑 Traceability Audit Failed. Fix orphaned items before release.[/bold red]")
        sys.exit(1)


def check_implicit_traceability(path) -> int:
    """
    Parses coverage.xml to find files with 0% coverage.
    If a file has 0% coverage, it means no traced test ever executes it,
    making it "Dead Code" or "Untraced Logic".
    """
    cov_file = os.path.join(path, "coverage.xml")
    if not os.path.exists(cov_file):
        return 0

    untested = 0
    try:
        tree = ET.parse(cov_file)  # nosec B314 # nosemgrep
        for cls in tree.iter("class"):
            filename = cls.attrib.get("filename", "")
            line_rate = float(cls.attrib.get("line-rate", "1.0"))

            # If a source file has 0% coverage, it is untraced.
            if line_rate == 0.0 and "src" in filename:
                console.print(f"   [magenta]⚠️  Untraced File (0% Coverage):[/magenta] {filename}")
                untested += 1
    except Exception:
        pass

    return untested


def execute(args):
    if args.audit_command == "structure":
        audit_structure(args.target)
    elif args.audit_command == "traceability":
        audit_traceability(args.target, args.is_global)