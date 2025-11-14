# Nova Ecosystem: Development Tools

This repository is a "factory," not a "product." Its sole purpose is to build, test, and publish the common, pre-built base images used for development (DevContainers) across all repositories in the nova-ecosystem organization.

Centralizing these base images gives us two major advantages:

- **Speed**: DevContainer startup for any pillar is nearly instant, as developers pull a pre-built image instead of building one from scratch.
- **Consistency**: Every developer runs on the exact same set of tools and dependencies, eliminating "it works on my machine" issues.

## 📦 Published Images

This repository builds and publishes the following images to the GitHub Container Registry (GHCR):

- `ghcr.io/nova-ecosystem/dev-python:latest`
- `ghcr.io/nova-ecosystem/dev-node:latest`

## 🚀 How to Use These Images

**Do not clone this repository for pillar development.**

Instead, in your pillar monorepos (e.g., `ecosystem-core`, `hub`), reference these images in your `.devcontainer/docker-compose.yml` file.

### Example: `.devcontainer/docker-compose.yml`

This example from `ecosystem-core` shows how to use the pre-built images. Notice the `image:` key is used instead of `build:`.

```yaml
version: '3.8'

services:
    app:
        # Uses the pre-built Node.js dev image
        image: ghcr.io/nova-ecosystem/dev-node:latest
        volumes:
            - ../app:/workspace  # We can still add local-only needs
        command: sleep infinity  # Keep container alive

    api:
        # Uses the pre-built Python dev image
        image: ghcr.io/nova-ecosystem/dev-python:latest
        volumes:
            - ../api:/workspace
        command: sleep infinity

    auth:
        # Re-uses the same Python dev image
        image: ghcr.io/nova-ecosystem/dev-python:latest
        volumes:
            - ../auth:/workspace
        command: sleep infinity
```
