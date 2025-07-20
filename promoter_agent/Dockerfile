# Promoter Agent Service Dockerfile - Optimized for Railway
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim as production

WORKDIR /app

# Install runtime dependencies including git for repository access
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Clone repository to get necessary files (optimized approach)
# This is necessary because Railway builds with promoter_agent as context
RUN git clone --depth 1 https://github.com/sctennis77/zazzle-agent.git /tmp/repo && \
    # Copy only necessary application files
    cp -r /tmp/repo/app ./app && \
    cp /tmp/repo/run_promoter_agent.py . && \
    cp /tmp/repo/alembic.ini . && \
    cp -r /tmp/repo/alembic ./alembic && \
    # Clean up to reduce image size
    rm -rf /tmp/repo

# Create logs directory
RUN mkdir -p /app/logs

# Health check that verifies the service can import properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app'); from app.agents.clouvel_promoter_agent import ClouvelPromoterAgent; print('Health check passed')" || exit 1

# Run the promoter agent
CMD ["python", "run_promoter_agent.py", "--continuous", "--log-level", "INFO"]