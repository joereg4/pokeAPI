#!/usr/bin/env python3
"""
Standalone script to backup the entire PostgreSQL database.
Usage: python3 scripts/backup_db.py --host localhost --port 5433 --database pokeapi --user pokeapi --password "password"
"""

import argparse
import sys
import os
import subprocess
import getpass
from datetime import datetime
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    load_dotenv(".flaskenv", override=True)


def connect_prod_ssh():
    """Connect to the production server via SSH (operator use only)."""
    import paramiko

    host = os.environ.get("PROD_SSH_HOST")
    user = os.environ.get("PROD_SSH_USER", "root")
    if not host:
        raise SystemExit(
            "PROD_SSH_HOST is not set. Add it to .env (operator use only)."
        )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh.connect(host, username=user)
    return ssh


def ensure_backup_directory(ssh_connection, backup_dir):
    """Ensure backup directory exists on production server"""
    # Create directory via SSH if it doesn't exist
    stdin, stdout, stderr = ssh_connection.exec_command(f"mkdir -p {backup_dir}")
    exit_status = stdout.channel.recv_exit_status()

    if exit_status != 0:
        error_msg = stderr.read().decode()
        raise Exception(f"Failed to create backup directory: {error_msg}")

    return backup_dir


def create_full_backup(ssh_connection, backup_dir, database, user, password):
    """Create timestamped full backup of production database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/full_backup_{timestamp}.sql"

    print(f"Creating full database backup: {os.path.basename(backup_file)}")
    print("This may take several minutes for large databases...")

    # Create backup via SSH (use PGPASSWORD environment variable for authentication)
    backup_cmd = f"PGPASSWORD='{password}' pg_dump -U {user} -d {database} > {backup_file} 2>/dev/null"
    stdin, stdout, stderr = ssh_connection.exec_command(backup_cmd)

    # Wait for command to complete and get exit status
    exit_status = stdout.channel.recv_exit_status()

    if exit_status != 0:
        # Try to get error message from stderr, but don't fail if empty
        try:
            error_msg = stderr.read().decode().strip()
            if error_msg:
                raise Exception(f"Backup failed: {error_msg}")
            else:
                raise Exception(f"Backup failed with exit code {exit_status}")
        except:
            raise Exception(f"Backup failed with exit code {exit_status}")

    # Verify backup was created and has content
    verify_cmd = f"test -s {backup_file} && echo 'OK' || echo 'EMPTY'"
    stdin, stdout, stderr = ssh_connection.exec_command(verify_cmd)
    verify_result = stdout.read().decode().strip()

    if verify_result != "OK":
        raise Exception(f"Backup file is empty or doesn't exist: {backup_file}")

    # Get backup file size
    size_cmd = f"ls -lh {backup_file} | awk '{{print $5}}'"
    stdin, stdout, stderr = ssh_connection.exec_command(size_cmd)
    backup_size = stdout.read().decode().strip()

    print(
        f"✓ Full backup created successfully: {os.path.basename(backup_file)} ({backup_size})"
    )
    return backup_file


def cleanup_old_backups(ssh_connection, backup_dir, keep_count=5):
    """Keep only the most recent N full backups, remove the rest"""

    # List all full backup files sorted by modification time (newest first)
    list_cmd = f"ls -t {backup_dir}/full_backup_*.sql 2>/dev/null || true"
    stdin, stdout, stderr = ssh_connection.exec_command(list_cmd)
    backup_files = stdout.read().decode().strip().split("\n")

    # Remove empty entries
    backup_files = [f for f in backup_files if f.strip()]

    if len(backup_files) > keep_count:
        # Keep the most recent ones, delete the rest
        files_to_delete = backup_files[keep_count:]

        for file_path in files_to_delete:
            delete_cmd = f"rm -f {file_path.strip()}"
            ssh_connection.exec_command(delete_cmd)
            print(f"✓ Removed old backup: {os.path.basename(file_path.strip())}")

        print(
            f"✓ Kept {keep_count} most recent full backups, removed {len(files_to_delete)} old ones"
        )
    else:
        print(f"✓ No cleanup needed - only {len(backup_files)} full backups exist")


def list_available_backups(ssh_connection, backup_dir):
    """List all available full backups with details"""
    list_cmd = f"ls -lah {backup_dir}/full_backup_*.sql 2>/dev/null || echo 'No full backups found'"
    stdin, stdout, stderr = ssh_connection.exec_command(list_cmd)
    backup_list = stdout.read().decode().strip()

    print("Available full backups:")
    print("=" * 80)
    if backup_list == "No full backups found":
        print(backup_list)
    else:
        print(backup_list)

        # Show total count and disk usage
        count_cmd = f"ls {backup_dir}/full_backup_*.sql 2>/dev/null | wc -l"
        stdin, stdout, stderr = ssh_connection.exec_command(count_cmd)
        count = stdout.read().decode().strip()

        size_cmd = f"du -sh {backup_dir}/full_backup_*.sql 2>/dev/null | tail -1 | awk '{{print $1}}'"
        stdin, stdout, stderr = ssh_connection.exec_command(size_cmd)
        total_size = stdout.read().decode().strip()

        print(f"\nTotal: {count} full backups using {total_size}")


def restore_from_backup(
    ssh_connection, backup_dir, database, user, password, backup_file=None
):
    """Restore production database from backup"""
    if backup_file is None:
        # Use most recent backup
        list_cmd = f"ls -t {backup_dir}/full_backup_*.sql 2>/dev/null | head -1"
        stdin, stdout, stderr = ssh_connection.exec_command(list_cmd)
        backup_file = stdout.read().decode().strip()

        if not backup_file:
            raise Exception("No full backups found for restore")

    full_backup_path = (
        f"{backup_dir}/{backup_file}"
        if not backup_file.startswith(backup_dir)
        else backup_file
    )

    print(f"WARNING: This will completely replace the production database!")
    print(f"Restoring from: {os.path.basename(full_backup_path)}")

    # Confirm restore
    confirm = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Restore cancelled.")
        return

    print("Restoring database... This may take several minutes...")

    # Restore from backup
    restore_cmd = f"psql -U {user} -d {database} < {full_backup_path}"
    stdin, stdout, stderr = ssh_connection.exec_command(restore_cmd)
    exit_status = stdout.channel.recv_exit_status()

    if exit_status != 0:
        error_msg = stderr.read().decode()
        raise Exception(f"Restore failed: {error_msg}")

    print(f"✓ Database restored successfully from {os.path.basename(full_backup_path)}")


def resolve_password(password):
    """Return password from args or prompt securely if omitted."""
    if password:
        return password
    return getpass.getpass("Database password: ")


def main():
    """Main function."""
    load_environment()

    parser = argparse.ArgumentParser(
        description="Backup the entire PostgreSQL database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create full backup with automatic cleanup
  python3 scripts/backup_db.py --host localhost --port 5433 --database pokeapi --user pokeapi --password "password"
  
  # Create backup keeping 10 most recent
  python3 scripts/backup_db.py --host localhost --port 5433 --database pokeapi --user pokeapi --password "password" --keep-backups 10
  
  # List available backups
  python3 scripts/backup_db.py --list-backups
  
  # Restore from latest backup
  python3 scripts/backup_db.py --restore --host localhost --port 5433 --database pokeapi --user pokeapi --password "password"
  
  # Restore from specific backup
  python3 scripts/backup_db.py --restore --backup-file full_backup_20241220_143022.sql --host localhost --port 5433 --database pokeapi --user pokeapi --password "password"
        """,
    )

    parser.add_argument(
        "--host", help="Production database host (localhost for SSH tunnel)"
    )
    parser.add_argument(
        "--port", type=int, help="Production database port (5433 for SSH tunnel)"
    )
    parser.add_argument("--database", help="Database name")
    parser.add_argument("--user", help="Database username")
    parser.add_argument("--password", help="Database password")
    parser.add_argument(
        "--backup-dir",
        default=os.environ.get("PROD_BACKUP_DIR", "./backups"),
        help="Backup directory on remote server",
    )
    parser.add_argument(
        "--keep-backups",
        type=int,
        default=5,
        help="Number of recent full backups to keep",
    )
    parser.add_argument(
        "--list-backups", action="store_true", help="List available full backups"
    )
    parser.add_argument("--restore", action="store_true", help="Restore from backup")
    parser.add_argument("--backup-file", help="Specific backup file for restore")

    args = parser.parse_args()

    # Handle list backups command
    if args.list_backups:
        try:
            ssh = connect_prod_ssh()

            list_available_backups(ssh, args.backup_dir)
            ssh.close()
            return
        except ImportError:
            print(
                "Error: paramiko is required for SSH operations. Install with: pip install paramiko"
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error listing backups: {e}")
            sys.exit(1)

    # Handle restore command
    if args.restore:
        if not all([args.host, args.port, args.database, args.user]):
            print(
                "Error: --host, --port, --database, and --user are required for restore"
            )
            sys.exit(1)

        args.password = resolve_password(args.password)

        try:
            ssh = connect_prod_ssh()

            restore_from_backup(
                ssh,
                args.backup_dir,
                args.database,
                args.user,
                args.password,
                args.backup_file,
            )
            ssh.close()
            return
        except ImportError:
            print(
                "Error: paramiko is required for SSH operations. Install with: pip install paramiko"
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error during restore: {e}")
            sys.exit(1)

    # Validate required arguments for backup
    if not all([args.host, args.port, args.database, args.user]):
        print(
            "Error: --host, --port, --database, and --user are required for backup operations"
        )
        sys.exit(1)

    args.password = resolve_password(args.password)

    print("PostgreSQL Full Database Backup Tool")
    print("=" * 60)
    print(f"Target: {args.host}:{args.port}")
    print(f"Database: {args.database}")
    print(f"User: {args.user}")
    print(f"Backup directory: {args.backup_dir}")
    print(f"Keep backups: {args.keep_backups}")
    print("=" * 60)

    try:
        ssh = connect_prod_ssh()
        print("✓ Connected to production server via SSH")

        # Ensure backup directory exists
        ensure_backup_directory(ssh, args.backup_dir)

        # Create full backup
        create_full_backup(
            ssh, args.backup_dir, args.database, args.user, args.password
        )

        # Cleanup old backups
        cleanup_old_backups(ssh, args.backup_dir, args.keep_backups)

        # Close SSH connection
        ssh.close()

        print("\n✓ Full backup completed successfully!")
        print(f"Backup stored in: {args.backup_dir}")
        print(f"Keeping {args.keep_backups} most recent full backups")

    except ImportError as e:
        print(f"Error: Missing required module: {e}")
        print("Install missing modules with: pip install paramiko")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
