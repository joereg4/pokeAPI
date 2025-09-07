#!/usr/bin/env python3
"""
Interactive Summary Updater

This script allows you to review and update summaries for specific resource types.
It supports both interactive mode (ask for each resource) and batch mode (update all).

Usage:
    # Interactive mode
    python3 scripts/interactive_summary_updater.py --resource pokemon

    # Batch mode (update all)
    python3 scripts/interactive_summary_updater.py --resource pokemon --update-all

    # Start from a specific resource
    python3 scripts/interactive_summary_updater.py --resource pokemon --start-from "charmander"
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.markdown import Markdown
from rich.syntax import Syntax

from app import create_app
from models.model import Resource, db
from routes.summary_generators.generators import generate_summary

# Initialize Rich console
console = Console()

# Progress file location
PROGRESS_FILE = project_root / "data" / "summary_progress.json"


def ensure_progress_directory():
    """Ensure the progress directory exists."""
    PROGRESS_FILE.parent.mkdir(exist_ok=True)


def load_progress(resource_type):
    """Load progress for a specific resource type."""
    ensure_progress_directory()

    if not PROGRESS_FILE.exists():
        return {"completed": [], "last_run": None}

    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
            return data.get(resource_type, {"completed": [], "last_run": None})
    except (json.JSONDecodeError, FileNotFoundError):
        return {"completed": [], "last_run": None}


def save_progress(resource_type, completed_list):
    """Save progress for a specific resource type."""
    ensure_progress_directory()

    # Load existing data
    data = {}
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}

    # Update the specific resource type
    data[resource_type] = {
        "completed": completed_list,
        "last_run": datetime.now().isoformat(),
    }

    # Save back to file
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_resources_to_process(resource_type, start_from=None):
    """Get list of resources to process, excluding already completed ones."""
    app = create_app()

    with app.app_context():
        # Get all resources of the specified type that have summaries
        query = Resource.query.filter(
            Resource.resource == resource_type,
            Resource.summary.isnot(None),
            Resource.summary != "",
            Resource.summary != "NaN",
        ).order_by(Resource.name)

        resources = query.all()

        # Load progress to exclude completed items
        progress = load_progress(resource_type)
        completed = set(progress["completed"])

        # Filter out completed resources
        remaining_resources = [r for r in resources if r.name not in completed]

        # If start_from is specified, start from that point
        if start_from:
            start_index = None
            for i, resource in enumerate(remaining_resources):
                if resource.name >= start_from:
                    start_index = i
                    break

            if start_index is not None:
                remaining_resources = remaining_resources[start_index:]
            else:
                console.print(
                    f"[yellow]Warning: '{start_from}' not found in remaining resources. Starting from beginning.[/yellow]"
                )

        return remaining_resources, len(resources)


def display_summary(text, title="Summary", max_lines=None):
    """Display a summary with nice formatting."""
    if not text:
        console.print("[dim]No summary available[/dim]")
        return

    # Convert to markdown for better display
    markdown = Markdown(text)

    # Show the complete summary (no truncation)
    panel = Panel(markdown, title=title, border_style="blue")
    console.print(panel)


def generate_new_summary(
    resource_type, resource_name, current_summary, custom_instructions=""
):
    """Generate a new summary using the existing generator."""
    try:
        new_summary = generate_summary(
            resource_type=resource_type,
            resource_name=resource_name,
            base_summary=current_summary,
            custom_instructions=custom_instructions,
            max_tokens=2000,
        )
        return new_summary
    except Exception as e:
        console.print(f"[red]Error generating summary: {str(e)}[/red]")
        return None


def update_resource_summary(resource, new_summary):
    """Update the resource summary in the database."""
    app = create_app()

    with app.app_context():
        try:
            resource.summary = new_summary
            db.session.commit()
            return True
        except Exception as e:
            console.print(f"[red]Error updating database: {str(e)}[/red]")
            db.session.rollback()
            return False


def interactive_mode(resource_type, start_from=None):
    """Run in interactive mode - ask for each resource."""
    resources, total_count = get_resources_to_process(resource_type, start_from)

    if not resources:
        console.print(
            f"[green]✓ All {resource_type} resources have been processed![/green]"
        )
        return

    progress = load_progress(resource_type)
    completed = set(progress["completed"])

    console.print(
        f"\n[bold blue]=== {resource_type.title()} Summary Updater ===[/bold blue]"
    )
    console.print(f"Mode: Interactive")
    console.print(f"Total resources: {total_count}")
    console.print(f"Already completed: {len(completed)}")
    console.print(f"Remaining: {len(resources)}")

    if start_from:
        console.print(f"Starting from: {start_from}")

    console.print()

    for i, resource in enumerate(resources, 1):
        console.print(f"\n[bold cyan]Progress: {i}/{len(resources)}[/bold cyan]")
        console.print(f"[bold]Current: {resource.name}[/bold]")

        # Display current summary
        display_summary(resource.summary, "Current Summary")

        # Ask for action
        while True:
            action = Prompt.ask(
                "[S]kip, [U]pdate, [Q]uit",
                choices=["s", "u", "q", "S", "U", "Q"],
                default="u",
            ).lower()

            if action == "q":
                console.print("[yellow]Quitting... Progress saved.[/yellow]")
                return

            elif action == "s":
                # Skip this resource
                completed.add(resource.name)
                save_progress(resource_type, list(completed))
                console.print("[dim]Skipped[/dim]")
                break

            elif action == "u":
                # Generate new summary
                console.print("[yellow]Generating new summary...[/yellow]")

                new_summary = generate_new_summary(
                    resource_type, resource.name, resource.summary
                )

                if not new_summary:
                    console.print("[red]Failed to generate summary. Try again.[/red]")
                    continue

                # Display new summary
                display_summary(new_summary, "New Summary")

                # Ask for approval
                if Confirm.ask("Accept this summary?", default=True):
                    if update_resource_summary(resource, new_summary):
                        completed.add(resource.name)
                        save_progress(resource_type, list(completed))
                        console.print("[green]✓ Summary updated![/green]")
                    else:
                        console.print("[red]✗ Failed to update summary[/red]")
                else:
                    console.print("[dim]Summary rejected[/dim]")

                break


def batch_mode(resource_type, start_from=None):
    """Run in batch mode - update all resources automatically."""
    resources, total_count = get_resources_to_process(resource_type, start_from)

    if not resources:
        console.print(
            f"[green]✓ All {resource_type} resources have been processed![/green]"
        )
        return

    progress = load_progress(resource_type)
    completed = set(progress["completed"])

    console.print(
        f"\n[bold blue]=== {resource_type.title()} Summary Updater ===[/bold blue]"
    )
    console.print(f"Mode: Batch (Update All)")
    console.print(f"Total resources: {total_count}")
    console.print(f"Already completed: {len(completed)}")
    console.print(f"Remaining: {len(resources)}")

    if start_from:
        console.print(f"Starting from: {start_from}")

    # Confirm before proceeding
    if not Confirm.ask(f"\nProceed with updating {len(resources)} resources?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print()

    # Process with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress_bar:

        task = progress_bar.add_task("Updating summaries...", total=len(resources))

        for i, resource in enumerate(resources):
            progress_bar.update(task, description=f"Processing {resource.name}")

            # Generate new summary
            new_summary = generate_new_summary(
                resource_type, resource.name, resource.summary
            )

            if new_summary:
                # Update the resource
                if update_resource_summary(resource, new_summary):
                    completed.add(resource.name)
                    save_progress(resource_type, list(completed))
                else:
                    console.print(f"[red]Failed to update {resource.name}[/red]")
            else:
                console.print(
                    f"[red]Failed to generate summary for {resource.name}[/red]"
                )

            # 1-second delay as requested
            time.sleep(1)

            progress_bar.advance(task)

    console.print(f"\n[green]✓ Batch update completed![/green]")
    console.print(f"Processed: {len(resources)} resources")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Interactive Summary Updater",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 scripts/interactive_summary_updater.py --resource pokemon
  
  # Batch mode (update all)
  python3 scripts/interactive_summary_updater.py --resource pokemon --update-all
  
  # Start from a specific resource
  python3 scripts/interactive_summary_updater.py --resource pokemon --start-from "charmander"
        """,
    )

    parser.add_argument(
        "--resource",
        required=True,
        choices=["pokemon", "move", "ability", "item", "type"],
        help="Resource type to process",
    )

    parser.add_argument(
        "--update-all",
        action="store_true",
        help="Update all resources automatically (batch mode)",
    )

    parser.add_argument(
        "--start-from", help="Start processing from this resource name (alphabetically)"
    )

    args = parser.parse_args()

    try:
        if args.update_all:
            batch_mode(args.resource, args.start_from)
        else:
            interactive_mode(args.resource, args.start_from)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Progress saved.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
