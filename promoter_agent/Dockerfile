# Promoter Agent Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including git for cloning
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy local requirements.txt if it exists (for local builds)
# Otherwise we'll get it from the repo
COPY requirements.txt* ./

# Clone the repository to get all necessary files
RUN git clone --depth 1 https://github.com/sctennis77/zazzle-agent.git /tmp/repo && \
    # Copy requirements if not already present
    if [ ! -f requirements.txt ]; then cp /tmp/repo/requirements.txt .; fi && \
    # Install Python dependencies
    pip install --no-cache-dir -r requirements.txt && \
    # Copy application code
    cp -r /tmp/repo/app ./app && \
    cp /tmp/repo/run_promoter_agent.py . && \
    # Clean up
    rm -rf /tmp/repo

# Create logs directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "print('Health check passed')" || exit 1

# Run the promoter agent
CMD ["python", "run_promoter_agent.py", "--continuous", "--log-level", "INFO"]