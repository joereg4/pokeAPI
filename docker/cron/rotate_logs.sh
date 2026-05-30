#!/bin/bash

# Log rotation for Docker container
LOG_DIR="/app/logs"

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$LOG_DIR/backups"
mkdir -p "$BACKUP_DIR"

if ls "$LOG_DIR"/*.log 1> /dev/null 2>&1; then
    tar -czf "$BACKUP_DIR/logs_backup_$TIMESTAMP.tar.gz" "$LOG_DIR"/*.log
    find "$LOG_DIR" -name "*.log" -type f -exec truncate -s 0 {} \;
fi

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "logs_backup_*.tar.gz" -type f -mtime +30 -delete

echo "Log cleanup completed at $(date)" >> "$LOG_DIR/cleanup_history.log"
