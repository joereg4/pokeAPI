import os
import csv
import json
from openai import OpenAI
import sys
import re
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


@summary_review_bp.route(
    "/new-pokemon-summary/<string:pokemon_name>", methods=["GET", "POST"]
)
@login_required
@admin_required
def new_pokemon_summary(pokemon_name):
    """Generate a new Pokemon summary with OpenAI using the templated format."""
    # Check if we're returning from a filtered list
    return_to = request.args.get("return_to", url_for("admin.list_pokemon_summaries"))

    # Get the Pokemon resource or create it if it doesn't exist
    resource_obj = Resource.query.filter_by(
        resource="pokemon", name=pokemon_name
    ).first()

    # Format the Pokemon display name
    display_name = pokemon_name.replace("-", " ").title()

    if request.method == "POST":
        # Handle form submission - this is for accepting the generated summary
        if request.form.get("action") == "accept":
            summary = request.form.get("summary", "")

            # Create or update the resource with the summary
            if not resource_obj:
                resource_obj = Resource(
                    resource="pokemon", name=pokemon_name, summary=summary
                )
                db.session.add(resource_obj)
            else:
                resource_obj.summary = summary

            db.session.commit()

            # Invalidate related caches
            invalidate_related_caches("pokemon", pokemon_name)

            flash(f"Summary for {display_name} saved successfully!", "success")
            return redirect(return_to)

        # Handle regeneration with custom instructions
        max_tokens = request.form.get("max_tokens", 2000, type=int)
        custom_instructions = request.form.get("custom_instructions", "").strip()

        # If we already have a generated summary, use it as a base
        current_summary = request.form.get("current_summary", "")

        # Generate a new summary with custom instructions
        new_summary = custom_generate_pokemon_summary(
            pokemon_name,
            base_summary=current_summary,
            custom_instructions=custom_instructions,
            max_tokens=max_tokens,
        )

        return render_template(
            "admin/new_pokemon_summary.html",
            pokemon_name=pokemon_name,
            display_name=display_name,
            summary=new_summary,
            return_to=return_to,
            max_tokens=max_tokens,
            custom_instructions=custom_instructions,
        )

    # GET request - generate an initial summary
    try:
        # If the resource already has a summary, use it
        if resource_obj and resource_obj.summary and resource_obj.summary != "NaN":
            return render_template(
                "admin/new_pokemon_summary.html",
                pokemon_name=pokemon_name,
                display_name=display_name,
                summary=resource_obj.summary,
                return_to=return_to,
                max_tokens=2000,
                custom_instructions="",
            )

        # Generate a new summary for this Pokemon
        summary = custom_generate_pokemon_summary(pokemon_name)

        return render_template(
            "admin/new_pokemon_summary.html",
            pokemon_name=pokemon_name,
            display_name=display_name,
            summary=summary,
            return_to=return_to,
            max_tokens=2000,
            custom_instructions="",
        )

    except Exception as e:
        flash(f"Error generating summary: {str(e)}", "error")
        return redirect(return_to)


def format_pokemon_summary(summary):
    """
    Ensure proper markdown formatting with extra line breaks after headers.
    This makes bullet point lists render properly in markdown.
    """
    # Add a line break after each section header (bold text followed by a colon)
    formatted_summary = re.sub(r"(\*\*[^*]+:\*\*)\n-", r"\1\n\n-", summary)

    # Handle edge cases where there might be no bullet points by ensuring consistent structure
    formatted_summary = re.sub(
        r"(\*\*[^*]+:\*\*)\n([^\n-])", r"\1\n\n\2", formatted_summary
    )

    return formatted_summary


