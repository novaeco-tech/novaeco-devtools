import os
import sys
import glob
import re
from collections import defaultdict
from rich.console import Console
from rich.table import Table

console = Console()

# --- Configuration & Constants ---

STRUCTURE_RULES = {
    "core": [
        "api/src/api_service.py",
        "api/tests/unit",
        "api/requirements.txt", "api/requirements-dev.txt", "api/requirements-internal.txt",
        "api/pyproject.toml",
        "api/VERSION",

        "app/src/app_service.py",
        "app/tests/unit",
        "app/requirements.txt", "app/requirements-dev.txt", "app/requirements-internal.txt",
        "app/pyproject.toml",
        "app/VERSION",

        "auth/src/auth_service.py",
        "auth/api/proto/v1/auth.proto",
        "auth/tests/unit",
        "auth/requirements.txt", "auth/requirements-dev.txt", "auth/requirements-internal.txt",
        "auth/pyproject.toml",
        "auth/VERSION",

        "website/docs/requirements/functional.md", 
        "website/docs/requirements/non-functional.md", 
        "website/docs/requirements/sustainability.md", 
        "website/docusaurus.config.js",
        "website/package.json",
        "website/src/components/__tests__",

        "tests/e2e/specs",
        "tests/performance",
        "tests/integration",

        ".github/workflows/ci.yml", 
        ".github/workflows/lint.yml",
        ".github/workflows/sast.yml",
        ".github/workflows/publish-api.yml",
        ".github/workflows/publish-app.yml",
        ".github/workflows/publish-auth.yml",
        ".github/workflows/publish-website.yml",

        ".github/CODEOWNERS"
    ],
    "enabler": [
        "api/src/main.py", "api/requirements.txt",
        "app/app.py",
        "website/docs/requirements/functional.md",
        "website/docs/requirements/non-functional.md",
        "tests/integration"
    ],
    "sector": [
        "api/src/main.py", "api/requirements.txt",
        "app/app.py",
        "website/docs/requirements/functional.md",
        "website/docs/requirements/non-functional.md",
        "tests/integration"
    ],
    "product": [
        "api/src/main.py", "api/requirements.txt",
        "app/app.py",
        "website/docs/requirements/functional.md",
        "website/docs/requirements/non-functional.md",
        "tests/integration"
    ],
    "worker": [
        "src/main.py", "requirements.txt",
        "tests"
    ]
}

REQ_DEF_PATTERN = re.compile(r'(REQ-[A-Z]+-[A-Z]+-\d+)')
TEST_VERIFY_PATTERN = re.compile(r'@pytest\.mark\.requirement\(\s*["\'](REQ-[^"\']+)["\']\s*\)')

# --- Helpers ---

def detect_repo_type(root_dir):
    """Heuristic to detect repo type based on folder structure."""
    if os.path.exists(os.path.join(root_dir, "auth")) and os.path.exists(os.path.join(root_dir, "api")):
        return "core"
    elif os.path.exists(os.path.join(root_dir, "api")) and os.path.exists(os.path.join(root_dir, "website")):
        return "sector" 
    elif os.path.exists(os.path.join(root_dir, "src")) and os.path.exists(os.path.join(root_dir, "Dockerfile")) and not os.path.exists(os.path.join(root_dir, "api")):
        return "worker"
    else:
        return "sector"

# --- Registration & Execution (Argparse) ---

def register_subcommand(subparsers):
    """Registers the audit command and its subcommands with argparse."""
    parser = subparsers.add_parser("audit", help="Audit tools for structure compliance and requirements")
    
    # Create subcommands like 'novaeco audit structure'
    audit_subs = parser.add_subparsers(dest="audit_command", required=True)

    # Command: structure
    p_structure = audit_subs.add_parser("structure", help="Check Golden Template compliance")
    p_structure.add_argument('--path', default='.', help='Root path to scan')

    # Command: traceability
    p_trace = audit_subs.add_parser("traceability", help="Generate V-Model Traceability Matrix")
    p_trace.add_argument('--path', default='.', help='Root path to scan')

def execute(args):
    """Dispatches execution to the correct function."""
    if args.audit_command == "structure":
        run_structure(args.path)
    elif args.audit_command == "traceability":
        run_traceability(args.path)

# --- Logic Implementation ---

def run_structure(path):
    """Checks if the repository matches the Golden Template."""
    path = os.path.abspath(path)
    repo_type = detect_repo_type(path)
    
    console.print(f"[bold blue]🔍 Auditing {repo_type} repository structure at: {path}[/bold blue]")
    
    rules = STRUCTURE_RULES.get(repo_type, STRUCTURE_RULES["sector"]) 
    missing = []
    
    for rule_path in rules:
        full_path = os.path.join(path, rule_path)
        if not os.path.exists(full_path):
            missing.append(rule_path)
            
    if repo_type not in ["worker", "core"]:
        internal_reqs = os.path.join(path, "api/requirements-internal.txt")
        if not os.path.exists(internal_reqs):
             console.print("[yellow]⚠️  Warning: api/requirements-internal.txt missing. QA Graph might fail.[/yellow]")

    if missing:
        console.print("[bold red]❌ Drift Detected! Missing standard paths:[/bold red]")
        for m in missing:
            console.print(f"   - {m}")
        sys.exit(1)
        
    console.print("[bold green]✅ Structure complies with NovaEco Standards.[/bold green]")

def run_traceability(path):
    """Generates the V-Model Traceability Matrix."""
    path = os.path.abspath(path)
    console.print(f"[bold blue]🔍 Scanning requirements in: {path}[/bold blue]")

    # 1. Find Definitions
    definitions = {}
    search_patterns = [
        os.path.join(path, "website", "docs", "requirements", "*.md"),
        os.path.join(path, "docs", "*.md")
    ]
    
    for pattern in search_patterns:
        for file_path in glob.glob(pattern):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = REQ_DEF_PATTERN.search(line)
                    if match:
                        req_id = match.group(1)
                        rel_path = os.path.relpath(file_path, path)
                        definitions[req_id] = rel_path

    if not definitions:
        console.print("[yellow]⚠️  No requirement IDs (REQ-*) found in documentation.[/yellow]")
        return

    # 2. Find Verifications
    verifications = defaultdict(list)
    test_pattern = os.path.join(path, "**", "tests", "**", "*.py")
    
    for file_path in glob.glob(test_pattern, recursive=True):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = TEST_VERIFY_PATTERN.findall(content)
            for req_id in matches:
                rel_path = os.path.relpath(file_path, path)
                verifications[req_id].append(rel_path)

    # 3. Build Table
    table = Table(title="Traceability Matrix")
    table.add_column("Req ID", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Definition File", style="dim")
    table.add_column("Verified By (Test)", style="green")

    pass_count = 0
    fail_count = 0

    for req_id in sorted(definitions.keys()):
        def_file = definitions[req_id]
        tests = verifications.get(req_id, [])
        
        if tests:
            status = "[bold green]PASS[/bold green]"
            test_str = "\n".join(tests[:2]) 
            if len(tests) > 2: test_str += "\n..."
            pass_count += 1
        else:
            status = "[bold red]MISSING[/bold red]"
            test_str = "-"
            fail_count += 1
            
        table.add_row(req_id, status, def_file, test_str)

    console.print(table)
    
    console.print(f"\n[bold]Summary:[/bold] ✅ {pass_count} Covered | ❌ {fail_count} Missing")
    
    if fail_count > 0:
        sys.exit(1)
