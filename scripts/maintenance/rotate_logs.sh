#!/bin/bash

# Set log directory to match application location
LOG_DIR="/var/www/pokeAPI/logs"

# Ensure script fails on any error
set -e

# Get current timestamp for backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
BACKUP_DIR="$LOG_DIR/backups"
mkdir -p "$BACKUP_DIR"

# Check if there are any log files before attempting backup
if ls "$LOG_DIR"/*.log 1> /dev/null 2>&1; then
    # Backup logs before clearing
    tar -czf "$BACKUP_DIR/logs_backup_$TIMESTAMP.tar.gz" "$LOG_DIR"/*.log

    # Clear logs
    find "$LOG_DIR" -name "*.log" -type f -exec truncate -s 0 {} \;
fi

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "logs_backup_*.tar.gz" -type f -mtime +30 -delete

# Log the cleanup
echo "Log cleanup completed at $(date)" >> "$LOG_DIR/cleanup_history.log" 