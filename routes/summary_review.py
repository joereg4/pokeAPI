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

        # Use the new resource-specific summary generator based on resource type
        if resource in ["pokemon", "move", "ability", "item", "type"]:
            # Use the custom_generate_summary function for resource-specific templates
            new_summary = custom_generate_summary(
                resource, name, current_summary, custom_instructions, max_tokens
            )
        else:
            # Fall back to the original generic approach for unsupported resource types
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


def format_generation(generation_text):
    """
    Format generation text with properly capitalized Roman numerals.
    Example: "generation ix" -> "Generation IX"
    """
    if not generation_text:
        return "Unknown"

    # First capitalize the word "generation"
    result = generation_text.replace("-", " ").title()

    # Find Roman numerals and make them uppercase
    roman_numeral_pattern = r"\b([IiVvXxLlCcDdMm]+)\b"

    def uppercase_roman(match):
        return match.group(0).upper()

    result = re.sub(roman_numeral_pattern, uppercase_roman, result)

    return result


def generate_pokemon_summary(
    pokemon_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon using OpenAI with the Pokémon template."""
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
                                # Format generation with proper Roman numerals
                                generation = format_generation(
                                    species_data["generation"]["name"]
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

        # Make sure generation has proper Roman numeral formatting
        if "generation" in generation.lower():
            if re.search(r"\b[ivxlcdm]+\b", generation.lower()):
                generation = format_generation(generation)

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points except for **Type:**, like this:

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
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information about Pokémon",
                    },
                }
            ],
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
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for information about Pokémon",
                        },
                    }
                ],
                tool_choice="auto",
            )

            result = retry_response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating summary with OpenAI: {e}")

        # Format generation for fallback template too
        generation_text = (
            generation if "generation" in locals() else "Unknown Generation"
        )
        if "generation" in generation_text.lower() and re.search(
            r"\b[ivxlcdm]+\b", generation_text.lower()
        ):
            generation_text = format_generation(generation_text)

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a Pokémon introduced in {generation_text}.

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


def generate_move_summary(
    move_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon move using OpenAI with the move template."""
    try:
        # Get the display name
        display_name = move_name.replace("-", " ").title()

        # Try to get Move data from the API
        import requests
        import re

        move_data = {}
        move_type = "Unknown"
        power = "?"
        accuracy = "?"
        pp = "?"
        damage_class = "Unknown"

        try:
            # Fetch from move endpoint
            move_response = requests.get(f"https://pokeapi.co/api/v2/move/{move_name}")
            if move_response.status_code == 200:
                move_data = move_response.json()

                # Extract basic move information
                if "type" in move_data and "name" in move_data["type"]:
                    move_type = move_data["type"]["name"].title()

                if "power" in move_data and move_data["power"] is not None:
                    power = str(move_data["power"])

                if "accuracy" in move_data and move_data["accuracy"] is not None:
                    accuracy = str(move_data["accuracy"])

                if "pp" in move_data and move_data["pp"] is not None:
                    pp = str(move_data["pp"])

                if "damage_class" in move_data and "name" in move_data["damage_class"]:
                    damage_class = move_data["damage_class"]["name"].title()

        except Exception as e:
            # Just log the error, we'll still generate a summary with less info
            current_app.logger.error(f"Error fetching Move data: {e}")

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon move summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:

**Section Header:**

- Bullet point 1
- Bullet point 2

{summary_to_improve}
"""
        else:
            # Custom Template with proper spacing after headers for moves
            template = f"""**{display_name}** is a {move_type}-type {damage_class} move in the Pokémon games.

**Basic Information:**

- **Type:** {move_type}
- **Category:** {damage_class}
- **Power:** {power}
- **Accuracy:** {accuracy}%
- **PP:** {pp}

**Effect:**

- [Primary effect description]
- [Additional effect details]
- [Chance of secondary effects if applicable]

**In-Game Description:**

- [Official in-game description]

**Notable Users:**

- [Pokémon that commonly learn this move]
- [Signature users if applicable]

**Strategic Use:**

- [How this move is typically used in battles]
- [Competitive viability]
- [Synergies with abilities or items]

**Interesting Facts:**

- [Development history or trivia]
- [Changes across generations]
- [Cultural references or name origins]
"""

            # Prepare the prompt with specific instructions to avoid returning placeholders
            prompt = f"""{custom_instructions}

You are a Pokémon move expert. Create a comprehensive and detailed summary for the move {display_name} following this exact template structure:

{template}

IMPORTANT INSTRUCTIONS:
1. Fill in ALL placeholders with specific, accurate information about the move {display_name}.
2. Do NOT leave any placeholder text like "[Primary effect description]" in your response.
3. Search the web for the most current and accurate information about this move.
4. Include realistic information about which Pokémon typically learn this move.
5. Describe the actual effects of the move in detail, including any secondary effects.
6. Include specific strategic applications in battles.
7. Keep the markdown formatting with bold section headers.
8. Be specific and detailed in your descriptions.
9. Maintain the exact spacing format with a blank line after each section header.

If you don't have enough information for a section, provide your best educated description based on similar moves rather than leaving placeholders.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()

        # Use GPT-4o with web search for new information about the move
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed and accurate summaries of Pokémon moves with precise information from official sources. You MUST replace all placeholder text with actual information. Always include a blank line after each section header before starting bullet points.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information about Pokémon moves",
                    },
                }
            ],
            tool_choice="auto",
        )

        result = response.choices[0].message.content.strip()

        # Check if the response still contains placeholder text
        placeholder_pattern = r"\[\w+( \w+)*\]"
        if re.search(placeholder_pattern, result):
            # If placeholders remain, try one more time with a more direct prompt
            current_app.logger.warning(
                f"Detected placeholders in summary for move {move_name}, retrying..."
            )

            retry_prompt = f"""The previous summary for the move {display_name} still contained placeholder text. 
            
Please create a complete summary WITHOUT ANY PLACEHOLDERS. Replace every [placeholder] with actual information.

For any section where you're uncertain, provide a reasonable description based on similar moves or your knowledge of the Pokémon universe.

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
                        "content": "You are a Pokémon expert who creates detailed and accurate summaries of moves. You MUST replace ALL placeholder text with actual information, even if you need to make educated guesses based on similar moves. Always include a blank line after each section header before starting bullet points.",
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                max_tokens=max_tokens,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for information about Pokémon moves",
                        },
                    }
                ],
                tool_choice="auto",
            )

            result = retry_response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)  # Reuse the same formatting function

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating move summary with OpenAI: {e}")

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a Pokémon move.

**Basic Information:**

- **Type:** {move_type if 'move_type' in locals() else "Unknown"}
- **Category:** {damage_class if 'damage_class' in locals() else "Unknown"}
- **Power:** {power if 'power' in locals() else "?"}
- **Accuracy:** {accuracy if 'accuracy' in locals() else "?"}%
- **PP:** {pp if 'pp' in locals() else "?"}

**Effect:**

- Deals damage to the target
- May have additional effects based on the move type

**In-Game Description:**

- A powerful attack that can cause various effects

**Notable Users:**

- Various Pokémon of compatible types
- Some Pokémon may learn this move through level-up, TM/TR, or tutoring

**Strategic Use:**

- Can be used in both casual and competitive play
- Effectiveness depends on the opponent's type and defenses
- Consider PP consumption for longer battles

**Interesting Facts:**

- Introduced in an earlier generation of Pokémon games
- Has been featured in the anime series
- The move's name relates to its effect or appearance
"""

        return fallback_template


