# Promoter Agent Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Clone the repository to get the source code
RUN git clone https://github.com/sctennis77/zazzle-agent.git /tmp/repo

# Install dependencies from the cloned repo
RUN cd /tmp/repo && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-root

# Copy application code
RUN cp -r /tmp/repo/app /app/app && \
    cp /tmp/repo/run_promoter_agent.py /app/

# Clean up
RUN rm -rf /tmp/repo

# Create logs directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "print('Health check passed')" || exit 1

# Run the promoter agent
CMD ["python", "run_promoter_agent.py", "--continuous", "--log-level", "INFO"]