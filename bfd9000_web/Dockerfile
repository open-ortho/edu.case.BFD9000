# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies required for building python packages
# gcc is often needed for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
# We copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
# (Add libpq-dev here if/when we switch to Postgres)
# libmagic1 is required for python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install packages
RUN pip install --no-cache-dir /wheels/*

# Copy project code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user for security
RUN useradd -m django
RUN chown -R django:django /app
USER django

# Expose port
EXPOSE 9000

# Default command
CMD ["gunicorn", "BFD9000.wsgi:application", "--bind", "0.0.0.0:9000"]
