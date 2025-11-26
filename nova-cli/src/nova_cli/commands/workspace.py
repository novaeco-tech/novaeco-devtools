import os
import json
import subprocess
import shutil
import sys

# Configuration
ORG_NAME = "novaeco-tech"
TARGET_DIR = "repos"
WORKSPACE_FILENAME = "novaeco.code-workspace"

# Priority defines the order in the VS Code workspace file
TOPIC_PRIORITY = [
    "meta",
    "ecosystem",
    "enabler",
    "sector",
    "worker",
    "product"
]

def register_subcommand(subparsers):
    parser = subparsers.add_parser("init", help="Clone repos and build workspace based on GitHub topics")
    parser.add_argument("--force", action="store_true", help="Re-clone existing repositories")

def check_gh_cli():
    """Ensures GitHub CLI is installed and authenticated."""
    if shutil.which("gh") is None:
        print("❌ Error: GitHub CLI ('gh') is not installed.")
        print("   Please install it: https://cli.github.com/")
        sys.exit(1)

def fetch_repos():
    """Fetches repository list and topics using 'gh' CLI."""
    print(f"🔍 Fetching repository list from {ORG_NAME}...")
    cmd = [
        "gh", "repo", "list", ORG_NAME,
        "--limit", "1000",
        "--json", "name,sshUrl,topics",
        "--no-archived"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error fetching repos: {e.stderr}")
        sys.exit(1)

def categorize_repos(repo_list):
    """Sorts repositories into buckets based on TOPIC_PRIORITY."""
    categorized = {topic: [] for topic in TOPIC_PRIORITY}
    categorized["uncategorized"] = []

    for repo in repo_list:
        repo_topics = repo.get("topics", [])
        assigned = False
        
        # Check topics in priority order (e.g. if it has 'ecosystem' and 'meta', 'meta' wins)
        for topic in TOPIC_PRIORITY:
            if topic in repo_topics:
                categorized[topic].append(repo)
                assigned = True
                break
        
        if not assigned:
            categorized["uncategorized"].append(repo)

    return categorized

def clone_repositories(categorized_repos, force_reclone):
    """Clones the repositories into the target directory."""
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    for category, repos in categorized_repos.items():
        if not repos:
            continue
            
        print(f"\n📂 Processing Category: {category.upper()}")
        for repo in repos:
            repo_name = repo["name"]
            repo_url = repo["sshUrl"]
            local_path = os.path.join(TARGET_DIR, repo_name)

            if os.path.exists(local_path):
                if force_reclone:
                    print(f"   ♻️  Removing existing {repo_name}...")
                    shutil.rmtree(local_path)
                else:
                    print(f"   ✅ {repo_name} already exists (skipping)")
                    continue

            print(f"   ⬇️  Cloning {repo_name}...")
            subprocess.run(["git", "clone", repo_url, local_path], check=True)

def generate_workspace_json(categorized_repos):
    """Generates the .code-workspace JSON file with categorized folders."""
    folders = []

    # Helper to add a list of repos to the folders config
    def add_group(group_repos):
        # Sort alphabetically within the group
        group_repos.sort(key=lambda x: x["name"])
        for r in group_repos:
            folders.append({
                "name": r["name"],
                "path": f"{TARGET_DIR}/{r['name']}"
            })

    # Add folders in the strict order of TOPIC_PRIORITY
    for topic in TOPIC_PRIORITY:
        repos = categorized_repos.get(topic, [])
        if repos:
            # Add a visual separator in the JSON (VS Code ignores pathless entries or comments, 
            # but we can't easily add comments to JSON output. We rely on order.)
            add_group(repos)

    # Add uncategorized at the bottom
    if categorized_repos["uncategorized"]:
        add_group(categorized_repos["uncategorized"])

    workspace_data = {
        "folders": folders,
        "settings": {
            "files.exclude": {
                "**/.git": True,
                "**/.svn": True,
                "**/.hg": True,
                "**/CVS": True,
                "**/.DS_Store": true,
                "**/Thumbs.db": true,
                "**/node_modules": True,
                "**/__pycache__": True,
                "**/.venv": True
            },
            "explorer.compactFolders": False
        }
    }

    with open(WORKSPACE_FILENAME, "w") as f:
        json.dump(workspace_data, f, indent=2)
    
    print(f"\n📝 Generated workspace file: {os.path.abspath(WORKSPACE_FILENAME)}")

def execute(args):
    check_gh_cli()
    all_repos = fetch_repos()
    categorized = categorize_repos(all_repos)
    
    clone_repositories(categorized, args.force)
    generate_workspace_json(categorized)
    
    print("\n✨ Development environment setup complete!")
    print(f"👉 Run: code {WORKSPACE_FILENAME}")