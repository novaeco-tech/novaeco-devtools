import os
import sys
import subprocess
import argparse
import shutil

def register_subcommand(subparsers):
    """Registers the 'test' command and its sub-commands."""
    
    examples = """Examples:
  # Run unit tests in the current repo (auto-detects Python/Node)
  novaeco test unit

  # Run integration tests with a keyword filter
  novaeco test integration --filter "database"

  # Run global acceptance tests (QA repo)
  novaeco test acceptance
"""

    parser = subparsers.add_parser(
        "test", 
        help="Execute tests (Unit, Integration, E2E, Acceptance)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples
    )
    
    test_subs = parser.add_subparsers(dest="test_scope", required=True)
    
    # Standard Scopes
    # These align with the Master Testing Matrix
    scopes = ["unit", "integration", "e2e", "system", "acceptance", "smoke"]
    
    for scope in scopes:
        p = test_subs.add_parser(scope, help=f"Run {scope.capitalize()} tests")
        p.add_argument("-f", "--filter", help="Filter tests by keyword (passed to -k in pytest)")
        p.add_argument("--watch", action="store_true", help="Run in watch mode (if supported)")

def detect_runtime():
    """Heuristic to decide if this is a Python or Node.js repository."""
    if os.path.exists("package.json"):
        return "node"
    if os.path.exists("pyproject.toml") or os.path.exists("requirements.txt") or os.path.exists("setup.py"):
        return "python"
    return "unknown"

def run_python_test(scope, args):
    """Runs Pytest for the specific scope."""
    target_dir = f"tests/{scope}"
    
    # Handle the slightly different pathing for QA repo structure vs Component repo
    # If standard path doesn't exist, try looking closer (e.g., just 'tests/')
    if not os.path.exists(target_dir):
        # Fallback for simple repos where tests might just be in 'tests/'
        # But generally we enforce the folder structure.
        print(f"⚠️  Directory '{target_dir}' not found.")
        # We check if maybe the user is in root and meant 'novaeco-qa/tests/system'
        # But usually CLI is run from repo root.
        if not os.path.exists("tests"):
             print("❌ No 'tests/' directory found in current root.")
             sys.exit(1)
    
    print(f"🐍 Detected Python Runtime. Running Pytest on {target_dir}...")
    
    cmd = ["pytest", target_dir]
    
    # Add common robust flags
    cmd.append("-v") # Verbose
    
    if args.filter:
        cmd.extend(["-k", args.filter])
        
    if args.watch:
        # Requires pytest-watch or pytest-xdist used in a specific way
        # For now, we'll just warn it's not fully standard in vanilla pytest
        print("⚠️  Watch mode in Python requires 'pytest-watch' (ptw). Running standard test...")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ {scope.capitalize()} tests failed.")
        sys.exit(1)

def run_node_test(scope, args):
    """Runs NPM scripts for the specific scope."""
    print(f"📦 Detected Node.js Runtime.")
    
    # Map 'scope' to standard npm script names defined in package.json
    # Convention: "test:unit", "test:e2e", "test:int"
    script_map = {
        "unit": "test:unit",
        "integration": "test:integration",
        "e2e": "test:e2e",
        "accessibility": "test:a11y"
    }
    
    script_name = script_map.get(scope, f"test:{scope}")
    
    # Check if script exists in package.json (simple grep check or json load)
    # We'll just try running it and catch error for simplicity in this script
    cmd = ["npm", "run", script_name, "--"]
    
    if args.filter:
        # Pass filter to Jest/Playwright
        # Jest uses -t, Playwright uses -g. This is tricky to standardize 100%.
        # We assume the underlying script accepts arguments passed after '--'
        cmd.append(args.filter)

    print(f"   Executing: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ 'npm run {script_name}' failed.")
        sys.exit(1)

def execute(args):
    runtime = detect_runtime()
    
    if runtime == "python":
        run_python_test(args.test_scope, args)
    elif runtime == "node":
        run_node_test(args.test_scope, args)
    else:
        print("❌ Could not detect project type (no pyproject.toml or package.json found).")
        sys.exit(1)