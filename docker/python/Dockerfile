# ==============================================================================
# NovaEco Python Development Image
# ==============================================================================
# Base: Debian 12 (Bookworm) - Matches 'unified' image base
# Usage: Python-specific microservices (e.g. Analysis, Risk Service)
# ==============================================================================

FROM python:3.11-bookworm

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    # Standard for modern CMake
    CMAKE_CXX_STANDARD=20

# --- 1. System Dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    ca-certificates \
    curl \
    gnupg \
    git \
    jq \
    bash \
    zsh \
    openssh-client \
    # Toolchain for compiling C++ Extensions (e.g. gateway-core)
    build-essential \
    clang \
    lld \
    gdb \
    ninja-build \
    # Protobuf Host Compiler
    protobuf-compiler \
    libprotobuf-dev \
    # Doc Support
    default-jre \
    graphviz \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- 2. Python Toolchain (Aligned with Unified) ---
RUN pip install --no-cache-dir \
    requests==2.32.5 \
    rich==13.5.3 \
    black==25.12.0 \
    flake8==7.3.0 \
    ruff==0.4.4 \
    mypy==1.19.0 \
    pytest==8.0.0 \
    pytest-cov==7.0.0 \
    pytest-asyncio==0.23.8 \
    pytest-benchmark==4.0.0 \
    openapi-spec-validator==0.7.1 \
    pyyaml==6.0.1 \
    build==1.4.0 \
    scikit-build-core==0.12.0 \
    # Modern CMake for banditC++20 support
    cmake==4.2.1 \
    ninja==1.13.0 \
    conan==2.25.2 \
    # Latest stack
    grpcio==1.76.0 \
    grpcio-tools==1.76.0 \
    protobuf==6.33.4 \
    sphinx==8.2.3 \
    sphinx-needs==6.3.0 \
    sphinx-copybutton==0.5.2 \
    sphinx-data-viewer==0.1.5 \
    sphinxcontrib-mermaid==2.0.0 \
    myst-parser==5.0.0 \
    furo==2025.12.19 \
    bandit==1.9.3 \
    semgrep==1.149.0 \
    # E2E Automation
    playwright==1.57.0 \
    pytest-playwright==0.5.0 \
    axe-playwright-python==0.1.7

# --- 3. Browser & User Setup ---
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH \
    && playwright install --with-deps \
    && chmod -R 777 $PLAYWRIGHT_BROWSERS_PATH

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

USER appuser
WORKDIR /workspace
CMD ["/bin/bash"]