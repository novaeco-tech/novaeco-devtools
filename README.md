# 🌍 NovaEco DevTools

**NovaEco** is the open‑source **Digital Public Infrastructure** for the circular economy.

This repository hosts shared developer tooling, Docker images, and scripts used to build the NovaEco **System-of-Systems**.

## 🛠️ NovaEco CLI

The **NovaEco CLI** (package: `novaeco-cli`) is our internal Python tool used to manage versioning, releases, automation, and compliance across our monorepos and microservices.

### Installation

Since this is an internal tool, we install it directly from the repository source.
You do not need to configure a private registry.

**1. Install the latest version:**

```bash
# Note: The package is located in the 'novaeco-cli' subdirectory
pipx install "git+https://github.com/novaeco-tech/novaeco-devtools.git@main#subdirectory=novaeco-cli"
```

**2. Configure your PATH (Important):**
If you see a warning during installation like:

> *WARNING: The script novaeco is installed in '/home/user/.local/bin' which is not on PATH.*

You must add that directory to your shell configuration so your terminal can find the `novaeco` command.

**For Zsh users (default on macOS & newer Linux):**

```bash
echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.zshrc
source ~/.zshrc
```

**For Bash users:**

```bash
echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

**3. Update to the latest version:**
If a teammate pushes a fix, run this to update your local machine:

```bash
pipx install --upgrade "git+https://github.com/novaeco-tech/novaeco-devtools.git@main#subdirectory=novaeco-cli"
```

-----

## ⚡ Environment Setup (Bootstrap)

New developers can bootstrap the entire NovaEco environment (cloning all repositories and generating a unified VS Code workspace) using the `novaeco init` command. This replaces manual cloning and configuration.

### Prerequisites

1.  **Python 3.11+**
2.  **Git**
3.  **GitHub CLI (`gh`)** — [Installation Guide](https://cli.github.com/)
      * *Note: You must run `gh auth login` to authenticate before initializing the environment.*

### Usage

**1. Initialize the Environment:**
Navigate to the folder where you want your project root to be, then run:

```bash
novaeco init
```

This command will:

1.  Query the `novaeco-tech` GitHub organization.
2.  Dynamically sort repositories based on the architecture topics (Meta, Core, Tooling, Governance, Enablers, Sectors, Workers, Products).
3.  Clone all missing repositories into a `./repos` directory.
4.  Generate a `novaeco.code-workspace` file configured with the correct folder structure.

**2. Open the Workspace:**
Open the generated workspace file in VS Code to see the full "System-of-Systems" view:

```bash
code novaeco.code-workspace
```

-----

## 📄 AI Context Export

Easily bundle your codebase into a single text file (`context.txt`) to provide clear context for AI coding assistants (ChatGPT, Claude, Gemini). The tool automatically ignores binary files, lock files, and common noise.

**1. Export everything in the current directory:**

```bash
# Exports to 'context.txt' by default
novaeco export .
```

**2. Export a specific repository or subdirectory:**

```bash
# Useful when targeting a specific service
novaeco export ./repos/novaeco-devtools/novaeco-cli
```

**3. Export a specific file:**

```bash
novaeco export ./repos/novaeco-devtools/README.md
```

**4. Advanced Filtering:**
You can exclude specific extensions or paths to reduce noise.

```bash
# Exclude Python compiled files and the git folder
novaeco export . --exclude-exts pyc --exclude-dirs .git

# Exclude specific sensitive files
novaeco export . --exclude-paths "secrets.json" "legacy/"
```

-----

## 🔍 Audit & Compliance

To support our **V-Model Testing Strategy**, we provide tools to ensure every repository follows the standard architecture and that all requirements are verified by tests.

The audit commands are **context-aware**. They adapt their behavior based on where you run them or what arguments you provide.

**1. Structural Audit**
Checks if the repository matches the "Golden Template" for its type (`core`, `enabler`, `sector`, `worker`). It ensures essential files (Dockerfiles, workflows, requirement docs) are present.

```bash
# Mode A: Audit the current directory (Local Check)
cd repos/novaagro
novaeco audit structure

# Mode B: Audit specific repositories (Targeted Check)
novaeco audit structure novaagro novafin

# Mode C: Audit the entire workspace (Global Governance)
# Run this from the root of your workspace (where the 'repos/' folder is)
novaeco audit structure
```

**2. Traceability Matrix**
Scans documentation for Requirement IDs (e.g., `REQ-AGRO-FUNC-001`) and tests for verification tags (`@pytest.mark.requirement(...)`). It generates a coverage matrix to prove compliance.

```bash
# Check coverage for a single component
novaeco audit traceability novatrade

# Generate a compliance report for the entire ecosystem (Global)
novaeco audit traceability
```

-----

## 📦 Versioning & Release Management

Once your environment is set up and audited, use the CLI to manage service versions.

**1. Patching a Service**
Used when fixing bugs. Increments the patch version (e.g., `1.0.0` -\> `1.0.1`).

```bash
# Syntax: novaeco version patch <service_name>

# For Monorepos (Enablers/Sectors):
novaeco version patch api
novaeco version patch auth

# For Workers (Root-level versioning):
novaeco version patch worker
```

**2. Creating a Release**
Used when shipping new features.
Increments the Global version and aligns **all** services in the repository to the new version (e.g., `1.1.0`).

```bash
# Syntax: novaeco version release <minor|major>
novaeco version release minor
```

-----

## 🐳 Shared Docker Images

We maintain standard development images to ensure consistency across all engineers' machines.
These are automatically built and pushed to GHCR (GitHub Container Registry) whenever the `docker/` directory changes.
Tool versions are strictly pinned. 

| Image | Tag | Description |
| :--- | :--- | :--- |
| `ghcr.io/novaeco/dev-python` | `latest` | **Python 3.11**, Flask, Pytest, and `protobuf-compiler` (for gRPC). |
| `ghcr.io/novaeco/dev-node` | `latest` | **Node.js 20**, npm, and Docusaurus support. |

**Usage in `devcontainer.json`:**

```json
"image": "ghcr.io/novaeco/dev-python:latest"
```

-----

## 👩‍💻 Contributing to DevTools

### Developing the CLI

If you want to add new commands to the `novaeco` tool:

1.  Clone this repository.
2.  Install the package in "editable" mode (changes are reflected immediately):
    ```bash
    cd novaeco-cli
    pip install -e .
    ```
3.  Add your new module in `src/novaeco_cli/commands/`.
4.  Register the command in `src/novaeco_cli/main.py`.

### Publishing Updates

  * **Docker Images:** Push changes to the `docker/` folder to trigger a rebuild and publish to GHCR.
  * **NovaEco CLI:** Simply push changes to the `novaeco-cli/` folder on the `main` branch. Everyone using the "Git Install" method will receive the updates the next time they run the upgrade command or rebuild their DevContainer.