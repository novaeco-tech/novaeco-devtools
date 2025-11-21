import os
import json
import sys
import argparse

# Configuration: Define what distinct services look like and where their version lives
SERVICE_TYPES = {
    "api": {"path": "api/VERSION", "type": "text"},
    "auth": {"path": "auth/VERSION", "type": "text"},
    "app": {"path": "app/VERSION", "type": "text"},
    "website": {"path": "website/package.json", "type": "json"},
}

GLOBAL_FILE = "GLOBAL_VERSION"

def register_subcommand(subparsers):
    """Registers this module's commands with the main parser."""
    
    # Define the examples to show in the help output
    examples = """Examples:
  # Patch a specific service (bug fix)
  nova version patch api
  
  # Create a new release (feature)
  nova version release minor
  nova version release major
"""

    parser = subparsers.add_parser(
        "version", 
        help="Manage ecosystem versions",
        formatter_class=argparse.RawDescriptionHelpFormatter, # <--- Preserves newlines
        epilog=examples # <--- Adds the examples at the bottom
    )
    
    # Add sub-actions for 'version'
    v_subs = parser.add_subparsers(dest="version_command", required=True)
    
    # Command: nova version patch <service>
    p_patch = v_subs.add_parser("patch", help="Bump patch version (e.g., 1.0.0 -> 1.0.1)")
    p_patch.add_argument("service", help="Service name (api, auth, app, website)")
    
    # Command: nova version release <type>
    p_release = v_subs.add_parser("release", help="Bump Global Major/Minor version (aligns all services)")
    p_release.add_argument("type", choices=["minor", "major"], help="Type of release")

def detect_services():
    """Returns a dict of services present in the current working directory."""
    found = {}
    for name, config in SERVICE_TYPES.items():
        if os.path.exists(config["path"]):
            found[name] = config
    return found

def read_version(config):
    """Reads version from text or json file."""
    if config["type"] == "text":
        with open(config["path"], 'r') as f:
            return f.read().strip()
    elif config["type"] == "json":
        with open(config["path"], 'r') as f:
            return json.load(f)["version"]

def write_version(config, new_version):
    """Writes version to text or json file."""
    print(f"  -> Updating {config['path']} to {new_version}")
    if config["type"] == "text":
        with open(config["path"], 'w') as f:
            f.write(new_version)
    elif config["type"] == "json":
        with open(config["path"], 'r') as f:
            data = json.load(f)
        data["version"] = new_version
        with open(config["path"], 'w') as f:
            json.dump(data, f, indent=4)
            f.write('\n') # Ensure newline at end of file

def get_global_version():
    if not os.path.exists(GLOBAL_FILE):
        return "1.0"
    with open(GLOBAL_FILE, 'r') as f:
        return f.read().strip()

def execute_patch(service_name, services):
    if service_name not in services:
        print(f"Error: Service '{service_name}' not found in this repository.")
        print(f"Available services here: {list(services.keys())}")
        sys.exit(1)

    config = services[service_name]
    current = read_version(config)
    
    try:
        major, minor, patch = map(int, current.split('.'))
        new_version = f"{major}.{minor}.{patch + 1}"
        print(f"Bumping PATCH for {service_name}: {current} -> {new_version}")
        write_version(config, new_version)
    except ValueError:
        print(f"Error: Could not parse version '{current}' in {config['path']}. Expected format X.Y.Z")
        sys.exit(1)

def execute_release(release_type, services):
    current_global = get_global_version()
    try:
        major, minor = map(int, current_global.split('.'))
    except ValueError:
        print(f"Error: GLOBAL_VERSION file contains invalid format '{current_global}'. Expected X.Y")
        sys.exit(1)
    
    if release_type == "major":
        major += 1
        minor = 0
    else: # minor
        minor += 1
        
    new_global = f"{major}.{minor}"
    new_service_version = f"{new_global}.0"
    
    print(f"Bumping GLOBAL ({release_type}): {current_global} -> {new_global}")
    
    # 1. Update Global File
    with open(GLOBAL_FILE, 'w') as f:
        f.write(new_global)
        
    # 2. Update ALL detected services to match
    for name, config in services.items():
        write_version(config, new_service_version)

def execute(args):
    # 1. Detect what services are available in the current folder
    services = detect_services()
    if not services:
        print("Warning: No standard service files (api/VERSION, website/package.json, etc.) found.")
        # We don't exit because maybe they just want to see help
    
    if args.version_command == "patch":
        execute_patch(args.service, services)
        
    elif args.version_command == "release":
        execute_release(args.type, services)