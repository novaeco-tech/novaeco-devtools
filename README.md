# 🛠️ NovaEco DevTools (Tools)

![Component ID](https://img.shields.io/badge/ID-TOOLS-orange)
![Layer](https://img.shields.io/badge/Layer-DevX-blue)
![Type](https://img.shields.io/badge/Type-CLI-green)

**The Force Multiplier.**

**NovaEco DevTools** (`novaeco-devtools`) is the engineering backbone of the platform.
It hosts the **NovaEco CLI** (`novaeco`), the internal Swiss Army Knife that automates the complex "System-of-Systems" workflow—from bootstrapping a new laptop to deploying a multi-service release.
It also defines the **Standard Development Environments** (DevContainers) used by engineers to write code.

> **Theoretical Context:** In a polyrepo architecture, "Context Switching" is the enemy.
This tooling implements **Unified Developer Experience** (ADR_KERNEL_0001)—abstracting away the complexity of 20+ Git repositories so engineers can treat the entire ecosystem as a single logical unit.
It also enforces **V-Model Compliance** by programmatically verifying that every Requirement has a matching Test.

---

## ⚡ Quick Start (Bootstrap)

New to the team? One command sets up your entire workstation.

### Prerequisites
* **Python 3.11+**
* **Git** & **GitHub CLI** (`gh auth login`)

### Installation
We use `pipx` to install the CLI globally in an isolated environment.

```bash
# Install (or Upgrade) the NovaEco CLI
pipx install --force "git+ssh://git@github.com/novaeco-tech/novaeco-devtools.git@v0.1.0#subdirectory=novaeco-cli"

```

### Initialize Workspace

Navigate to your work folder (e.g., `~/work/novaeco`) and run:

```bash
novaeco init

```

**What this does:**

1. **Discovery:** Queries the `novaeco-tech` GitHub org.
2. **Cloning:** Downloads all 20+ microservices into a `./repos/` directory.
3. **Workspace:** Generates a unified `novaeco.code-workspace` file for VS Code.

**Finally, open the workspace:**

```bash
code novaeco.code-workspace

```

---

## 📄 AI Context Export

Easily bundle your codebase into a single text file (`context.txt`) to provide clear context for AI coding assistants (ChatGPT, Claude, Gemini).
The tool automatically ignores binary files, lock files, and common noise.

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

**3. Advanced Filtering:**
You can exclude specific extensions or paths to reduce token usage.

```bash
# Exclude Python compiled files and the git folder
novaeco export . --exclude-exts pyc --exclude-dirs .git

# Exclude specific sensitive files
novaeco export . --exclude-paths "secrets.json" "legacy/"

```

---

## 🔍 Audit & Compliance (V-Model)

To support our quality standards, the CLI acts as a "Quality Gatekeeper" to ensure every repository follows the standard NovaEco architecture.

**1. Structural Audit:**
Checks if the current repository matches the folder template for its type (e.g., Service vs. Library).

```bash
# Run inside any repo
novaeco audit structure

```

**2. Traceability Matrix:**
Implements `REQ_DEVTOOLS_FUNCTIONAL_0001`. Scans documentation and tests to ensure requirements are verified.

```bash
# Scans for @trace annotations and maps them to Requirements
novaeco audit traceability

```

---

## 📦 Versioning & Release Management

Use the CLI to manage service versions across the ecosystem.

**1. Patching a Service:**
Used when fixing bugs. Increments the patch version (e.g., `1.0.0` -> `1.0.1`) and updates `pyproject.toml`.

```bash
# Syntax: novaeco version patch <service_name>
novaeco version patch api

```

**2. Creating a Release:**
Used when shipping new features.
Increments the local logic package version (SemVer) and generates changelogs.

```bash
# Syntax: novaeco version release <minor|major>
novaeco version release minor

```

---

## 🐳 Standard Development Environments

We maintain a **Unified Development Image** to ensure consistency across all engineers' machines, supporting our Hybrid C++/Python/Node architecture.

| Image | Tag | Description |
| --- | --- | --- |
| `ghcr.io/novaeco-tech/novaeco-dev-unified` | `latest` | **Unified Toolchain:** Python 3.11, Node.js 20, C++17 (GCC/CMake), Poetry, Git. |
| `ghcr.io/novaeco-tech/novaeco-dev-python` | `latest` | **Python 3.11**, Poetry, Git, Make, GCC. |
| `ghcr.io/novaeco-tech/novaeco-dev-node` | `latest` | **Node.js 20**, NPM, Cypress. |

> **⚠️ Important Distinction:**
> * **`novaeco-devtools` (Here):** Optimized for **Developer Experience** (includes debuggers, linters, shells).
> * **`novaeco-runtime` (Separate Repo):** Optimized for **Production Execution** (hardened, stripped, minimal footprint).
> 
> 

---

## 🔗 Traceability Matrix (V-Model)

This component implements specific requirements defined in the **NovaEco Kernel** and local component logic.

| Requirement ID | Type | Description | Source |
| --- | --- | --- | --- |
| **`NEED_OPERATIONS_0002`** | Need | **Standardized Tooling:** Consistent dev environment. | [Systemic Needs](../novaeco/docs/source/usecases/systemic_needs.rst) |
| **`REQ_DEVTOOLS_FUNCTIONAL_0001`** | Functional | **Compliance Scan:** Automated V-Model verification. | [Functional Reqs](docs/source/requirements/internal_functional.rst) |
| **`REQ_DEVTOOLS_INTERFACE_0001`** | Interface | **Unified Interface:** CLI must wrap Docker/Pytest. | [Interface Reqs](docs/source/requirements/interface.rst) |
| **`CONSTRAINT_ARCH_0002`** | Constraint | **Kernel Governance:** CLI enforces V-Model verification. | [Constraints](../novaeco/docs/source/architecture/constraints.rst) |
| **`USECASE_COMPLIANCE_0002`** | Use Case | **Action Reconstruction:** Cryptographic BoM audits. | [Compliance Domain](../novaeco/docs/source/usecases/compliance.rst) |
| **`NEED_COMPLIANCE_0001`** | Need | **Regulatory Auditability:** Verifiable action reconstruction. | [Systemic Needs](../novaeco/docs/source/usecases/systemic_needs.rst) |

---

## 👩‍💻 Contributing to DevTools

### Developing the CLI

If you want to add new commands (e.g., `novaeco deploy`):

1. **Clone:** `git clone .../novaeco-devtools.git`
2. **Install Editable:**

```bash
cd novaeco-cli
pip install -e .

```

3. **Code:** Add your module in `src/novaeco_cli/commands/`.
4. **Test:** Your changes are reflected immediately when you run `novaeco`.

### Updating DevContainers

The `docker/` folder contains the source for our Development Images.

* **Push to Main:** Triggers a GitHub Action to rebuild and push `ghcr.io/novaeco-tech/novaeco-dev-unified`.
* **Usage:** These are consumed by `.devcontainer/devcontainer.json` files across the ecosystem.
