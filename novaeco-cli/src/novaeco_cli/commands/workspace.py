import json
import os
import shutil
import subprocess
import sys

# --- Configuration ---
ORG_NAME = "novaeco-tech"
TARGET_DIR = "repos"
WORKSPACE_FILENAME = "novaeco.code-workspace"

# Priority defines the order in the VS Code workspace file
# Repositories are grouped by the first matching topic found in this list.
TOPIC_PRIORITY = [
    "meta",  # e.g., .github, governance repos
    "novaeco",  # e.g., novaeco repositories
]


def register_subcommand(subparsers):
    """Registers the 'init' command with the main argument parser."""
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
    cmd = ["gh", "repo", "list", ORG_NAME, "--limit", "1000", "--json", "name,sshUrl,repositoryTopics", "--no-archived"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error fetching repos: {e.stderr}")
        sys.exit(1)


def categorize_repos(repo_list):
    """Sorts repositories into buckets based on TOPIC_PRIORITY.
    Unmatched repos are placed in an 'other' bucket."""

    # Initialize buckets for priority topics + a catch-all 'other'
    categorized = {topic: [] for topic in TOPIC_PRIORITY}
    categorized["other"] = []

    for repo in repo_list:
        # Handle case where GitHub returns explicit null for empty topics
        raw_topics = repo.get("repositoryTopics") or []
        repo_topics = [t["name"] for t in raw_topics]

        matched = False

        # Check topics in priority order
        for topic in TOPIC_PRIORITY:
            if topic in repo_topics:
                categorized[topic].append(repo)
                matched = True
                break

        # If no priority topic matched, add to 'other' for tracking/warning
        if not matched:
            categorized["other"].append(repo)

    return categorized


def clone_repositories(categorized_repos, force_reclone):
    """Clones the repositories into the target directory."""
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    for category, repos in categorized_repos.items():
        # SKIP cloning for the 'other' category
        if category == "other":
            continue

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

    # Helper to add a list of repos to the folders config with a prefix
    def add_group(category_label, group_repos):
        # Sort alphabetically within the group
        group_repos.sort(key=lambda x: x["name"])
        for r in group_repos:
            # Prefix the display name (e.g., "PRODUCT: my-app")
            display_name = f"{category_label.upper()}: {r['name']}"

            folders.append({"name": display_name, "path": f"{TARGET_DIR}/{r['name']}"})

    # Add folders ONLY for the strict order of TOPIC_PRIORITY
    # We deliberately ignore 'other' here to exclude them from the workspace
    for topic in TOPIC_PRIORITY:
        repos = categorized_repos.get(topic, [])
        if repos:
            add_group(topic, repos)

    workspace_data = {
        "folders": folders,
        "settings": {
            "files.exclude": {
                "**/.git": True,
                "**/.DS_Store": True,
                "**/node_modules": True,
                "**/__pycache__": True,
                "**/.venv": True,
            },
            "explorer.compactFolders": False,
        },
    }

    with open(WORKSPACE_FILENAME, "w") as f:
        json.dump(workspace_data, f, indent=2)

    print(f"\n📝 Generated workspace file: {os.path.abspath(WORKSPACE_FILENAME)}")


def execute(args):
    check_gh_cli()
    all_repos = fetch_repos()
    categorized = categorize_repos(all_repos)

    # Print warning for skipped repositories
    skipped = categorized.get("other", [])
    if skipped:
        print(f"\n⚠️  Skipped {len(skipped)} repositories (topics did not match target product):")
        for r in skipped:
            print(f"   - {r['name']}")

    clone_repositories(categorized, args.force)
    generate_workspace_json(categorized)

    print("\n✨ Development environment setup complete!")
    print(f"👉 Run: code {WORKSPACE_FILENAME}")
