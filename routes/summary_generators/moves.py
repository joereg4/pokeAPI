import requests
from flask import current_app
from pokedex.utils import Config
from .utils import get_openai_client, format_pokemon_summary


def generate_move_summary(move_name, custom_instructions="", max_tokens=2000):
    """Generate a summary for a Pokémon move using OpenAI with the Thunderbolt example template."""
    try:
        # Get the display name
        display_name = move_name.replace("-", " ").title()

        # Try to get Move data from the API
        move_data = {}
        effect = "Unknown"
        generation = "Unknown"

        try:
            # Fetch from move endpoint
            move_response = requests.get(f"https://pokeapi.co/api/v2/move/{move_name}", timeout=Config.HTTP_TIMEOUT)
            if move_response.status_code == 200:
                move_data = move_response.json()

                # Extract basic move information
                if "effect_entries" in move_data:
                    # Try to find English effect description
                    for entry in move_data["effect_entries"]:
                        if entry.get("language", {}).get("name") == "en":
                            effect = entry.get("effect", "Unknown")
                            break

                # Get generation information
                if "generation" in move_data and "name" in move_data["generation"]:
                    generation = (
                        move_data["generation"]["name"]
                        .replace("generation-", "")
                        .upper()
                    )

        except Exception as e:
            current_app.logger.error(f"Error fetching Move data: {e}")

        # Example template to show the desired format and structure
        example_template = """**Thunderbolt** is an Electric-type move introduced in Generation I.

**Basic Information:**

- **Type:** Electric
- **Category:** Special
- **Power:** 90
- **Accuracy:** 100%
- **PP:** 15

**Effect:**

- Deals damage to the target
- Has a 10% chance to paralyze the target
- Can hit non-adjacent Pokémon in Triple Battles
- Affected by Lightning Rod and Motor Drive abilities

**In-Game Description:**

- A strong electric blast crashes down on the target
- May leave the target with paralysis
- One of the most reliable Electric-type moves

**Notable Users:**

- Pikachu (signature move)
- Jolteon (STAB move)
- Zapdos (STAB move)
- Many other Electric-type Pokémon

**Strategic Use:**

- Reliable STAB move for Electric-types
- Good coverage against Water and Flying types
- Higher accuracy than Thunder
- Common choice for special attackers

**Interesting Facts:**

- One of the most iconic moves in the series
- Featured prominently in the anime
- Has maintained consistent power and accuracy since Generation I
- Often used as a benchmark for balanced move design
"""

        # Prepare the prompt with specific instructions and the example
        prompt = f"""{custom_instructions}

You are a Pokémon move expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Effect: {effect}
   - Generation introduced: {generation}
   - Battle mechanics and interactions
   - Notable Pokémon that learn this move
   - Strategic applications
   - Interesting facts and trivia
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
            max_completion_tokens=max_tokens,
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
