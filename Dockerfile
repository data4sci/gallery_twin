# 1. Use official Python image
FROM python:3.12-slim

# 2. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set working directory in container
WORKDIR /app

# 4. Install uv
RUN pip install uv

# 5. Copy dependency files
COPY pyproject.toml uv.lock ./

# 6. Install project dependencies
RUN uv sync

# 7. Copy rest of application code
COPY ./app ./app
COPY ./content ./content
COPY ./static ./static
COPY ./alembic ./alembic

# 8. Set non-sensitive default environment variables
ENV DATABASE_URL="sqlite+aiosqlite:///./db/gallery.db"
ENV DEBUG="false"
ENV SESSION_TTL="2592000"
ENV ALLOWED_ORIGINS='["*"]'

# 9. Expose port where application will run
EXPOSE 8000

# 10. Run migrations and start application
CMD uv run alembic -c alembic/alembic.ini upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
