import requests
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary


def generate_ability_summary(ability_name, custom_instructions="", max_tokens=2000):
    """Generate a summary for a Pokémon ability using OpenAI with the Intimidate example template."""
    try:
        # Get the display name
        display_name = ability_name.replace("-", " ").title()

        # Try to get Ability data from the API
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
                    generation = (
                        ability_data["generation"]["name"]
                        .replace("generation-", "")
                        .upper()
                    )

        except Exception as e:
            current_app.logger.error(f"Error fetching Ability data: {e}")

        # Example template to show the desired format and structure
        example_template = """**Intimidate** is a Pokémon ability introduced in Generation III.

**Effect:**

- Lowers the Attack stat of opposing Pokémon by one stage when the user enters battle
- Activates when the user is sent out or when an opponent switches in
- Can be activated multiple times in a battle
- Does not affect Pokémon with the Clear Body, Hyper Cutter, or White Smoke abilities

**In Battle:**

- Provides immediate defensive utility by weakening physical attackers
- Particularly effective against physical sweepers and priority move users
- Can force switches, giving the user's team momentum
- Works well with defensive Pokémon that can take advantage of weakened opponents

**Pokémon with this Ability:**

- Arcanine (standard ability)
- Gyarados (standard ability)
- Landorus-Therian (signature ability)
- Many other physical attackers and defensive Pokémon

**Competitive Use:**

- Highly valued in competitive play for its consistent utility
- Common on defensive pivots and support Pokémon
- Can be used to check physical attackers without using a move
- Often paired with Intimidate cycling strategies using multiple users

**Interesting Facts:**

- One of the most widely distributed abilities in the series
- Has remained competitively relevant since its introduction
- The ability's name reflects its psychological warfare aspect
- Featured prominently in the anime, often shown with a visual effect
"""

        # Prepare the prompt with specific instructions and the example
        prompt = f"""{custom_instructions}

You are a Pokémon ability expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Effect: {effect}
   - Generation introduced: {generation}
   - Battle mechanics and interactions
   - Notable Pokémon that have this ability
   - Competitive applications
   - Interesting facts and trivia
3. Search the web for the most current and accurate information.
4. Keep the markdown formatting with bold section headers.
5. Maintain the exact spacing format with a blank line after each section header.
6. Be specific and detailed in your descriptions.
7. If you don't have enough information for a section, provide your best educated description based on similar abilities rather than leaving it vague.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon ability expert who creates detailed, accurate summaries about abilities. Use web search to ensure your information is current and accurate.",
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
        current_app.logger.error(f"Error generating ability summary with OpenAI: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")
