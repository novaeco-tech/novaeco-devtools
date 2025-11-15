# Nova Ecosystem: Development Tools

This repository is a "factory," not a "product." Its sole purpose is to build, test, and publish the common, pre-built base images used for development (DevContainers) across all repositories in the `nova-ecosystem` organization.

Centralizing these base images gives us two major advantages:

1.  **Speed:** DevContainer startup for any monorepo is nearly instant, as developers pull a pre-built image instead of building one from scratch.
2.  **Consistency:** Every developer runs on the exact same set of tools and dependencies, eliminating "it works on my machine" issues.

## 📦 Published Images

This repository builds and publishes the following images to the GitHub Container Registry (GHCR):

  * `ghcr.io/nova-ecosystem/dev-python:latest` (For API/Worker services)
  * `ghcr.io/nova-ecosystem/dev-node:latest` (For App/Website services)

-----

## 🚀 Consumer Guide: How to Use These Images

**For Developers working on Pillars (Hub, Agro, Finance):**

Do **not** clone this repository. Instead, in your pillar monorepo (e.g., `hub`), reference these images in your `.devcontainer/docker-compose.yml` file.

### Example: `hub/.devcontainer/docker-compose.yml`

Notice the `image:` key is used instead of `build:`.

```yaml
version: '3.8'
services:
  app:
    # Uses the pre-built Node.js dev image
    image: ghcr.io/nova-ecosystem/dev-node:latest
    volumes:
      - ..:/workspace:cached
    working_dir: /workspace/app
    command: sleep infinity

  api:
    # Uses the pre-built Python dev image
    image: ghcr.io/nova-ecosystem/dev-python:latest
    volumes:
      - ..:/workspace:cached
    working_dir: /workspace/api
    command: sleep infinity
```

---

## 🛠️ Maintainer Guide: How to Develop This Repo

**For DevOps Engineers modifying the base images:**

This repository creates the foundation for everyone else. Since it cannot depend on itself, it uses a standard **Docker-in-Docker** environment for its own development.

### 1. Bootstrapping Your Environment
1. Clone this repository.
2. Open it in VS Code.
3. When prompted, click **"Reopen in Container"**.
   * *Note: This uses a generic `mcr.microsoft.com/devcontainers/base:ubuntu` image defined in this repo's `.devcontainer/` folder.*

### 2. Building & Testing Locally
You can build the images locally to verify your changes before pushing.

```bash
# Build the Python image locally to test
docker build -t test-python ./python

# Build the Node image locally to test
docker build -t test-node ./node
````

### 3\. Publishing New Versions

Do not manually push images to GHCR from your laptop.

1.  Commit your changes to the `main` branch.
2.  The **GitHub Actions Workflow** (`publish-dev-images.yml`) will automatically trigger.
3.  It will build the images and push them to `ghcr.io/nova-ecosystem/...`.
4.  Other developers can pull the new updates by running `Dev Containers: Rebuild Container` in their repos.
