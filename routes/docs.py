from flask import Blueprint, render_template, send_from_directory, abort
import os
import markdown
from flask import current_app

docs_bp = Blueprint("docs", __name__, url_prefix="/docs")


@docs_bp.route("/<path:doc_name>")
def view_doc(doc_name):
    """
    View a documentation file by its name (without the .md extension).
    Converts Markdown files to HTML for display.
    """
    try:
        # Get the path to the docs directory
        docs_dir = os.path.join(current_app.root_path, "docs")

        # Check if the MD file exists
        md_file = f"{doc_name}.md"
        file_path = os.path.join(docs_dir, md_file)

        if not os.path.isfile(file_path):
            current_app.logger.error(f"Documentation file not found: {file_path}")
            abort(404)

        # Read the Markdown file
        with open(file_path, "r") as file:
            md_content = file.read()

        # Convert Markdown to HTML
        html_content = markdown.markdown(
            md_content, extensions=["fenced_code", "tables", "nl2br"]
        )

        # Get the title from the first line (assumed to be a heading)
        if md_content.startswith("#"):
            title = md_content.split("\n")[0].lstrip("# \t")
        else:
            title = doc_name.replace("-", " ").replace("_", " ").title()

        return render_template(
            "docs/doc_template.html",
            title=title,
            content=html_content,
            doc_name=doc_name,
        )

    except Exception as e:
        current_app.logger.error(f"Error rendering documentation: {str(e)}")
        abort(500)


@docs_bp.route("/")
def docs_index():
    """View a list of all available documentation files."""
    try:
        docs_dir = os.path.join(current_app.root_path, "docs")
        docs = []

        # Scan the docs directory for markdown files
        for filename in os.listdir(docs_dir):
            if filename.endswith(".md"):
                # Read the file to get the title
                with open(os.path.join(docs_dir, filename), "r") as file:
                    content = file.read()

                # Get the title from the first line if it's a heading
                if content.startswith("#"):
                    title = content.split("\n")[0].lstrip("# \t")
                else:
                    title = filename[:-3].replace("-", " ").replace("_", " ").title()

                docs.append(
                    {
                        "name": filename[:-3],  # Remove .md extension
                        "title": title,
                        "filename": filename,
                    }
                )

        # Sort by title
        docs.sort(key=lambda x: x["title"])

        return render_template("docs/index.html", docs=docs, title="Documentation")

    except Exception as e:
        current_app.logger.error(f"Error rendering documentation index: {str(e)}")
        abort(500)
