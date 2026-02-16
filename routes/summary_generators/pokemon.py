from flask import current_app
from pokedex.client import client as pokeapi
from .utils import get_openai_client, format_pokemon_summary, format_generation


def generate_pokemon_summary(pokemon_name, custom_instructions="", max_tokens=2000):
    """Generate a summary for a Pokémon using OpenAI with the Pikachu example template."""
    try:
        # Get the display name
        display_name = pokemon_name.replace("-", " ").title()

        # Try to get Pokemon data from the API
        pokemon_data = {}
        generation = "Unknown"

        try:
            # Fetch from pokemon endpoint via unified client
            pokemon_data = pokeapi.fetch_url_json(
                f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
            )

            # Try to extract generation from species data
            try:
                species_url = pokemon_data.get("species", {}).get("url")
                if species_url:
                    species_data = pokeapi.fetch_url_json(species_url)
                    if "generation" in species_data:
                        generation = format_generation(
                            species_data["generation"]["name"]
                        )
            except Exception as e:
                current_app.logger.error(f"Error fetching species data: {e}")

        except Exception as e:
            current_app.logger.error(f"Error fetching Pokemon data: {e}")

        # Get types
        types = []
        if "types" in pokemon_data:
            types = [t["type"]["name"].title() for t in pokemon_data["types"]]

        # Example template to show the desired format and structure
        example_template = """**Pikachu** is an Electric-type Pokémon introduced in Generation I.

**Type:** Electric

**Abilities:**

- **Static:** May paralyze opponents on contact
- **Lightning Rod:** Draws in all Electric-type moves to boost Special Attack

**Physical Characteristics:**

- Small, yellow, mouse-like Pokémon
- Red cheeks that store electricity
- Long, pointed ears with black tips
- Lightning bolt-shaped tail

**Behavior and Habitat:**

- Lives in forests and grasslands
- Often found near power plants
- Forms strong bonds with trainers
- Communicates through electrical signals

**In Battle:**

- Fast special attacker
- Signature moves: Thunderbolt, Volt Tackle
- Strong against Water and Flying types
- Weak against Ground types

**Evolution:**

- Evolves from Pichu when friendship is high
- Evolves into Raichu with a Thunder Stone

**Interesting Facts:**

- Mascot of the Pokémon franchise
- Ash's signature Pokémon in the anime
- Based on the Japanese word "pikapika" (sparkle)
"""

        # Prepare the prompt with specific instructions and the example
        prompt = f"""{custom_instructions}

You are a Pokémon expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Type(s): {" / ".join(types) if types else "Unknown"}
   - Abilities (both primary and hidden)
   - Physical characteristics
   - Behavior and habitat
   - Battle strategies and notable moves
   - Evolution details
   - Interesting facts
3. Search the web for the most current and accurate information.
4. Keep the markdown formatting with bold section headers.
5. Maintain the exact spacing format with a blank line after each section header.
6. Be specific and detailed in your descriptions.
7. If you don't have enough information for a section, provide your best educated description based on similar Pokémon rather than leaving it vague.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon expert who creates detailed, accurate summaries about Pokémon. Use web search to ensure your information is current and accurate.",
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
        current_app.logger.error(f"Error generating summary with OpenAI: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")
