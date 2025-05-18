import requests
import re
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary


def generate_move_summary(
    move_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon move using OpenAI with the move template."""
    try:
        # Get the display name
        display_name = move_name.replace("-", " ").title()

        # Try to get Move data from the API
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
            # Example template to show the desired format and structure
            example_template = """**Thunderbolt** is an Electric-type Special move in the Pokémon games.

**Basic Information:**

- **Type:** Electric
- **Category:** Special
- **Power:** 90
- **Accuracy:** 100%
- **PP:** 15

**Effect:**

- Deals significant Electric-type damage
- Has a 10% chance to paralyze the target
- Can hit non-adjacent Pokémon in Triple Battles

**In-Game Description:**

- A strong electric blast is loosed at the target. It may also leave the target with paralysis.

**Notable Users:**

- Pikachu (signature move in the anime)
- Jolteon (excellent STAB move)
- Zapdos (powerful coverage option)
- Many Electric-type Pokémon learn it via TM

**Strategic Use:**

- Reliable STAB move for Electric-types
- Good coverage against Water and Flying types
- High accuracy makes it more reliable than Thunder
- Common choice for special attackers

**Interesting Facts:**

- Introduced in Generation I
- Featured prominently in the anime as Pikachu's signature move
- Based on the real-world phenomenon of lightning
- Has remained competitively viable across all generations
"""

            # Prepare the prompt with specific instructions and the example
            prompt = f"""{custom_instructions}

You are a Pokémon move expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Type: {move_type}
   - Category: {damage_class}
   - Power: {power}
   - Accuracy: {accuracy}%
   - PP: {pp}
   - Effects and secondary effects
   - Notable Pokémon that learn it
   - Strategic applications
   - Interesting facts
3. Search the web for the most current and accurate information.
4. Keep the markdown formatting with bold section headers.
5. Maintain the exact spacing format with a blank line after each section header.
6. Be specific and detailed in your descriptions.
7. If you don't have enough information for a section, provide your best educated description based on similar moves rather than leaving it vague.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon move expert who creates detailed, accurate summaries about moves. Use web search to ensure your information is current and accurate.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )

        # Check if we have a valid content in the response
        if (
            not hasattr(response.choices[0], "message")
            or not hasattr(response.choices[0].message, "content")
            or response.choices[0].message.content is None
        ):
            current_app.logger.error("No valid content in API response")
            raise Exception(
                "Failed to generate summary: No valid content in API response"
            )

        result = response.choices[0].message.content.strip()

        # Post-process the summary to ensure proper formatting
        result = format_pokemon_summary(result)

        return result

    except Exception as e:
        current_app.logger.error(f"Error generating move summary with OpenAI: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")
