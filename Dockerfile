# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

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

# Copy installed packages from builder
COPY --from=builder /root/.cache/uv/ ./.uv-cache
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY app/ ./app/
COPY content/ ./content/
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY alembic/alembic.ini ./alembic.ini
# (gallery.db is not copied; it will be created on first run by Alembic migrations)
COPY .env.example ./.env.example

# Expose port
EXPOSE 8000

# Ensure CLI tools (alembic, uvicorn) are in PATH
ENV PATH="/usr/local/bin:${PATH}"

# Run migrations and then start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
