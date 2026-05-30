# Database Management Scripts

This document describes the database management scripts available for syncing data between local development and production environments.

## Overview

The database management system consists of two main scripts:

1. **`scripts/upload_pokemon_summaries.py`** - Upload specific resource types from local to production
2. **`scripts/backup_db.py`** - Create full database backups and restore functionality

Both scripts include automatic backup creation and cleanup to ensure data safety.

## Prerequisites

### Required Dependencies

Install the required Python packages:

```bash
.venv/bin/pip install -r requirements.txt
```

### SSH Tunnel Setup

For secure connections to production, establish an SSH tunnel (operator-only — set `PROD_SSH_HOST` in your private `.env`; not required for local/Docker use):

```bash
ssh -L 5433:localhost:5432 ${PROD_SSH_USER:-root}@${PROD_SSH_HOST:?set PROD_SSH_HOST in .env}
```

Keep this tunnel active while running the scripts.

## Upload Script: `upload_pokemon_summaries.py`

### Purpose

Uploads specific resource types (Pokemon summaries, abilities, moves, etc.) from your local development database to production. Includes automatic backup creation before each upload.

### Features

- **Forced Backup**: Creates a backup before every upload operation
- **Resource-Specific**: Upload only specific resource types (pokemon, ability, move, etc.)
- **Dry-Run Mode**: Preview changes without applying them
- **Automatic Cleanup**: Keeps 7 most recent backups (configurable)
- **Rollback Capability**: Restore from any backup if needed
- **SSH Tunnel Support**: Secure connections via SSH tunnel

### Usage

#### Basic Upload

```bash
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

#### Dry Run (Preview Changes)

```bash
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password" \
  --dry-run
```

#### Upload Different Resource Types

```bash
# Upload abilities
python3 scripts/upload_pokemon_summaries.py \
  --resource ability \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"

# Upload moves
python3 scripts/upload_pokemon_summaries.py \
  --resource move \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

#### Backup Management

```bash
# List available backups
python3 scripts/upload_pokemon_summaries.py --list-backups

# Rollback to latest backup
python3 scripts/upload_pokemon_summaries.py \
  --rollback \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"

# Rollback to specific backup
python3 scripts/upload_pokemon_summaries.py \
  --rollback \
  --backup-file production_backup_20241220_143022.sql \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

#### Custom Backup Settings

```bash
# Keep 10 most recent backups instead of 7
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --keep-backups 10 \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"

# Use custom backup directory
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --backup-dir /custom/backup/path \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

### Command Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--resource` | Yes* | Resource type to upload (pokemon, ability, move, etc.) |
| `--host` | Yes* | Production database host (localhost for SSH tunnel) |
| `--port` | Yes* | Production database port (5433 for SSH tunnel) |
| `--database` | Yes* | Database name |
| `--user` | Yes* | Database username |
| `--password` | Yes* | Database password |
| `--backup-dir` | No | Backup directory on production server (default: /var/www/pokeAPI/backups) |
| `--keep-backups` | No | Number of recent backups to keep (default: 7) |
| `--dry-run` | No | Preview changes without applying them |
| `--list-backups` | No | List available backups |
| `--rollback` | No | Rollback to latest backup |
| `--backup-file` | No | Specific backup file for rollback |

*Required for upload operations, not required for `--list-backups`

### Output Example

```
Pokemon Summaries Upload Tool
============================================================
Resource type: pokemon
Target: localhost:5433
Database: pokeapi
User: pokeapi
Backup directory: /var/www/pokeAPI/backups
Keep backups: 7
============================================================
✓ Connected to production database
✓ Connected to production server via SSH
Creating backup: production_backup_20241220_143022.sql
✓ Backup created successfully: production_backup_20241220_143022.sql
✓ Kept 7 most recent backups, removed 0 old ones
Found 1308 pokemon resources locally
Found 1308 pokemon resources in production

Processing pokemon resources...
============================================================
✓ Updated: pikachu
- Unchanged: bulbasaur
+ New: new-pokemon
...

============================================================
UPLOAD COMPLETE!
============================================================
Total processed: 1308
New resources: 5
Updated resources: 12
Unchanged resources: 1291

✓ Upload completed successfully!
```

## Backup Script: `backup_db.py`

### Purpose

Creates full database backups of the production PostgreSQL database. Useful for manual backups before major changes or scheduled maintenance.

### Features

- **Full Database Backup**: Complete backup of all tables and data
- **Automatic Cleanup**: Keeps 5 most recent full backups (configurable)
- **Backup Verification**: Confirms backup integrity and size
- **Restore Functionality**: Restore from any backup with confirmation
- **Detailed Reporting**: Shows backup sizes and disk usage

### Usage

#### Create Full Backup

```bash
python3 scripts/backup_db.py \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

#### List Available Backups

```bash
python3 scripts/backup_db.py --list-backups
```

#### Restore from Backup

```bash
# Restore from latest backup
python3 scripts/backup_db.py \
  --restore \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"

# Restore from specific backup
python3 scripts/backup_db.py \
  --restore \
  --backup-file full_backup_20241220_143022.sql \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

#### Custom Backup Settings