def generate_ability_summary(
    ability_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon ability using OpenAI with the ability template."""
    try:
        # Get the display name
        display_name = ability_name.replace("-", " ").title()

        # Try to get Ability data from the API
        import requests
        import re

        ability_data = {}
        effect = "Unknown"
        generation = "Unknown"

        try:
            # Fetch from ability endpoint
            ability_response = requests.get(
                f"https://pokeapi.co/api/v2/ability/{ability_name}"
            )
            if ability_response.status_code == 200:
                ability_data = ability_response.json()

                # Extract basic ability information
                if "effect_entries" in ability_data:
                    # Try to find English effect description
                    for entry in ability_data["effect_entries"]:
                        if entry.get("language", {}).get("name") == "en":
                            effect = entry.get("effect", "Unknown")
                            break

                # Get generation information
                if (
                    "generation" in ability_data
                    and "name" in ability_data["generation"]
                ):
                    generation = format_generation(ability_data["generation"]["name"])

        except Exception as e:
            # Just log the error, we'll still generate a summary with less info
            current_app.logger.error(f"Error fetching Ability data: {e}")

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon ability summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:

**Section Header:**

- Bullet point 1
- Bullet point 2

{summary_to_improve}
"""
        else:
            # Custom Template with proper spacing after headers for abilities
            template = f"""**{display_name}** is a Pokémon ability introduced in {generation}.

**Effect:**

- {effect if effect != "Unknown" else "[Primary effect description]"}
- [Additional effect details if applicable]

**In Battle:**

- [How this ability affects battles]
- [Interactions with moves/status conditions]
- [Strategic applications]

**Pokémon with this Ability:**

- [Common Pokémon with this ability]
- [Notable Pokémon with this ability]
- [Information about whether it's a Hidden Ability for certain Pokémon]

**Competitive Use:**

- [How this ability is used in competitive play]
- [Tier viability]
- [Team synergies]

**Interesting Facts:**

- [When it was introduced]
- [Changes across generations]
- [Name origin or trivia]
"""

            # Prepare the prompt with specific instructions to avoid returning placeholders
            prompt = f"""{custom_instructions}

You are a Pokémon ability expert. Create a comprehensive and detailed summary for the ability {display_name} following this exact template structure:

{template}

IMPORTANT INSTRUCTIONS:
1. Fill in ALL placeholders with specific, accurate information about the ability {display_name}.
2. Do NOT leave any placeholder text like "[Primary effect description]" in your response.
3. Search the web for the most current and accurate information about this ability.
4. Include realistic information about which Pokémon have this ability.
5. Describe the actual effects of the ability in detail.
6. Include specific strategic applications in battles.
7. Keep the markdown formatting with bold section headers.
8. Be specific and detailed in your descriptions.
9. Maintain the exact spacing format with a blank line after each section header.

If you don't have enough information for a section, provide your best educated description based on similar abilities rather than leaving placeholders.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()

        # Use GPT-4o with web search for new information about the ability
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed and accurate summaries of Pokémon abilities with precise information from official sources. You MUST replace all placeholder text with actual information. Always include a blank line after each section header before starting bullet points.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information about Pokémon abilities",
                    },
                }
            ],
            tool_choice="auto",
        )

        result = response.choices[0].message.content.strip()

        # Check if the response still contains placeholder text
        placeholder_pattern = r"\[\w+( \w+)*\]"
        if re.search(placeholder_pattern, result):
            # If placeholders remain, try one more time with a more direct prompt
            current_app.logger.warning(
                f"Detected placeholders in summary for ability {ability_name}, retrying..."
            )

            retry_prompt = f"""The previous summary for the ability {display_name} still contained placeholder text. 
            
Please create a complete summary WITHOUT ANY PLACEHOLDERS. Replace every [placeholder] with actual information.

For any section where you're uncertain, provide a reasonable description based on similar abilities or your knowledge of the Pokémon universe.

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
                        "content": "You are a Pokémon expert who creates detailed and accurate summaries of abilities. You MUST replace ALL placeholder text with actual information, even if you need to make educated guesses based on similar abilities. Always include a blank line after each section header before starting bullet points.",
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                max_tokens=max_tokens,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for information about Pokémon abilities",
                        },
                    }
                ],
                tool_choice="auto",
            )

            result = retry_response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)  # Reuse the same formatting function

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating ability summary with OpenAI: {e}")

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a Pokémon ability.

