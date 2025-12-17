import os
import sys
import shutil
import subprocess
import argparse
import glob
import re
import tarfile
from pathlib import Path

def register_subcommand(subparsers):
    """Registers the 'build' command and its sub-commands (client, service)."""
    
    # Define examples to show in the help output (novaeco build --help)
    examples = """Examples:
  # --- Client SDK Building ---
  # Compile ProtoBufs from 'component/api/proto/v1' into a Python Wheel
  novaeco build client

  # Build client from a custom proto location with a specific service name
  novaeco build client --proto-dir api/protos --out-dir dist/sdk --service-name custom-auth

  # --- Service Packaging ---
  # Package the current service source code for Docker deployment
  novaeco build service

  # Package a service with a non-standard source directory
  novaeco build service --src-dir app/src --out-dir build_artifacts --reqs requirements-prod.txt
"""

    parser = subparsers.add_parser(
        "build", 
        help="Build artifacts (SDKs, Docker images, Service packages)",
        formatter_class=argparse.RawDescriptionHelpFormatter, # Required to preserve newlines in examples
        epilog=examples
    )
    
    build_subs = parser.add_subparsers(dest="build_command", required=True)
    
    # --- 1. Client Builder ---
    # Compiles ProtoBufs into a Python Client SDK package (.whl)
    p_client = build_subs.add_parser("client", help="Compile ProtoBufs into a Python Client SDK")
    p_client.add_argument("--proto-dir", default="component/api/proto/v1", help="Directory containing .proto files")
    p_client.add_argument("--out-dir", default="dist/client", help="Staging directory for the build")
    p_client.add_argument("--service-name", help="Override service name (defaults to repo folder name)")

    # --- 2. Service Builder ---
    # Packages the service source code and requirements for Docker deployment (.tar.gz)
    p_service = build_subs.add_parser("service", help="Package Service for Deployment")
    p_service.add_argument("--src-dir", default="src", help="Source code root directory")
    p_service.add_argument("--out-dir", default="dist", help="Output directory for the tarball")
    p_service.add_argument("--reqs", default="requirements.txt", help="Primary requirements file")

def clean_dir(path):
    """Ensures a directory exists and is empty."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def get_version():
    """Tries to find a version source of truth from standard locations."""
    # Priority: GLOBAL_VERSION (Repo root) -> Component Version -> API Version
    candidates = ["GLOBAL_VERSION", "component/api/VERSION", "api/VERSION", "VERSION"]
    for c in candidates:
        if os.path.exists(c):
            with open(c, 'r') as f:
                return f.read().strip()
    return "0.0.1-dev" # Fallback if no version file is found

def fix_imports(package_dir):
    """
    Replicates the 'sed' logic to fix relative imports in generated gRPC files.
    Changes 'import foo_pb2' to 'from . import foo_pb2' so it works as a package.
    """
    print(f"🔧 Fixing relative imports in {package_dir}...")
    for filepath in glob.glob(os.path.join(package_dir, "*_pb2_grpc.py")):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Regex to find standard proto imports and make them relative
        # Matches: import some_file_pb2 as ... or just import some_file_pb2
        content = re.sub(r'import (\w+_pb2)', r'from . import \1', content)
        
        with open(filepath, 'w') as f:
            f.write(content)

def execute_client_build(args):
    cwd = os.getcwd()
    # Resolve paths relative to current working directory
    proto_dir = os.path.join(cwd, args.proto_dir)
    out_dir = os.path.join(cwd, args.out_dir)
    
    # Auto-detect service name from folder (e.g., 'novaagro')
    service_name = args.service_name or os.path.basename(cwd)
    # Python packages usually use underscores (novaagro_client)
    package_name = f"{service_name.replace('-', '_')}_client" 
    package_dir = os.path.join(out_dir, package_name)
    version = get_version()

    print(f"📦 Building Client SDK: {package_name} v{version}")
    print(f"   Proto Source: {proto_dir}")

    # 1. Clean & Init Staging Area
    clean_dir(out_dir)
    os.makedirs(package_dir)
    
    # 2. Compile ProtoBuf -> Python
    # We use the grpc_tools module via subprocess to generate code
    protos = glob.glob(os.path.join(proto_dir, "*.proto"))
    if not protos:
        print(f"❌ No .proto files found in {proto_dir}")
        sys.exit(1)

    print(f"   Compiling {len(protos)} proto files...")
    # protoc command construction
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={package_dir}",
        f"--grpc_python_out={package_dir}",
    ] + protos
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Protoc compilation failed: {e}")
        sys.exit(1)

    # 3. Fix Relative Imports (The Python gRPC gotcha)
    fix_imports(package_dir)

    # 4. Create __init__.py to make it a valid Python package
    Path(os.path.join(package_dir, "__init__.py")).touch()

    # 5. Generate setup.py dynamically
    # This allows the artifact to be pip installed
    setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{service_name}-client",
    version="{version}",
    packages=find_packages(),
    install_requires=[
        "grpcio>=1.60.0",
        "protobuf>=4.25.1"
    ],
    description="Auto-generated gRPC client for {service_name}",
)
"""
    with open(os.path.join(out_dir, "setup.py"), 'w') as f:
        f.write(setup_content)

    # 6. Build the Wheel artifact
    print("   Building Wheel artifact...")
    try:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel"], 
            cwd=out_dir, 
            check=True,
            stdout=subprocess.DEVNULL # Silence the verbose build output
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Wheel build failed: {e}")
        sys.exit(1)

    # List the result
    dist_output = os.path.join(out_dir, "dist")
    if os.path.exists(dist_output):
        artifacts = os.listdir(dist_output)
        print(f"✅ Success! Artifacts generated in {dist_output}:")
        for a in artifacts:
            print(f"   - {a}")
    else:
        print("⚠️  Warning: Build command succeeded but dist folder is missing.")

