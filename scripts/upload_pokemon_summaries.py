#!/usr/bin/env python3
"""
Script to upload Pokemon summaries from local database to production database.
Usage: python3 scripts/upload_pokemon_summaries.py --resource pokemon --host localhost --port 5433 --database pokeapi --user pokeapi
"""

import argparse
import sys
import os
import subprocess
import getpass
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.model import db, Resource


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


def create_production_backup(ssh_connection, backup_dir, database, user, password):
    """Create timestamped backup of production database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/production_backup_{timestamp}.sql"

    print(f"Creating backup: {os.path.basename(backup_file)}")

    # Create backup via SSH (use PGPASSWORD environment variable for authentication)
    backup_cmd = f"PGPASSWORD='{password}' pg_dump -U {user} -d {database} > {backup_file} 2>/dev/null"
    stdin, stdout, stderr = ssh_connection.exec_command(backup_cmd)
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

    print(f"✓ Backup created successfully: {os.path.basename(backup_file)}")
    return backup_file


def cleanup_old_backups(ssh_connection, backup_dir, keep_count=7):
    """Keep only the most recent N backups, remove the rest"""

    # List all backup files sorted by modification time (newest first)
    list_cmd = f"ls -t {backup_dir}/production_backup_*.sql 2>/dev/null || true"
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
            f"✓ Kept {keep_count} most recent backups, removed {len(files_to_delete)} old ones"
        )
    else:
        print(f"✓ No cleanup needed - only {len(backup_files)} backups exist")


def list_available_backups(ssh_connection, backup_dir):
    """List all available backups"""
    list_cmd = f"ls -la {backup_dir}/production_backup_*.sql 2>/dev/null || echo 'No backups found'"
    stdin, stdout, stderr = ssh_connection.exec_command(list_cmd)
    backup_list = stdout.read().decode().strip()

    print("Available backups:")
    print("=" * 60)
    print(backup_list)


def rollback_from_backup(
    ssh_connection, backup_dir, database, user, password, backup_file=None
):
    """Rollback production database from backup"""
    if backup_file is None:
        # Use most recent backup
        list_cmd = f"ls -t {backup_dir}/production_backup_*.sql 2>/dev/null | head -1"
        stdin, stdout, stderr = ssh_connection.exec_command(list_cmd)
        backup_file = stdout.read().decode().strip()

        if not backup_file:
            raise Exception("No backups found for rollback")

    full_backup_path = (
        f"{backup_dir}/{backup_file}"
        if not backup_file.startswith(backup_dir)
        else backup_file
    )

    print(f"Rolling back from: {os.path.basename(full_backup_path)}")

    # Restore from backup
    restore_cmd = f"psql -U {user} -d {database} < {full_backup_path}"
    stdin, stdout, stderr = ssh_connection.exec_command(restore_cmd)
    exit_status = stdout.channel.recv_exit_status()

    if exit_status != 0:
        error_msg = stderr.read().decode()
        raise Exception(f"Rollback failed: {error_msg}")

    print(
        f"✓ Rollback completed successfully from {os.path.basename(full_backup_path)}"
    )


def upload_resource_type(resource_type, prod_conn, local_app, dry_run=False):
    """Upload specific resource type from local to production"""
    try:
        with local_app.app_context():
            # Get local data for resource type
            local_resources = Resource.query.filter(
                Resource.resource == resource_type,
                Resource.summary.isnot(None),
                Resource.summary != "",
                Resource.summary != "NaN",
            ).all()

            print(f"Found {len(local_resources)} {resource_type} resources locally")

            # Get production data for comparison (needed for both dry run and actual upload)
            prod_cursor = prod_conn.cursor()
            prod_cursor.execute(
                """
                SELECT name, summary 
                FROM resources 
                WHERE resource = %s AND summary IS NOT NULL AND summary != '' AND summary != 'NaN'
            """,
                (resource_type,),
            )
            prod_results = prod_cursor.fetchall()
            prod_summaries = {row[0]: row[1] for row in prod_results}

            print(
                f"Found {len(prod_summaries)} {resource_type} resources in production"
            )

            if dry_run:
                # Simulate the upload process to show actual changes
                updated_count = 0
                new_count = 0
                unchanged_count = 0
                changes_to_show = []

                for local_resource in local_resources:
                    pokemon_name = local_resource.name
                    local_summary = local_resource.summary

                    if pokemon_name in prod_summaries:
                        if prod_summaries[pokemon_name] != local_summary:
                            updated_count += 1
                            if len(changes_to_show) < 5:
                                changes_to_show.append(f"  - {pokemon_name}: UPDATE")
                        else:
                            unchanged_count += 1
                    else:
                        new_count += 1
                        if len(changes_to_show) < 5:
                            changes_to_show.append(f"  - {pokemon_name}: NEW")

                print(
                    f"\nDRY RUN - Analysis of {len(local_resources)} {resource_type} resources:"
                )
                print(f"  New resources: {new_count}")
                print(f"  Updated resources: {updated_count}")
                print(f"  Unchanged resources: {unchanged_count}")

                if changes_to_show:
                    print(f"\nSample changes that would be made:")
                    for change in changes_to_show:
                        print(change)
                    if (new_count + updated_count) > 5:
                        print(f"  ... and {new_count + updated_count - 5} more changes")
                else:
                    print(f"\n✓ No changes needed - databases are in sync!")

                prod_cursor.close()
                return True

            # Process each local resource
            updated_count = 0
            new_count = 0
            unchanged_count = 0

            print(f"\nProcessing {resource_type} resources...")
            print("=" * 60)

            for local_resource in local_resources:
                pokemon_name = local_resource.name
                local_summary = local_resource.summary

                if pokemon_name in prod_summaries:
                    # Update existing resource
                    if prod_summaries[pokemon_name] != local_summary:
                        update_cmd = """
                            UPDATE resources 
                            SET summary = %s 
                            WHERE resource = %s AND name = %s
                        """
                        prod_cursor.execute(
                            update_cmd, (local_summary, resource_type, pokemon_name)
                        )
                        updated_count += 1
                        print(f"✓ Updated: {pokemon_name}")
                    else:
                        unchanged_count += 1
                        print(f"- Unchanged: {pokemon_name}")
                else:
                    # Create new resource
                    insert_cmd = """
                        INSERT INTO resources (resource, name, summary) 
                        VALUES (%s, %s, %s)
                    """
                    prod_cursor.execute(
                        insert_cmd, (resource_type, pokemon_name, local_summary)
                    )
                    new_count += 1
                    print(f"+ New: {pokemon_name}")

            # Commit all changes
            prod_conn.commit()
            prod_cursor.close()

            print("\n" + "=" * 60)
            print("UPLOAD COMPLETE!")
            print("=" * 60)
            print(f"Total processed: {len(local_resources)}")
            print(f"New resources: {new_count}")
            print(f"Updated resources: {updated_count}")
            print(f"Unchanged resources: {unchanged_count}")

            return True

    except Exception as e:
        print(f"Error during upload: {e}")
        return False


def resolve_password(password):
    """Return password from args or prompt securely if omitted."""
    if password:
        return password
    return getpass.getpass("Database password: ")


def main():
    """Main function."""
    load_environment()

    parser = argparse.ArgumentParser(
        description="Upload Pokemon summaries from local database to production database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload Pokemon summaries with automatic backup
  python3 scripts/upload_pokemon_summaries.py --resource pokemon --host localhost --port 5433 --database pokeapi --user pokeapi
  
  # Dry run to see what would change
  python3 scripts/upload_pokemon_summaries.py --resource pokemon --dry-run
  
  # List available backups
  python3 scripts/upload_pokemon_summaries.py --list-backups
  
  # Rollback to latest backup
  python3 scripts/upload_pokemon_summaries.py --rollback
        """,
    )

    parser.add_argument(
        "--resource",
        required=False,
        help="Resource type to upload (pokemon, ability, move, etc.)",
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
        "--keep-backups", type=int, default=7, help="Number of recent backups to keep"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--list-backups", action="store_true", help="List available backups"
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback to latest backup"
    )
    parser.add_argument("--backup-file", help="Specific backup file for rollback")

    args = parser.parse_args()

    # Handle special commands
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

    if args.rollback:
        if not all([args.host, args.port, args.database, args.user]):
            print(
                "Error: --host, --port, --database, and --user are required for rollback"
            )
            sys.exit(1)

        args.password = resolve_password(args.password)

        try:
            ssh = connect_prod_ssh()

            rollback_from_backup(
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
            print(f"Error during rollback: {e}")
            sys.exit(1)

    # Validate required arguments for upload
    if not args.resource:
        print("Error: --resource is required for upload operations")
        sys.exit(1)

    if not all([args.host, args.port, args.database, args.user]):
        print(
            "Error: --host, --port, --database, and --user are required for upload operations"
        )
        sys.exit(1)

    args.password = resolve_password(args.password)

    print("Pokemon Summaries Upload Tool")
    print("=" * 60)
    print(f"Resource type: {args.resource}")
    print(f"Target: {args.host}:{args.port}")
    print(f"Database: {args.database}")
    print(f"User: {args.user}")
    print(f"Backup directory: {args.backup_dir}")
    print(f"Keep backups: {args.keep_backups}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print("=" * 60)

    try:
        # Import required modules
        import paramiko
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Connect to production database
        print(f"Connecting to production database at {args.host}:{args.port}")
        prod_conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
        )
        print("✓ Connected to production database")

        # Set up SSH connection for backup operations
        ssh = connect_prod_ssh()
        print("✓ Connected to production server via SSH")

        # Ensure backup directory exists
        ensure_backup_directory(ssh, args.backup_dir)

        # Create backup before upload (unless dry run)
        if not args.dry_run:
            create_production_backup(
                ssh, args.backup_dir, args.database, args.user, args.password
            )
            cleanup_old_backups(ssh, args.backup_dir, args.keep_backups)

        # Create local app context
        app = create_app()

        # Upload resource type
        success = upload_resource_type(args.resource, prod_conn, app, args.dry_run)

        # Close connections
        prod_conn.close()
        ssh.close()

        if success:
            if args.dry_run:
                print("\n✓ Dry run completed successfully!")
                print("Run without --dry-run to apply changes")
            else:
                print("\n✓ Upload completed successfully!")
        else:
            print("\n✗ Upload failed. Please check the error messages above.")
            sys.exit(1)

    except ImportError as e:
        print(f"Error: Missing required module: {e}")
        print("Install missing modules with: pip install paramiko psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
