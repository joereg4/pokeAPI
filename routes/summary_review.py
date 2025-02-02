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


# Set up OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

summary_review_bp = Blueprint("summary_review", __name__)


# Add markdown filter to blueprint
@summary_review_bp.app_template_filter("markdown")
def markdown_filter(text):
    return markdown.markdown(text) if text else ""


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
    "/summary-review/<string:resource>/<string:name>", methods=["POST"]
)
@login_required
@admin_required
def update_summary(resource, name):
    resource_obj = Resource.query.filter_by(resource=resource, name=name).first()
    if not resource_obj:
        flash("Resource not found", "error")
        return redirect(url_for("summary_review.summary_review"))

    current_summary = resource_obj.summary
    try:
        prompt = f"""Analyze the following summary and provide a corrected version that:
1. Uses **bold text** for emphasis and section names
2. Uses simple paragraph breaks to separate sections
3. Uses bullet points (not numbered lists)
4. Maintains a clean, consistent style without HTML headings
5. Organizes information into clear sections (like Type, Abilities, etc.)
6. Is comprehensive but concise
7. Follows this format:
   - First paragraph introduces the Pokémon
   - Use "**Type:**" for type information
   - Use "**Abilities:**" for abilities
   - Use "**Notable Features:**" for other important information
8. Is not longer than the original summary

Only provide the corrected summary without any additional analysis or comments:

{current_summary}
"""
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

        new_summary = response.choices[0].message.content.strip()

        if request.form.get("action") == "accept":
            resource_obj.summary = new_summary
            db.session.commit()
            flash("Summary updated successfully", "success")

        return render_template(
            "admin/summary_preview.html", resource=resource_obj, new_summary=new_summary
        )

    except Exception as e:
        flash(f"Error generating summary: {str(e)}", "error")
        return redirect(url_for("summary_review.summary_review"))


def analyze_summary(summary, max_tokens=1000):
    while True:
        prompt = f"""Analyze the following summary and provide a corrected version that:
1. Uses **bold text** for emphasis and section names
2. Uses simple paragraph breaks to separate sections
3. Uses bullet points (not numbered lists)
4. Maintains a clean, consistent style without HTML headings
5. Organizes information into clear sections (like Type, Abilities, etc.)
6. Is comprehensive but concise
7. Follows this format:
   - First paragraph introduces the Pokémon
   - Use "**Type:**" for type information
   - Use "**Abilities:**" for abilities
   - Use "**Notable Features:**" for other important information
8. Is not longer than the original summary

Only provide the corrected summary without any additional analysis or comments:

{summary}
"""

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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python summary_review.py <csv_filename>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    process_csv_file(csv_filename)
