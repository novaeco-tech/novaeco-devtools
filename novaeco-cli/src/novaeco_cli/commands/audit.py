import os
import sys
import glob
import argparse

# The "Golden Template" for every repo type
STRUCTURE_RULES = {
    "core": [
        "api/src/main.py", "api/requirements.txt", "api/Dockerfile",
        "app/app.py", "app/requirements.txt",
        "auth/src/main.py", "auth/api/proto/v1/auth.proto",
        "website/docs/requirements/functional.md", "website/docusaurus.config.js",
        ".github/workflows/ci.yml", ".github/CODEOWNERS"
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

def register_subcommand(subparsers):
    parser = subparsers.add_parser("audit", help="Audit repository structure and requirements")
    # No extra arguments needed for now, it audits the current directory

def check_structure(repo_type):
    """Checks if current directory matches the rules."""
    print(f"🔍 Auditing {repo_type} repository structure...")
    
    rules = STRUCTURE_RULES.get(repo_type, STRUCTURE_RULES["sector"]) 
    missing = []
    
    for path in rules:
        if not os.path.exists(path):
            missing.append(path)
            
    # Check for requirements-internal.txt (Architecture Step 1e)
    # This is critical for the QA Dependency Graph
    # Workers usually just have requirements.txt at root
    if repo_type != "worker" and repo_type != "core":
        if not os.path.exists("api/requirements-internal.txt"):
             print("⚠️ Warning: api/requirements-internal.txt missing. QA Graph might fail.")

    if missing:
        print("❌ Drift Detected! Missing standard paths:")
        for m in missing:
            print(f"   - {m}")
        return False
        
    print("✅ Structure complies with NovaEco Standards.")
    return True

def scan_requirements():
    """Scans for REQ- IDs in markdown files."""
    print("\n🔍 Scanning for Requirements Definitions...")
    reqs = []
    # Scan both functional and non-functional requirements
    # Also catch other potential requirement files
    search_path = "website/docs/requirements/*.md"
    
    # If it's a worker, docs might be in root or differently placed, 
    # but based on specs, they should be in website/docs if applicable.
    # For standalone workers without website folder, we might skip or check README.
    
    files = glob.glob(search_path)
    if not files:
         # Fallback for simple repos or different structures
         files = glob.glob("docs/*.md")

    for file in files:
        print(f"   Reading {file}...")
        with open(file, 'r') as f:
            for line in f:
                # Matches ## REQ-AGRO-FUNC-001 or similar
                if line.strip().startswith("## REQ-"):
                    # Extract ID: "## REQ-AGRO-FUNC-001: Title" -> "REQ-AGRO-FUNC-001"
                    parts = line.strip().split(" ")
                    if len(parts) > 1:
                        req_id = parts[1].replace(":", "")
                        reqs.append(req_id)
                        print(f"      found: {req_id}")
    return reqs

def detect_repo_type():
    """Heuristic to detect repo type based on folder structure."""
    if os.path.exists("auth") and os.path.exists("api") and os.path.exists("app"):
        return "core"
    elif os.path.exists("api") and os.path.exists("app") and os.path.exists("website"):
        # Could be enabler, sector, or product. 
        # We can check package.json or naming convention if needed, 
        # but their structure rules are identical for now.
        return "sector" 
    elif os.path.exists("src") and os.path.exists("Dockerfile") and not os.path.exists("api"):
        return "worker"
    else:
        return "sector" # Default fallback

def execute(args):
    rtype = detect_repo_type()
    
    valid_struct = check_structure(rtype)
    reqs = scan_requirements()
    
    if not reqs and rtype != "worker": # Workers might not have rigorous requirements docs yet
        print("⚠️ No requirements defined in website/docs/requirements/*.md")
    
    if not valid_struct:
        sys.exit(1)