def custom_generate_pokemon_summary(
    pokemon_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary for a Pokemon using OpenAI with a custom template."""
    try:
        # Get the display name
        display_name = pokemon_name.replace("-", " ").title()

        # Try to get Pokemon data from the API
        import requests
        import re

        pokemon_data = {}
        generation = "Unknown"

        try:
            # Directly fetch from pokemon endpoint only
            pokemon_response = requests.get(
                f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
            )
            if pokemon_response.status_code == 200:
                pokemon_data = pokemon_response.json()

                # Try to extract generation (might not be available)
                try:
                    species_url = pokemon_data.get("species", {}).get("url")
                    if species_url:
                        species_response = requests.get(species_url)
                        if species_response.status_code == 200:
                            species_data = species_response.json()
                            if "generation" in species_data:
                                generation = (
                                    species_data["generation"]["name"]
                                    .replace("-", " ")
                                    .title()
                                )
                except Exception as e:
                    current_app.logger.error(f"Error fetching species data: {e}")

        except Exception as e:
            # Just log the error, we'll still generate a summary with less info
            current_app.logger.error(f"Error fetching Pokemon data: {e}")

        # Get types
        types = []
        if pokemon_data and "types" in pokemon_data:
            types = [t["type"]["name"].title() for t in pokemon_data["types"]]

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:

**Section Header:**

- Bullet point 1
- Bullet point 2

{summary_to_improve}
"""
        else:
            # Custom Template with proper spacing after headers
            template = f"""**{display_name}** is a {"/".join(types) if types else "[Type]"} Pokémon introduced in {generation}.

**Type:** {" / ".join(types) if types else "[Type]"}

**Abilities:**

- **[Primary Ability]:** [Description]
- **[Hidden Ability]:** [Description]

**Physical Characteristics:**

- [Notable physical feature 1]
- [Notable physical feature 2]
- [Notable physical feature 3]

**Behavior and Habitat:**

- [Behavior description]
- [Habitat information]

**In Battle:**

- [Battle strategy or role]
- [Signature/Notable moves]
- [Strengths]
- [Weaknesses]

**Evolution:**

- [Evolution details]

**Interesting Facts:**

- [Interesting fact 1]
- [Interesting fact 2]
- [Interesting fact 3]
"""

            # Prepare the prompt with specific instructions to avoid returning placeholders
            prompt = f"""{custom_instructions}

You are a Pokémon expert. Create a comprehensive and detailed summary for {display_name} following this exact template structure:

{template}

IMPORTANT INSTRUCTIONS:
1. Fill in ALL placeholders with specific, accurate information about {display_name}.
2. Do NOT leave any placeholder text like "[Description]" or "[Notable physical feature]" in your response.
3. Search the web for the most current and accurate information about this Pokémon.
4. Include specific abilities with their actual descriptions.
5. Describe actual physical characteristics, behavior patterns, battle strategies, and evolution chains.
6. Include factual interesting facts, not placeholders.
7. Keep the markdown formatting with bold section headers.
8. Be specific and detailed in your descriptions.
9. Maintain the exact spacing format with a blank line after each section header.

If you don't have enough information for a section, provide your best educated description based on similar Pokémon rather than leaving placeholders.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()

        # Use GPT-4o with web search for new information about Pokémon
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed and accurate summaries of Pokémon with precise information from official sources. You MUST replace all placeholder text with actual information. Always include a blank line after each section header before starting bullet points.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
        )

        result = response.choices[0].message.content.strip()

        # Check if the response still contains placeholder text
        placeholder_pattern = r"\[\w+( \w+)*\]"
        if re.search(placeholder_pattern, result):
            # If placeholders remain, try one more time with a more direct prompt
            current_app.logger.warning(
                f"Detected placeholders in summary for {pokemon_name}, retrying..."
            )

            retry_prompt = f"""The previous summary for {display_name} still contained placeholder text. 
            
Please create a complete summary WITHOUT ANY PLACEHOLDERS. Replace every [placeholder] with actual information.

For any section where you're uncertain, provide a reasonable description based on similar Pokémon or your knowledge of the Pokémon universe.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:
**Section:**

- Bullet point
- Another bullet point

Here's the previous summary that needs to be improved:

{result}"""

            retry_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Pokémon expert who creates detailed and accurate summaries. You MUST replace ALL placeholder text with actual information, even if you need to make educated guesses based on similar Pokémon. Always include a blank line after each section header before starting bullet points.",
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                max_tokens=max_tokens,
                tools=[{"type": "web_search"}],
                tool_choice="auto",
            )

            result = retry_response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating summary with OpenAI: {e}")

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a Pokémon introduced in {generation if 'generation' in locals() else 'Unknown Generation'}.

**Type:** {" / ".join(types) if 'types' in locals() and types else "[Type]"}

**Abilities:**

- **Vital Spirit:** Prevents the Pokémon from falling asleep.
- **Anger Point:** Maxes Attack when hit by a critical hit.

**Physical Characteristics:**

- Muscular bipedal Pokémon with a primate-like appearance
- Has distinctive coloration and markings
- Shows signs of its evolutionary heritage

**Behavior and Habitat:**

- Known for its aggressive temperament
- Typically found in mountainous or forested regions
- Forms small groups in the wild

**In Battle:**

- Primarily physical attacker with high Attack stat
- Known for fighting-type moves with good coverage
- Strong against Normal, Ice, Rock, Dark, and Steel types
- Vulnerable to Psychic, Flying, and Fairy moves

**Evolution:**

- Evolves from its pre-evolution under specific conditions
- Evolution triggers specific changes in appearance and abilities

**Interesting Facts:**

- Has a unique place in Pokémon lore and games
- Featured in various Pokémon media
- Has distinctive cry and animation in the games
"""

        return fallback_template


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python summary_review.py <csv_filename>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    process_csv_file(csv_filename)
