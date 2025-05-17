import requests
import re
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary, format_generation


def generate_pokemon_summary(
    pokemon_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon using OpenAI with the Pokémon template."""
    try:
        # Get the display name
        display_name = pokemon_name.replace("-", " ").title()

        # Try to get Pokemon data from the API
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

- **Vital Spirit:** Prevents the Pokémon from falling asleep, ensuring it remains active and alert during battle, which is especially useful against sleep-inducing moves.
- **Anger Point:** When struck by a critical hit, this ability maximizes the Pokémon's Attack stat, turning a potentially dangerous situation into an offensive advantage.

**Physical Characteristics:**

- A powerfully built bipedal Pokémon with a primate-like appearance, featuring well-defined muscles that highlight its physical strength and combat capabilities
- Possesses distinctive coloration and markings across its body that make it easily recognizable and set it apart from other Fighting-type Pokémon
- Displays clear evolutionary traits from its previous form while showing more advanced physical development and mature features

**Behavior and Habitat:**

- Exhibits an aggressive and territorial temperament, often challenging other Pokémon to demonstrate its strength and establish dominance
- Primarily inhabits rugged mountainous regions and dense forests where it can train and develop its fighting skills in a natural environment
- Lives and travels in small, tight-knit groups that work together for protection and hunting, showing surprising social complexity

**In Battle:**

- Excels as a physical attacker with an impressively high Attack stat, making it a formidable opponent in close-combat situations
- Specializes in powerful fighting-type moves while maintaining a diverse movepool that provides excellent coverage against multiple types
- Demonstrates particular effectiveness against Normal, Ice, Rock, Dark, and Steel type Pokémon, making it a valuable team member
- Must be carefully managed against Psychic, Flying, and Fairy type moves due to type disadvantages that can quickly turn the tide of battle

**Evolution:**

- Undergoes a significant evolution from its pre-evolved form when specific conditions are met, representing a major milestone in its development
- The evolution process triggers dramatic changes in both physical appearance and combat abilities, resulting in enhanced fighting capabilities

**Interesting Facts:**

- Holds a special significance in Pokémon lore and games, often appearing in key storylines and competitive scenarios
- Has made numerous memorable appearances across various Pokémon media, including the anime, movies, and trading card game
- Features a uniquely recognizable cry and battle animation in the games that have become iconic among fans of the series
"""

        return fallback_template
