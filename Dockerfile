# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy only necessary files for dependency installation
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync

# Stage 2: Runner
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.cache/uv/ ./.uv-cache
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

# Copy application code
COPY app/ ./app/
COPY content/ ./content/
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY gallery.db ./gallery.db
COPY .env.example ./.env.example

# Expose port
EXPOSE 8000

# Run migrations and then start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