**Effect:**

- Changes how a Pokémon interacts with battle mechanics
- May provide immunities, boosts, or other benefits

**In Battle:**

- Activates under specific conditions in battle
- May affect the Pokémon's stats or abilities
- Can create unique strategic opportunities

**Pokémon with this Ability:**

- Multiple Pokémon across different generations
- May be either a standard or hidden ability
- Often thematically related to the Pokémon's design

**Competitive Use:**

- Considered in team building for certain strategies
- Effectiveness varies based on the metagame
- Can complement specific move sets

**Interesting Facts:**

- Introduced in one of the core Pokémon games
- May have been adjusted in later generations
- Name often reflects the ability's function
"""

        return fallback_template


def generate_item_summary(
    item_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon item using OpenAI with the item template."""
    try:
        # Get the display name
        display_name = item_name.replace("-", " ").title()

        # Try to get Item data from the API
        import requests
        import re

        item_data = {}
        effect = "Unknown"
        category = "Unknown"
        cost = "Unknown"

        try:
            # Fetch from item endpoint
            item_response = requests.get(f"https://pokeapi.co/api/v2/item/{item_name}")
            if item_response.status_code == 200:
                item_data = item_response.json()

                # Extract basic item information
                if "effect_entries" in item_data:
                    # Try to find English effect description
                    for entry in item_data["effect_entries"]:
                        if entry.get("language", {}).get("name") == "en":
                            effect = entry.get("effect", "Unknown")
                            break

                # Get category
                if "category" in item_data and "name" in item_data["category"]:
                    category = item_data["category"]["name"].replace("-", " ").title()

                # Get cost
                if "cost" in item_data and item_data["cost"] is not None:
                    cost = str(item_data["cost"])

        except Exception as e:
            # Just log the error, we'll still generate a summary with less info
            current_app.logger.error(f"Error fetching Item data: {e}")

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon item summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:

