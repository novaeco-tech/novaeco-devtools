# ==============================================================================
# NovaEco Node.js Development Image
# ==============================================================================
# Base: Debian 12 (Bookworm) - Matches 'unified' image base
# Usage: Frontend Apps (novaeco-app-web) and Documentation Website
# ==============================================================================

FROM node:20-bookworm-slim

# --- Environment Configuration ---
# Ensure consistent behavior for tools that rely on python
ENV PYTHONUNBUFFERED=1

# --- 1. System Dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    git \
    openssh-client \
    curl \
    bash \
    zsh \
    # Install Python 3 (Will be 3.11+ on Bookworm) for NovaEco CLI support
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- 2. Global Node Tools (Pinned) ---
RUN npm install -g \
    npm@latest \
    nodemon@3.1.11 \
    typescript@5.9.3 \
    pnpm@9.0.0

# --- 3. User Configuration ---
# Node image provides 'node' user (UID 1000) by default
USER node
WORKDIR /workspace
CMD ["/bin/bash"]