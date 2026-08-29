FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 10001 gomaa && \
    useradd -u 10001 -g gomaa -m -d /home/gomaa -s /bin/bash gomaa

# Copy source code and configuration
COPY gomaa/ ./gomaa/
COPY mnemosyne/ ./mnemosyne/
COPY pyproject.toml README.md ./

# Install package with production extras
RUN pip install --no-cache-dir ".[all]"

# Setup data directory and permissions
RUN mkdir -p /app/data /home/gomaa/.gomaa && \
    chown -R gomaa:gomaa /app /home/gomaa

ENV TOKENIZERS_PARALLELISM=false \
    HF_HUB_DISABLE_PROGRESS_BARS=1 \
    PYTHONUNBUFFERED=1

USER gomaa

# Default command starts Gomaa MCP server
CMD ["python", "-m", "gomaa", "server"]