**Section Header:**

- Bullet point 1
- Bullet point 2

{summary_to_improve}
"""
        else:
            # Custom Template with proper spacing after headers for items
            template = f"""**{display_name}** is a {category} item in the Pokémon games.

**Basic Information:**

- **Category:** {category}
- **Cost:** {cost} Pokédollars
- **Availability:** [Where it can be purchased or found]

**Effect:**

- {effect if effect != "Unknown" else "[Primary effect description]"}
- [Additional effect details if applicable]

**In-Game Use:**

- [How players typically use this item]
- [When it's most effective]
- [Limitations or restrictions]

**Game Appearances:**

- [First appearance in the series]
- [Notable games featuring this item]
- [Any changes across different games]

**Strategic Applications:**

- [How competitive players use this item]
- [Which Pokémon benefit most from holding it]
- [Team strategies involving this item]

**Interesting Facts:**

- [Development history or inspiration]
- [References in anime or manga]
- [Cultural significance or trivia]
"""

            # Prepare the prompt with specific instructions to avoid returning placeholders
            prompt = f"""{custom_instructions}

You are a Pokémon item expert. Create a comprehensive and detailed summary for the item {display_name} following this exact template structure:

{template}

IMPORTANT INSTRUCTIONS:
1. Fill in ALL placeholders with specific, accurate information about the item {display_name}.
2. Do NOT leave any placeholder text like "[Primary effect description]" in your response.
3. Search the web for the most current and accurate information about this item.
4. Include realistic information about how this item is used in the games.
5. Describe the actual effects of the item in detail.
6. Include specific strategic applications for competitive play.
7. Keep the markdown formatting with bold section headers.
8. Be specific and detailed in your descriptions.
9. Maintain the exact spacing format with a blank line after each section header.

If you don't have enough information for a section, provide your best educated description based on similar items rather than leaving placeholders.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()

        # Use GPT-4o with web search for new information about the item
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed and accurate summaries of Pokémon items with precise information from official sources. You MUST replace all placeholder text with actual information. Always include a blank line after each section header before starting bullet points.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information about Pokémon items",
                    },
                }
            ],
            tool_choice="auto",
        )

        result = response.choices[0].message.content.strip()

        # Check if the response still contains placeholder text
        placeholder_pattern = r"\[\w+( \w+)*\]"
        if re.search(placeholder_pattern, result):
            # If placeholders remain, try one more time with a more direct prompt
            current_app.logger.warning(
                f"Detected placeholders in summary for item {item_name}, retrying..."
            )

            retry_prompt = f"""The previous summary for the item {display_name} still contained placeholder text. 
            
Please create a complete summary WITHOUT ANY PLACEHOLDERS. Replace every [placeholder] with actual information.

For any section where you're uncertain, provide a reasonable description based on similar items or your knowledge of the Pokémon universe.

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
                        "content": "You are a Pokémon expert who creates detailed and accurate summaries of items. You MUST replace ALL placeholder text with actual information, even if you need to make educated guesses based on similar items. Always include a blank line after each section header before starting bullet points.",
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                max_tokens=max_tokens,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for information about Pokémon items",
                        },
                    }
                ],
                tool_choice="auto",
            )

            result = retry_response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)  # Reuse the same formatting function

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating item summary with OpenAI: {e}")

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a Pokémon item.

**Basic Information:**

- **Category:** {category if 'category' in locals() else "Item"}
- **Cost:** {cost if 'cost' in locals() else "Varies"} Pokédollars
- **Availability:** Can be found in Pokémon games

**Effect:**

- Used by trainers to help their Pokémon
- Provides a specific benefit in battles or exploration

**In-Game Use:**

- Can be used in various situations in the games
- May be consumed on use or held by a Pokémon
- Available in Pokémon Centers or from special vendors

**Game Appearances:**

- Featured in multiple generations of Pokémon games
- Consistent functionality across most game versions
- Part of the core item collection system

**Strategic Applications:**

- May be used in competitive play for specific strategies
- Can provide advantages in certain battle situations
- Some trainers use it for specific team compositions

**Interesting Facts:**

- Part of the Pokémon universe's item ecosystem
- Has a design that reflects its purpose
- Recognized by most Pokémon players
"""

        return fallback_template


