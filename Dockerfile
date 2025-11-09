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

# 8. Create database directory PŘED nastavením ENV
RUN mkdir -p /home/data/db

# 9. Set environment variables for Azure
ENV DATABASE_URL="sqlite+aiosqlite:///home/data/db/gallery.db"
ENV DEBUG="false"
ENV SESSION_TTL="2592000"
ENV ALLOWED_ORIGINS='["*"]'

# 10. Expose port where application will run
EXPOSE 8000

# 11. Create startup script
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

CMD ["/startup.sh"]