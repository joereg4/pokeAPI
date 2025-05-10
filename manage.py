#!/usr/bin/env python3
import click
from flask.cli import FlaskGroup
from app import create_app
from models.model import db, User


def create_cli_app():
    return create_app()


cli = FlaskGroup(create_app=create_cli_app)


@cli.command()
@click.option("--username", prompt=True, help="Username for the user")
@click.option("--email", prompt=True, help="Email address for the user")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for the user",
)
@click.option("--admin", is_flag=True, help="Make the user an admin")
def create_user(username, email, password, admin):
    """Create a new user."""
    try:
        user = User(username=username, email=email, is_admin=admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User {username} created successfully!")
    except Exception as e:
        click.echo(f"Error creating user: {str(e)}", err=True)


@cli.command()
@click.argument("username")
@click.option("--email", help="New email for the user")
@click.option("--password", help="New password for the user")
@click.option("--admin", type=bool, help="Set admin status (True/False)")
def update_user(username, email, password, admin):
    """Update an existing user."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User {username} not found.", err=True)
            return

        if email:
            user.email = email
        if password:
            user.set_password(password)
        if admin is not None:
            user.is_admin = admin

        db.session.commit()
        click.echo(f"User {username} updated successfully!")
    except Exception as e:
        click.echo(f"Error updating user: {str(e)}", err=True)


@cli.command()
@click.argument("username")
def delete_user(username):
    """Delete a user."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User {username} not found.", err=True)
            return

        db.session.delete(user)
        db.session.commit()
        click.echo(f"User {username} deleted successfully!")
    except Exception as e:
        click.echo(f"Error deleting user: {str(e)}", err=True)


@cli.command()
def list_users():
    """List all users."""
    try:
        users = User.query.all()
        if not users:
            click.echo("No users found.")
            return

        click.echo("\nUser List:")
        click.echo("-" * 80)
        click.echo(f"{'Username':<20} {'Email':<30} {'Admin':<10} {'Created At'}")
        click.echo("-" * 80)

        for user in users:
            click.echo(
                f"{user.username:<20} {user.email:<30} {str(user.is_admin):<10} {user.created_at}"
            )
    except Exception as e:
        click.echo(f"Error listing users: {str(e)}", err=True)


@cli.command()
@click.argument("resource_type")
@click.argument("resource_name", required=False)
def clear_cache(resource_type, resource_name=None):
    """
    Clear cache for specific resource.
    Usage: python manage.py clear-cache [resource_type] [resource_name]
    Example: python manage.py clear-cache ability sand-veil
    """
    from utils import invalidate_related_caches

    if resource_name:
        # Clear cache for specific resource
        count = invalidate_related_caches(resource_type, resource_name)
        print(f"Cleared {count} cache keys for {resource_type}/{resource_name}")
    else:
        # Clear all caches for this resource type
        from cache import cache

        keys = cache.cache._write_client.keys(f"pokedex:*{resource_type}*")
        deleted_count = 0

        # Handle bytes/string conversion and delete each key individually
        for key in keys:
            try:
                # Convert bytes to string if needed
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                # Delete the key
                if cache.cache._write_client.delete(key):
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting key {key}: {e}")

        print(f"Cleared {deleted_count} cache keys for all {resource_type}s")

    return 0


if __name__ == "__main__":
    cli()