def generate_type_summary(
    type_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon type using OpenAI with the type template."""
    try:
        # Get the display name
        display_name = type_name.replace("-", " ").title()

        # Try to get Type data from the API
        import requests
        import re

        type_data = {}
        generation = "Unknown"
        double_damage_from = []
        double_damage_to = []
        half_damage_from = []
        half_damage_to = []
        no_damage_from = []
        no_damage_to = []

        try:
            # Fetch from type endpoint
            type_response = requests.get(f"https://pokeapi.co/api/v2/type/{type_name}")
            if type_response.status_code == 200:
                type_data = type_response.json()

                # Get generation information
                if "generation" in type_data and "name" in type_data["generation"]:
                    generation = format_generation(type_data["generation"]["name"])

                # Get damage relations
                if "damage_relations" in type_data:
                    damage_relations = type_data["damage_relations"]

                    # Extract type names from damage relation objects
                    double_damage_from = [
                        t["name"].title()
                        for t in damage_relations.get("double_damage_from", [])
                    ]
                    double_damage_to = [
                        t["name"].title()
                        for t in damage_relations.get("double_damage_to", [])
                    ]
                    half_damage_from = [
                        t["name"].title()
                        for t in damage_relations.get("half_damage_from", [])
                    ]
                    half_damage_to = [
                        t["name"].title()
                        for t in damage_relations.get("half_damage_to", [])
                    ]
                    no_damage_from = [
                        t["name"].title()
                        for t in damage_relations.get("no_damage_from", [])
                    ]
                    no_damage_to = [
                        t["name"].title()
                        for t in damage_relations.get("no_damage_to", [])
                    ]

        except Exception as e:
            # Just log the error, we'll still generate a summary with less info
            current_app.logger.error(f"Error fetching Type data: {e}")

        # If we have a base summary already, use it as the starting point
        if base_summary:
            summary_to_improve = base_summary

            # Prepare the prompt
            prompt = f"""{custom_instructions}
            
Improve the following Pokémon type summary for {display_name}. Maintain the structure and sections of the summary.
Ensure all information is accurate and maintain the markdown formatting with bold headings.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:

**Section Header:**

- Bullet point 1
- Bullet point 2

{summary_to_improve}
"""
        else:
            # Prepare damage relation strings
            weaknesses = ", ".join(double_damage_from) if double_damage_from else "None"
            strengths = ", ".join(double_damage_to) if double_damage_to else "None"
            resistances = ", ".join(half_damage_from) if half_damage_from else "None"
            not_very_effective = ", ".join(half_damage_to) if half_damage_to else "None"
            immunities = ", ".join(no_damage_from) if no_damage_from else "None"
            no_effect = ", ".join(no_damage_to) if no_damage_to else "None"

            # Custom Template with proper spacing after headers for types
            template = f"""**{display_name}** is a type of Pokémon introduced in {generation}.

**Type Effectiveness:**

- **Super Effective Against:** {strengths}
- **Not Very Effective Against:** {not_very_effective}
- **No Effect Against:** {no_effect}
- **Weak To:** {weaknesses}
- **Resistant To:** {resistances}
- **Immune To:** {immunities}

**Notable Pokémon:**

- [Pure {display_name}-type Pokémon]
- [Popular dual-type Pokémon with {display_name}]
- [Legendary/Mythical Pokémon with this type]

**Move Pool:**

- [Signature moves of this type]
- [Powerful moves of this type]
- [Common moves of this type]

**Competitive Analysis:**

- [Strengths in competitive play]
- [Weaknesses in competitive play]
- [Role in the metagame]

**Historical Changes:**

- [Introduction and initial reception]
- [Balance changes across generations]
- [Notable type effectiveness changes]

**Interesting Facts:**

- [Design inspiration]
- [Cultural references]
- [Type-specific mechanics or gimmicks]
"""

            # Prepare the prompt with specific instructions to avoid returning placeholders
            prompt = f"""{custom_instructions}

You are a Pokémon type expert. Create a comprehensive and detailed summary for the {display_name} type following this exact template structure:

{template}

IMPORTANT INSTRUCTIONS:
1. Fill in ALL placeholders with specific, accurate information about the {display_name} type.
2. Do NOT leave any placeholder text like "[Signature moves of this type]" in your response.
3. Search the web for the most current and accurate information about this type.
4. Include notable Pokémon that have this type, either as a pure type or as part of a dual typing.
5. Describe the competitive strengths and weaknesses of this type in detail.
6. Include specific historical information about how this type has changed across generations.
7. Keep the markdown formatting with bold section headers.
8. Be specific and detailed in your descriptions.
9. Maintain the exact spacing format with a blank line after each section header.

If you don't have enough information for a section, provide your best educated description based on similar types rather than leaving placeholders.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()

        # Use GPT-4o with web search for new information about the type
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed and accurate summaries of Pokémon types with precise information from official sources. You MUST replace all placeholder text with actual information. Always include a blank line after each section header before starting bullet points.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information about Pokémon types",
                    },
                }
            ],
            tool_choice="auto",
        )

        # Check if we have a valid content in the response
        if (
            not hasattr(response.choices[0], "message")
            or not hasattr(response.choices[0].message, "content")
            or response.choices[0].message.content is None
        ):
            # Handle tool outputs if present
            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                # Try to extract information from tool calls
                current_app.logger.warning(
                    "Received tool calls instead of direct content. Processing tool data."
                )
                result = "**" + display_name + "** is a Pokémon type.\n\n"

                # Add some basic information we already have
                result += "**Type Effectiveness:**\n\n"
                if double_damage_from:
                    result += f"- **Weak To:** {', '.join(double_damage_from)}\n"
                if double_damage_to:
                    result += f"- **Super Effective Against:** {', '.join(double_damage_to)}\n"
                if half_damage_from:
                    result += f"- **Resistant To:** {', '.join(half_damage_from)}\n"
                if half_damage_to:
                    result += f"- **Not Very Effective Against:** {', '.join(half_damage_to)}\n"
                if no_damage_from:
                    result += f"- **Immune To:** {', '.join(no_damage_from)}\n"
                if no_damage_to:
                    result += f"- **No Effect Against:** {', '.join(no_damage_to)}\n"

                # Add generation info if available
                if generation != "Unknown":
                    result += (
                        f"\n**Historical Changes:**\n\n- Introduced in {generation}\n"
                    )

                # Add basic fallback content
                result += "\n**Notable Pokémon:**\n\n- Various pure and dual-type Pokémon feature this type\n"
                result += (
                    "\n**Move Pool:**\n\n- Multiple moves are available for this type\n"
                )
                result += "\n**Competitive Analysis:**\n\n- Has specific strengths and weaknesses in competitive play\n"
                result += "\n**Interesting Facts:**\n\n- This type has unique characteristics in the Pokémon world\n"
            else:
                # Fall back to a basic template
                current_app.logger.error(
                    "No valid content or tool calls in API response"
                )
                return fallback_template
        else:
            result = response.choices[0].message.content.strip()

            # Check if the response still contains placeholder text
            placeholder_pattern = r"\[\w+( \w+)*\]"
            if re.search(placeholder_pattern, result):
                # If placeholders remain, try one more time with a more direct prompt
                current_app.logger.warning(
                    f"Detected placeholders in summary for type {type_name}, retrying..."
                )

                retry_prompt = f"""The previous summary for the {display_name} type still contained placeholder text. 
                
Please create a complete summary WITHOUT ANY PLACEHOLDERS. Replace every [placeholder] with actual information.

For any section where you're uncertain, provide a reasonable description based on similar types or your knowledge of the Pokémon universe.

IMPORTANT: Make sure to add a blank line after each section header and before bullet points, like this:
**Section:**

- Bullet point
- Another bullet point

Here's the previous summary that needs to be improved:

{result}"""

                try:
                    retry_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a Pokémon expert who creates detailed and accurate summaries of types. You MUST replace ALL placeholder text with actual information, even if you need to make educated guesses based on similar types. Always include a blank line after each section header before starting bullet points.",
                            },
                            {"role": "user", "content": retry_prompt},
                        ],
                        max_tokens=max_tokens,
                        tools=[
                            {
                                "type": "function",
                                "function": {
                                    "name": "web_search",
                                    "description": "Search the web for information about Pokémon types",
                                },
                            }
                        ],
                        tool_choice="auto",
                    )

                    # Check if the retry has valid content
                    if (
                        hasattr(retry_response.choices[0], "message")
                        and hasattr(retry_response.choices[0].message, "content")
                        and retry_response.choices[0].message.content is not None
                    ):
                        result = retry_response.choices[0].message.content.strip()
                    else:
                        current_app.logger.warning(
                            "Retry response has no valid content, keeping original result"
                        )
                except Exception as e:
                    current_app.logger.error(f"Error in retry request: {e}")
                    # Keep the original result if retry fails

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)  # Reuse the same formatting function

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating type summary with OpenAI: {e}")

        # Fallback to a basic template if the API call fails
        fallback_template = f"""**{display_name}** is a type of Pokémon.

**Type Effectiveness:**

- **Super Effective Against:** Various types
- **Not Very Effective Against:** Various types
- **No Effect Against:** Depends on specific interactions
- **Weak To:** Various types
- **Resistant To:** Various types
- **Immune To:** Depends on specific interactions

**Notable Pokémon:**

- Several pure {display_name}-type Pokémon
- Various dual-type Pokémon featuring {display_name}
- Some notable Legendary or Mythical Pokémon may have this typing

**Move Pool:**

- Variety of moves available to {display_name}-type Pokémon
- Different power levels and effects
- Mix of physical and special attacks

**Competitive Analysis:**

- Has strategic uses in competitive play
- Strengths against certain types and strategies
- Weaknesses that need to be considered when team building

**Historical Changes:**

- Present since early generations of Pokémon games
- May have undergone balance changes over time
- Type effectiveness might have changed across generations

**Interesting Facts:**

- Based on elemental or conceptual themes
- Represented by specific colors and symbols in the games
- Featured in various Pokémon media beyond the games
"""

        return fallback_template


def custom_generate_summary(
    resource_type,
    resource_name,
    base_summary="",
    custom_instructions="",
    max_tokens=2000,
):
    """
    Generate a summary for a resource based on its type.
    This function selects the appropriate template based on the resource type.
    """
    if resource_type == "pokemon":
        return generate_pokemon_summary(
            resource_name, base_summary, custom_instructions, max_tokens
        )
    elif resource_type == "move":
        return generate_move_summary(
            resource_name, base_summary, custom_instructions, max_tokens
        )
    elif resource_type == "ability":
        return generate_ability_summary(
            resource_name, base_summary, custom_instructions, max_tokens
        )
    elif resource_type == "item":
        return generate_item_summary(
            resource_name, base_summary, custom_instructions, max_tokens
        )
    elif resource_type == "type":
        return generate_type_summary(
            resource_name, base_summary, custom_instructions, max_tokens
        )
    else:
        # Generic template for other resource types
        return f"Summary for {resource_name} ({resource_type}). This resource type doesn't have a specific template yet."


# Update the route to use the new function
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
        new_summary = generate_pokemon_summary(
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
        summary = generate_pokemon_summary(pokemon_name)

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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python summary_review.py <csv_filename>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    process_csv_file(csv_filename)
