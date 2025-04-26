import os
import csv
import json
from openai import OpenAI
import sys
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from routes.admin import admin_required
from models.model import Resource, db
import markdown
from utils import invalidate_related_caches


summary_review_bp = Blueprint("summary_review", __name__)


# Add markdown filter to blueprint
@summary_review_bp.app_template_filter("markdown")
def markdown_filter(text):
    return markdown.markdown(text) if text else ""


def get_openai_client():
    """Get OpenAI client with API key from environment"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


@summary_review_bp.route("/summary-review", methods=["GET"])
@login_required
@admin_required
def summary_review():
    search_term = request.args.get("search", "")
    if search_term:
        resources = Resource.query.filter(
            (Resource.name.ilike(f"%{search_term}%"))
            & (Resource.summary.isnot(None))  # This might be filtering out valid nulls
        ).all()
    else:
        resources = []

    return render_template(
        "admin/summary_review.html", resources=resources, search_term=search_term
    )


@summary_review_bp.route(
    "/summary-review/<string:resource>/<string:name>", methods=["GET", "POST"]
)
@login_required
@admin_required
def update_summary(resource, name):
    # For GET requests, redirect to the summary review page with search parameters
    if request.method == "GET":
        search_term = request.args.get("search_term", "")
        return_to = request.args.get("return_to")
        if search_term:
            return redirect(
                url_for(
                    "summary_review.summary_review",
                    search=search_term,
                    return_to=return_to,
                )
            )
        return redirect(url_for("summary_review.summary_review"))

    resource_obj = Resource.query.filter_by(resource=resource, name=name).first()
    if not resource_obj:
        flash("Resource not found", "error")
        return redirect(url_for("summary_review.summary_review"))

    current_summary = resource_obj.summary
    try:
        max_tokens = request.form.get("max_tokens", 2000, type=int)
        custom_instructions = request.form.get("custom_instructions", "").strip()

        if request.form.get("action") == "accept":
            resource_obj.summary = request.form.get("edited_summary", current_summary)
            db.session.commit()
            # Invalidate related caches after updating the summary
            invalidate_related_caches(resource_obj.resource, resource_obj.name)
            flash("Summary updated successfully", "success")
            return_to = request.args.get("return_to")
            if return_to:
                return redirect(return_to)
            # If no return_to, redirect to search results if we have a search term
            search_term = request.form.get("search_term")
            if search_term:
                return redirect(
                    url_for("summary_review.summary_review", search=search_term)
                )
            return redirect(url_for("summary_review.summary_review"))

        prompt = f"""{custom_instructions if custom_instructions else ""} Analyze the following summary and provide a corrected version that:
1. Completes any unfinished sentences or thoughts from the original summary
2. Maintains the existing structure and style, maintain great markdown formatting
3. Uses **bold text** for emphasis on important terms
4. Ensures all information is accurate and complete
5. Preserves all existing information while fixing any grammatical issues
6. Only adds new information if a section is clearly incomplete
7. Keeps the same length and scope as the original summary

Only provide the corrected summary without any additional analysis or comments.
Do not restructure the summary unless a section is clearly incomplete.

Original summary for reference:

{current_summary}
"""
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that improves Pokémon-related summaries. Provide only the corrected summary without any additional text.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )

        new_summary = response.choices[0].message.content.strip()

        return render_template(
            "admin/summary_preview.html",
            resource=resource_obj,
            new_summary=new_summary,
            return_to=request.args.get("return_to"),
            max_tokens=max_tokens,
            custom_instructions=custom_instructions,
        )

    except Exception as e:
        flash(f"Error generating summary: {str(e)}", "error")
        return redirect(url_for("summary_review.summary_review"))


def analyze_summary(summary, max_tokens=1000):
    while True:
        prompt = f"""Analyze the following summary and provide a corrected version that:
1. Completes any unfinished sentences or thoughts from the original summary
2. Maintains the existing structure and style, maintain great markdown formatting
3. Uses **bold text** for emphasis on important terms
4. Ensures all information is accurate and complete
5. Preserves all existing information while fixing any grammatical issues
6. Only adds new information if a section is clearly incomplete
7. Keeps the same length and scope as the original summary

Only provide the corrected summary without any additional analysis or comments.
Do not restructure the summary unless a section is clearly incomplete.

Original summary for reference:

{summary}
"""
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that improves Pokémon-related summaries. Provide only the corrected summary without any additional text.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
        )

        corrected_summary = response.choices[0].message.content.strip()
        print("\nCorrected summary:")
        print(corrected_summary)

        user_input = input("\nAccept this summary? (Y/n): ").lower()
        if user_input == "" or user_input == "y":
            return corrected_summary
        elif user_input == "n":
            print("Generating a new summary...")
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def process_csv_file(filename):
    resources_dir = "resources"
    input_file = os.path.join(resources_dir, filename)
    output_file = os.path.join(resources_dir, f"{os.path.splitext(filename)[0]}.json")

    print(f"Processing CSV file: {filename}")

    with open(input_file, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        data = []

        for row in reader:
            print(f"Processing: {row['name']}")
            if "summary" in row and row["summary"]:
                row["summary"] = analyze_summary(row["summary"])
            data.append(row)

    with open(output_file, "w", encoding="utf-8") as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    print(f"Finished processing {filename}. Results saved to {output_file}")


@summary_review_bp.route("/render-markdown", methods=["POST"])
@login_required
@admin_required
def render_markdown():
    data = request.get_json()
    if not data or "text" not in data:
        return ""
    return markdown.markdown(data["text"]) if data["text"] else ""


@summary_review_bp.route(
    "/summary-review/<string:resource>/<string:name>/edit", methods=["GET"]
)
@login_required
@admin_required
def edit_summary(resource, name):
    resource_obj = Resource.query.filter_by(resource=resource, name=name).first()
    if not resource_obj:
        flash("Resource not found", "error")
        return redirect(url_for("summary_review.summary_review"))

    return render_template(
        "admin/summary_preview.html",
        resource=resource_obj,
        new_summary=resource_obj.summary,  # Start with current summary
        return_to=request.args.get("return_to"),
        max_tokens=2000,
        custom_instructions="",
        is_edit_mode=True,  # New flag to indicate edit mode
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python summary_review.py <csv_filename>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    process_csv_file(csv_filename)
