# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv and required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy only necessary files for dependency installation
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync
RUN uv pip install --system -e .
RUN uv pip install --system alembic

# Stage 2: Runner
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY app/ ./app/
COPY content/ ./content/
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# Create db directory and set permissions
RUN mkdir -p /app/db && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Ensure CLI tools (alembic, uvicorn) are in PATH
ENV PATH="/usr/local/bin:${PATH}"

# Run migrations and then start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
