import os
import sys
import glob
import re
import json
import shutil
import subprocess
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

def get_repo_type_from_github(root_dir):
    """Attempts to detect repo type from GitHub topics using gh CLI."""
    if shutil.which("gh") is None:
        return None
        
    try:
        # Run gh repo view in the target directory to get the context of that repo
        # We fetch the 'repositoryTopics' field to see tags like 'core', 'sector'
        cmd = ["gh", "repo", "view", "--json", "repositoryTopics"]
        
        # Suppress output to avoid cluttering the audit log
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            cwd=root_dir  # Execute in the target repo's directory
        )
        data = json.loads(result.stdout)
        
        # data structure: {'repositoryTopics': [{'name': 'core'}, {'name': 'python'}]}
        topics = [t['name'] for t in data.get('repositoryTopics', [])]
        
        # Match against our known keys in STRUCTURE_RULES
        for topic in topics:
            if topic in STRUCTURE_RULES:
                return topic
                
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        # Fail silently and fall back to file heuristics if no network/gh tool
        return None
    return None

def detect_repo_type(root_dir):
    """Detects repo type using GitHub topics, falling back to file heuristics."""
    
    # 1. Try GitHub Topics (Source of Truth)
    gh_type = get_repo_type_from_github(root_dir)
    if gh_type:
        # console.print(f"[dim]ℹ️  Detected type '{gh_type}' from GitHub topics[/dim]")
        return gh_type

    # 2. Fallback to Heuristics (File-based)
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
    p_structure.add_argument('targets', nargs='*', default=[], help='Specific repos to check (e.g. "novaagro"). If empty, checks current dir or all repos if in root.')

    # Command: traceability
    p_trace = audit_subs.add_parser("traceability", help="Generate V-Model Traceability Matrix")
    p_trace.add_argument('targets', nargs='*', default=[], help='Specific repos to check (e.g. "novaagro"). If empty, checks current dir or all repos if in root.')

def execute(args):
    """Dispatches execution to the correct function."""
    if args.audit_command == "structure":
        dispatch_structure_audit(args.targets)
    elif args.audit_command == "traceability":
        dispatch_traceability_audit(args.targets)

# --- Dispatch Logic (Handles Global vs Local) ---

def dispatch_audit_generic(targets, audit_func):
    """Generic dispatcher for running an audit function against one or many repos."""
    cwd = os.getcwd()
    repos_dir = os.path.join(cwd, "repos")
    
    # CASE 1: User specified targets: "novaeco audit structure novaagro"
    if targets:
        success = True
        for t in targets:
            candidate = os.path.join(repos_dir, t)
            if not os.path.exists(candidate):
                candidate = os.path.abspath(t)
            
            if not audit_func(candidate):
                success = False
        if not success:
            sys.exit(1)
        return

    # CASE 2: Running from Workspace Root (Auto-discover all)
    if os.path.exists(repos_dir) and os.path.isdir(repos_dir):
        console.print(f"[bold blue]🚀 Detected Workspace Root. Auditing all repositories in ./repos ...[/bold blue]")
        
        results = {"pass": 0, "fail": 0}
        repo_list = sorted([d for d in os.listdir(repos_dir) if os.path.isdir(os.path.join(repos_dir, d))])
        
        for repo in repo_list:
            full_path = os.path.join(repos_dir, repo)
            if repo.startswith("."): continue
            
            if audit_func(full_path):
                results["pass"] += 1
            else:
                results["fail"] += 1
                
        console.print(f"\n[bold]🏁 Summary: {results['pass']} Passed | {results['fail']} Failed[/bold]")
        if results["fail"] > 0:
            sys.exit(1)
        return

    # CASE 3: Running from inside a repo (Single mode)
    if not audit_func("."):
        sys.exit(1)

def dispatch_structure_audit(targets):
    dispatch_audit_generic(targets, audit_single_structure)

def dispatch_traceability_audit(targets):
    dispatch_audit_generic(targets, audit_single_traceability)

# --- Core Logic Implementation ---

def audit_single_structure(path):
    """Audits structure for a single repository. Returns True if passed."""
    path = os.path.abspath(path)
    repo_name = os.path.basename(path)
    
    if not os.path.isdir(path):
        console.print(f"[red]❌ Error: {path} is not a directory.[/red]")
        return False

    repo_type = detect_repo_type(path)
    
    console.print(f"[bold]🔍 Auditing {repo_name} ({repo_type})...[/bold]")
    
    rules = STRUCTURE_RULES.get(repo_type, STRUCTURE_RULES["sector"]) 
    missing = []
    
    for rule_path in rules:
        full_path = os.path.join(path, rule_path)
        if not os.path.exists(full_path):
            missing.append(rule_path)
            
    if repo_type not in ["worker", "core"]:
        internal_reqs = os.path.join(path, "api/requirements-internal.txt")
        if not os.path.exists(internal_reqs):
             console.print(f"   [yellow]⚠️  Warning: api/requirements-internal.txt missing.[/yellow]")

    if missing:
        console.print(f"   [bold red]❌ FAILED. Missing:[/bold red]")
        for m in missing:
            console.print(f"      - {m}")
        return False
    
    console.print(f"   [bold green]✅ OK[/bold green]")
    return True

def audit_single_traceability(path):
    """Audits traceability for a single repository. Returns True if passed."""
    path = os.path.abspath(path)
    repo_name = os.path.basename(path)
    
    if not os.path.isdir(path):
        console.print(f"[red]❌ Error: {path} is not a directory.[/red]")
        return False

    console.print(f"\n[bold blue]🔍 Scanning requirements in: {repo_name}[/bold blue]")

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
        console.print(f"   [yellow]⚠️  No requirement IDs (REQ-*) found.[/yellow]")
        # We return True because it's not a failure, just empty (e.g. for devtools)
        return True

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
    table = Table(title=f"Traceability: {repo_name}")
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
    console.print(f"   [bold]Summary:[/bold] ✅ {pass_count} Covered | ❌ {fail_count} Missing")
    
    return fail_count == 0