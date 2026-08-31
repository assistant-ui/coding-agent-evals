FROM node:24-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
  && apt-get install --yes --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    netcat-openbsd \
    procps \
    python3 \
    python3-pip \
  && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    "pytest==8.3.5" \
    "playwright==1.62.0" \
    "pytest-playwright==0.9.0" \
  && python3 -m playwright install --with-deps chromium

# Packed from this checkout by scripts/refresh-mcp-package.sh (not live npm).
COPY mcp-docs-server.tgz /opt/mcp-docs-server.tgz
RUN npm install --global /opt/mcp-docs-server.tgz

WORKDIR /workspace

COPY --from=ghcr.io/blaxel-ai/sandbox:latest /sandbox-api /usr/local/bin/sandbox-api
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