def execute_service_build(args):
    cwd = os.getcwd()
    dist_dir = os.path.join(cwd, args.out_dir)
    src_dir = os.path.join(cwd, args.src_dir)
    service_name = os.path.basename(cwd) # e.g., 'auth' or 'novaagro'
    
    # Clean & Init
    # Only clean if it's not the same as source (sanity check)
    if os.path.exists(dist_dir) and os.path.abspath(dist_dir) != os.path.abspath(cwd):
         shutil.rmtree(dist_dir)
    
    os.makedirs(dist_dir, exist_ok=True)

    print(f"📦 Packaging Service Artifact: {service_name}...")

    # Define the output tarball name
    # Convention: novaeco-[service].tar.gz
    tar_name = f"novaeco-{service_name}.tar.gz"
    tar_path = os.path.join(dist_dir, tar_name)

    print(f"   Source: {src_dir}")
    print(f"   Target: {tar_path}")

    # Create the Tarball directly
    # This effectively creates the 'build context' for Docker
    with tarfile.open(tar_path, "w:gz") as tar:
        # 1. Add Source Code (The App)
        if os.path.exists(src_dir):
            print(f"   + Adding {args.src_dir}/")
            tar.add(src_dir, arcname="src")
        else:
            print(f"❌ Error: Source directory '{src_dir}' not found.")
            sys.exit(1)

        # 2. Add Requirements (Critical for Docker install)
        # We look for the primary reqs file + the internal one
        req_files = [args.reqs, "requirements-internal.txt"]
        
        for req in req_files:
            if os.path.exists(req):
                print(f"   + Adding {req}")
                tar.add(req, arcname=req)

        # 3. Add Configs (Optional but common)
        if os.path.exists("pyproject.toml"):
            print("   + Adding pyproject.toml")
            tar.add("pyproject.toml", arcname="pyproject.toml")
            
    print(f"✅ Service Artifact Created: {tar_path}")

def execute(args):
    """Dispatch based on the build sub-command."""
    if args.build_command == "client":
        execute_client_build(args)
    elif args.build_command == "service":
        execute_service_build(args)
    else:
        print(f"Unknown build command: {args.build_command}")
        sys.exit(1)