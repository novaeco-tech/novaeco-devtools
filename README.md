# NovaEco DevTools

This repository hosts shared developer tooling, Docker images, and scripts used across the NovaEco organization.

## 🛠️ NovaEco CLI

The **NovaEco CLI** (package: `novaeco-cli`) is our internal Python tool used to manage versioning, releases, and automation across our monorepos and microservices.

### Installation

Since this is an internal tool, we install it directly from the repository source. You do not need to configure a private registry.

**1. Install the latest version:**
```bash
# Note: The package is located in the 'novaeco-cli' subdirectory
pip install "git+https://github.com/novaeco-tech/ecosystem-devtools.git@main#subdirectory=novaeco-cli"
````

**2. Update to the latest version:**
If a teammate pushes a fix, run this to update your local machine:

```bash
pip install --upgrade "git+https://github.com/novaeco-tech/ecosystem-devtools.git@main#subdirectory=novaeco-cli"
```

-----

## ⚡ Environment Setup (Bootstrap)

New developers can bootstrap the entire NovaEco environment (cloning all repositories and generating a unified VS Code workspace) using the `novaeco init` command. This replaces manual cloning and configuration.

### Prerequisites

1.  **Python 3.10+**
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
2.  Dynamically sort repositories based on their topics (`ecosystem`, `enabler`, `sector`, etc.).
3.  Clone all missing repositories into a `./repos` directory.
4.  Generate a `novaeco.code-workspace` file configured with the correct folder structure.

**2. Open the Workspace:**
Open the generated workspace file in VS Code to see the full "System-of-Systems" view:

```bash
code novaeco.code-workspace
```

-----

## 📦 Versioning & Release Management

Once your environment is set up, use the CLI to manage service versions.

**1. Patching a Service**
Used when fixing bugs. Increments the patch version (e.g., `1.0.0` -\> `1.0.1`) for a specific service.

```bash
# Syntax: novaeco version patch <service_name>
novaeco version patch auth
novaeco version patch api
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

| Image | Tag | Description |
| :--- | :--- | :--- |
| `ghcr.io/novaeco/dev-python` | `latest` | Python 3.10, Flask, Pytest, and common utilities. |
| `ghcr.io/novaeco/dev-node` | `latest` | Node.js 18, npm, and Docusaurus support. |

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
