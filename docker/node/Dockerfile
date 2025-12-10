# Start from a stable, slim Node.js base
FROM node:20-bullseye-slim

# Install common system dependencies and dev tools
# Added ca-certificates so git can verify HTTPS connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    curl \
    bash \
    zsh \
    # Add any other common, system-level tools
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install common global Node.js tools
# Pin versions to prevent "works on my machine" drift.
# We explicitly list the versions we want to lock into the platform.
RUN npm install -g \
    nodemon@3.1.11 \
    typescript@5.9.3

# The base 'node' image already includes a non-root 'node' user
USER node

# Set a default working directory
WORKDIR /workspace