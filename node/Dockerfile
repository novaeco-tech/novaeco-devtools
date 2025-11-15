# Start from a stable, slim Node.js base
FROM node:20-bullseye-slim

# Install common system dependencies and dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    bash \
    zsh \
    # Add any other common, system-level tools
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install common global Node.js tools
# NOTE: We removed 'yarn' from this list because it is already 
# pre-installed in the base 'node' image.
RUN npm install -g \
    nodemon \
    typescript

# The base 'node' image already includes a non-root 'node' user
USER node

# Set a default working directory
WORKDIR /workspace