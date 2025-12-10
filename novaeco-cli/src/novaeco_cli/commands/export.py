import os
import argparse
import sys

# --- Configuration & Defaults ---

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".pytest_cache", "node_modules", "dist", "build", 
    "__pycache__", ".idea", ".vscode", ".venv", "venv", "bin", "obj", ".docusaurus", ".ruff_cache"
}

DEFAULT_EXCLUDE_EXTS = {
    # Images
    "png", "jpg", "jpeg", "gif", "ico", "svg", "webp",
    # Archives
    "zip", "tar", "gz", "7z", "rar",
    # Executables/Binary
    "exe", "dll", "so", "dylib", "bin", "pyc", "class", "jar",
    # Lock files (often huge and noisy)
    "lock" 
}

# Partial paths to exclude (matches if the file path ends with these)
DEFAULT_EXCLUDE_PATHS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock"
}

def register_subcommand(subparsers):
    parser = subparsers.add_parser(
        "export", 
        help="Export text content of files for AI context",
        description="Recursively reads files and merges them into a single text output."
    )
    
    parser.add_argument(
        "path", 
        nargs="?", 
        default=".", 
        help="Root path to export (file or directory). Defaults to current dir."
    )
    
    parser.add_argument(
        "-o", "--output", 
        default="context.txt", 
        help="Output file path (default: context.txt)"
    )
    
    parser.add_argument(
        "--no-defaults", 
        action="store_true", 
        help="Ignore default exclusion lists"
    )

    # Configuration flags
    parser.add_argument("--exclude-dirs", nargs="+", default=[], help="Add directories to exclude")
    parser.add_argument("--exclude-exts", nargs="+", default=[], help="Add extensions to exclude")
    parser.add_argument("--exclude-paths", nargs="+", default=[], help="Add specific path suffixes to exclude")

def is_excluded(file_path, exclude_paths, exclude_exts):
    """Checks if a file should be skipped based on extension or specific path."""
    filename = os.path.basename(file_path)
    
    # 1. Check Extension
    if "." in filename:
        ext = filename.split(".")[-1].lower()
        if ext in exclude_exts:
            return True
            
    # 2. Check Specific Paths (Suffix Match)
    # Matches bash script logic: find ... -path "*config/secrets.js"
    for p in exclude_paths:
        if file_path.endswith(p) or file_path.endswith(os.path.sep + p):
            return True
            
    return False

def process_file(file_path):
    """Reads a file and returns formatted string, or None if unreadable."""
    try:
        # Try reading as UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        header = "=" * 80 + "\n"
        header += f"### FILE: {file_path}\n"
        header += "=" * 80 + "\n\n"
        
        return header + content + "\n\n"
    except (UnicodeDecodeError, Exception):
        # Skip binary or unreadable files that slipped through extension checks
        return None

def execute(args):
    root_path = os.path.abspath(args.path)
    output_file = os.path.abspath(args.output)
    
    # Merge Defaults with Arguments
    if args.no_defaults:
        exclude_dirs = set(args.exclude_dirs)
        exclude_exts = set(args.exclude_exts)
        exclude_paths = set(args.exclude_paths)
    else:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS.union(args.exclude_dirs)
        exclude_exts = DEFAULT_EXCLUDE_EXTS.union(args.exclude_exts)
        exclude_paths = DEFAULT_EXCLUDE_PATHS.union(args.exclude_paths)

    print(f"📦 Exporting content from: {root_path}")
    print(f"📄 Output target: {output_file}")

    if not os.path.exists(root_path):
        print(f"❌ Error: Path '{root_path}' does not exist.")
        sys.exit(1)

    files_processed = 0
    
    with open(output_file, 'w', encoding='utf-8') as out:
        # CASE 1: Single File
        if os.path.isfile(root_path):
            content = process_file(root_path)
            if content:
                out.write(content)
                files_processed = 1
        
        # CASE 2: Directory
        else:
            for root, dirs, files in os.walk(root_path):
                # 1. Prune Excluded Directories (in-place modification of 'dirs')
                # We iterate over a copy so we can remove items safely
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start=os.getcwd())
                    
                    if is_excluded(rel_path, exclude_paths, exclude_exts):
                        continue
                        
                    # Skip the output file itself if it's inside the target dir
                    if os.path.abspath(full_path) == output_file:
                        continue

                    print(f"   + {rel_path}")
                    content = process_file(full_path)
                    
                    if content:
                        out.write(content)
                        files_processed += 1
                    else:
                        print(f"     ⚠️  Skipping binary/unreadable: {rel_path}")

    print(f"\n✅ Success! Exported {files_processed} files to '{args.output}'")