```bash
# Keep 10 most recent backups instead of 5
python3 scripts/backup_db.py \
  --keep-backups 10 \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"

# Use custom backup directory
python3 scripts/backup_db.py \
  --backup-dir /custom/backup/path \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

### Command Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--host` | Yes* | Production database host (localhost for SSH tunnel) |
| `--port` | Yes* | Production database port (5433 for SSH tunnel) |
| `--database` | Yes* | Database name |
| `--user` | Yes* | Database username |
| `--password` | Yes* | Database password |
| `--backup-dir` | No | Backup directory on production server (default: /var/www/pokeAPI/backups) |
| `--keep-backups` | No | Number of recent full backups to keep (default: 5) |
| `--list-backups` | No | List available full backups |
| `--restore` | No | Restore from backup |
| `--backup-file` | No | Specific backup file for restore |

*Required for backup/restore operations, not required for `--list-backups`

### Output Example

```
PostgreSQL Full Database Backup Tool
============================================================
Target: localhost:5433
Database: pokeapi
User: pokeapi
Backup directory: /var/www/pokeAPI/backups
Keep backups: 5
============================================================
✓ Connected to production server via SSH
Creating full database backup: full_backup_20241220_143022.sql
This may take several minutes for large databases...
✓ Full backup created successfully: full_backup_20241220_143022.sql (45MB)
✓ Kept 5 most recent full backups, removed 0 old ones

✓ Full backup completed successfully!
Backup stored in: /var/www/pokeAPI/backups
Keeping 5 most recent full backups
```

## Backup Management

### Backup Directory Structure

```
/var/www/pokeAPI/backups/
├── production_backup_20241220_143022.sql    # Upload script backups
├── production_backup_20241220_150145.sql
├── full_backup_20241220_143022.sql          # Full database backups
├── full_backup_20241220_150145.sql
└── backup_log.txt                           # Backup history (future feature)
```

### Backup Types

1. **Production Backups** (`production_backup_*.sql`)
   - Created by upload script before each upload
   - Contains only the resources table
   - Smaller file size, faster creation
   - Keeps 7 most recent (configurable)

2. **Full Backups** (`full_backup_*.sql`)
   - Created by backup script manually
   - Contains entire database
   - Larger file size, longer creation time
   - Keeps 5 most recent (configurable)

### Automatic Cleanup

Both scripts automatically manage backup storage:

- **Upload Script**: Keeps 7 most recent production backups
- **Backup Script**: Keeps 5 most recent full backups
- **Cleanup Process**: Removes oldest backups when limit is exceeded
- **No Manual Intervention**: Cleanup happens automatically

## Safety Features

### Backup Verification

- **File Size Check**: Confirms backup file is not empty
- **Integrity Verification**: Validates backup was created successfully
- **Error Handling**: Fails gracefully if backup creation fails

### Rollback Safety

- **Confirmation Prompts**: Requires explicit confirmation for restore operations
- **Backup Listing**: Shows available backups before restore
- **Transaction Safety**: Uses database transactions for data integrity

### SSH Security

- **Tunnel Support**: All operations use SSH tunnels for security
- **Key-based Authentication**: Uses SSH keys for server access
- **Encrypted Connections**: All data transfer is encrypted

## Troubleshooting

### Common Issues

#### Connection Errors

```bash
# Error: Connection refused
# Solution: Ensure SSH tunnel is active
ssh -L 5433:localhost:5432 ${PROD_SSH_USER:-root}@${PROD_SSH_HOST:?set PROD_SSH_HOST in .env}

# Error: Authentication failed
# Solution: Check SSH key setup or password
```

#### Missing Dependencies

```bash
# Error: No module named 'paramiko'
# Solution: Install required packages
.venv/bin/pip install -r requirements.txt
```

#### Backup Failures

```bash
# Error: Backup failed
# Solution: Check disk space and permissions on the production server (via SSH using PROD_SSH_HOST)
ssh ${PROD_SSH_USER:-root}@${PROD_SSH_HOST:?set PROD_SSH_HOST in .env} "df -h \$DEPLOY_APP_DIR/backups"
```

#### Permission Issues

```bash
# Error: Permission denied
# Solution: Check backup directory permissions on the production server
ssh ${PROD_SSH_USER:-root}@${PROD_SSH_HOST:?set PROD_SSH_HOST in .env} "ls -la \$DEPLOY_APP_DIR/backups"
```

### Log Files

Monitor script execution:

```bash
# Check for error messages in script output
# All operations provide detailed status messages

# Future: Backup history log
# /var/www/pokeAPI/backups/backup_log.txt
```

## Best Practices

### Before Major Changes

1. **Create Full Backup**: Run backup script before major deployments
2. **Test Upload**: Use dry-run mode to preview changes
3. **Verify Backups**: List backups to confirm they exist

### Regular Maintenance

1. **Monitor Disk Space**: Check backup directory usage
2. **Review Backup Count**: Adjust keep-backups if needed
3. **Test Restore**: Periodically test restore functionality

### Development Workflow

1. **Local Development**: Make changes in local environment
2. **Test Changes**: Verify changes work correctly
3. **Dry Run**: Preview upload with --dry-run
4. **Upload**: Upload specific resource types
5. **Verify**: Check production site for changes

## Security Considerations

- **SSH Keys**: Use SSH key authentication instead of passwords when possible
- **Backup Encryption**: Consider encrypting backup files for sensitive data
- **Access Control**: Limit access to backup scripts and directories
- **Network Security**: Always use SSH tunnels for database connections

## Future Enhancements

- **Scheduled Backups**: Automatic backup scheduling
- **Backup Encryption**: Encrypt backup files
- **Remote Storage**: Store backups in cloud storage
- **Backup Verification**: Automated backup integrity checks
- **Email Notifications**: Alert on backup failures
- **Backup History Log**: Detailed backup operation logging
