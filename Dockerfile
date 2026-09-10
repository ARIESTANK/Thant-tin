# Step 1: Base image with shared environment variables
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKDIR=/app

WORKDIR ${WORKDIR}

# Install system dependencies (C compiler, libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project code
COPY . .

# Collect static files (requires SECRET_KEY; fallback provided for build time)
RUN SECRET_KEY=dummy-build-key python manage.py collectstatic --noinput

# Step 3: Production Runner
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy installed packages and built static files from base
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /app /app

# Create a non-root user for security
RUN useradd -m django-user && chown -R django-user:django-user /app
USER django-user

EXPOSE 8000

# Run database migrations and start Gunicorn WSGI server
# (Replace `config.wsgi:application` with `<your_project_name>.wsgi:application`)
CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application"]