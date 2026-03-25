# ==============================================================================
# NovaEco Unified Development Image
# ==============================================================================
# Base: Debian 12 (Bookworm) via Python Official Image
# Contains: Python 3.11 + Node.js 20 (LTS) + C++20/23 Toolchain (GCC 12 & Clang)
# Usage: CI/CD Pipelines and Local DevContainers
# ==============================================================================

FROM python:3.11-bookworm

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    # Global location for Playwright browsers so they persist across user switches
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    # Global Conan home so both 'root' (CI) and 'appuser' (Local Dev) share the cache
    CONAN_HOME=/opt/conan \
    # Node Version
    NODE_MAJOR=20 \
    # Hint for CMake to prefer modern C++
    CMAKE_CXX_STANDARD=20

# --- 1. System Dependencies & Modern C++ Toolchain ---
# We use --fix-missing to handle transient network issues in CI
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    # Basic Utilities
    ca-certificates \
    curl \
    gnupg \
    git \
    jq \
    bash \
    zsh \
    openssh-client \
    # C++ Build System (GCC 12+ supports C++20/23)
    build-essential \
    # Add Clang/LLVM for modern C++ cross-compilation support & faster linking
    clang \
    lld \
    # Debugging & Build Tools
    gdb \
    ninja-build \
    # Protocol Buffers Compiler (Host)
    protobuf-compiler \
    libprotobuf-dev \
    # OpenSSL for C++ Extensions
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- 2. Python Build Tools (Core Prerequisites) ---
# We isolate these so Conan and CMake are available for the C++ build.
RUN pip install --no-cache-dir \
    cmake==4.2.1 \
    ninja==1.13.0 \
    conan==2.25.2 \
    build==1.4.0 \
    scikit-build-core==0.12.0 \
    pybind11==2.13.6

# --- 3. Pre-build Heavy C++ Dependencies (Conan Cache) ---
# Protected by the layers above. Bumping Node or Linters will no longer break this 40-minute cache!
RUN mkdir -p /opt/conan && chmod 777 /opt/conan && \
    echo "[requires]\ngrpc/1.54.3\nyaml-cpp/0.8.0\ngtest/1.13.0\npybind11/2.10.4\nbenchmark/1.8.3\njwt-cpp/0.7.0" > /tmp/conanfile.txt && \
    conan profile detect --force && \
    # Build Release binaries (For CI and Production wheels)
    conan install /tmp/conanfile.txt --build=missing -s compiler.cppstd=20 -s build_type=Release && \
    # Build Debug binaries (For Local DevContainer GDB debugging)
    conan install /tmp/conanfile.txt --build=missing -s compiler.cppstd=20 -s build_type=Debug && \
    # Cleanup and ensure appuser can read/write to the cache
    rm /tmp/conanfile.txt && \
    chmod -R 777 /opt/conan

# --- 4. Install Node.js 20 (Official Source) ---
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g npm@latest nodemon@3.1.11 typescript@5.9.3

# --- 5. Python Ecosystem Toolchain (High Churn Layer) ---
RUN pip install --no-cache-dir \
    # Core Utilities
    requests==2.32.5 \
    rich==13.5.3 \
    # Linters & Formatters
    ruff==0.4.4 \
    mypy==1.19.0 \
    autotyping==24.9.0 \
    doc8==2.0.0 \
    rstcheck==6.2.0 \
    # Testing
    pytest==8.0.0 \
    pytest-cov==7.0.0 \
    pytest-asyncio==0.23.8 \
    pytest-benchmark==4.0.0 \
    openapi-spec-validator==0.7.1 \
    pyyaml==6.0.1 \
    # Communication (gRPC)
    grpcio==1.76.0 \
    grpcio-tools==1.76.0 \
    protobuf==6.33.4 \
    # Type Stubs
    types-protobuf==6.32.1.20251210 \
    types-requests==2.32.4.20260107 \
    types-PyYAML==6.0.12.20250915 \
    # Web Framework (FastAPI)
    fastapi==0.115.4 \
    uvicorn==0.40.0 \
    httpx==0.28.1 \
    # Utilities
    pydantic==2.12.5 \
    pyjwt[crypto]==2.11.0 \
    cryptography==46.0.5 \
    nats-py==2.7.2 \
    kubernetes==29.0.0 \
    sphinx==8.2.3 \
    sphinx-needs==6.3.0 \
    sphinx-copybutton==0.5.2 \
    sphinx-data-viewer==0.1.5 \
    sphinx-design==0.7.0 \
    sphinxcontrib-mermaid==2.0.0 \
    sphinxcontrib-openapi==0.9.0 \
    myst-parser==5.0.0 \
    furo==2025.12.19 \
    sphinx-autobuild==2025.8.25 \
    # Security (SAST)
    bandit==1.9.3 \
    semgrep==1.149.0 \
    # E2E Automation
    playwright==1.57.0 \
    pytest-playwright==0.5.0 \
    axe-playwright-python==0.1.7

# --- 6. Playwright Browsers (System-Wide Install) ---
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH \
    && playwright install --with-deps \
    && chmod -R 777 $PLAYWRIGHT_BROWSERS_PATH

# --- 7. User Setup (Non-Root) ---
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set Defaults
USER appuser
WORKDIR /workspace
CMD ["/bin/bash"]