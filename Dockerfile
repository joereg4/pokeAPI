FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for psycopg2 and cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create logs directory and set up cron
RUN mkdir -p /app/logs \
    && chmod +x /app/docker/cron/rotate_logs.sh \
    && chmod +x /app/docker/entrypoint.sh \
    && crontab /app/docker/cron/crontab

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Start cron and gunicorn
CMD ["sh", "-c", "cron && exec gunicorn --workers 3 --timeout 300 --bind 0.0.0.0:8000 --access-logfile /app/logs/gunicorn-access.log --error-logfile /app/logs/gunicorn-error.log 'app:create_app()'"]
