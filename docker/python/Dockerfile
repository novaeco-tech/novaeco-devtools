# Start from a stable, slim Python base
FROM python:3.11-slim-bullseye

# Set environment variables to optimize Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    # Set the Playwright path globally so all users can find the browsers
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install common system dependencies and dev tools
# Added ca-certificates so git can verify HTTPS connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    curl \
    gnupg \
    bash \
    zsh \
    protobuf-compiler \
    # Add any other common, system-level tools your team needs
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install common Python development tools
RUN pip install --no-cache-dir \
    black \
    flake8 \
    pytest \
    mypy \
    playwright \
    grpcio \
    grpcio-tools

# Install Playwright Browsers & OS Dependencies
# We do this as ROOT before creating the appuser so it's globally available.
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH \
    && playwright install --with-deps \
    && chmod -R 777 $PLAYWRIGHT_BROWSERS_PATH

# Create a non-root user for security
RUN useradd -m -s /bin/bash appuser
USER appuser

# Set a default working directory
WORKDIR /workspace