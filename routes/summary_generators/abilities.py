import requests
import re
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary, format_generation


def generate_ability_summary(
    ability_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon ability using OpenAI with the ability template."""
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

- Fundamentally changes how a Pokémon interacts with core battle mechanics and systems
- May provide specific immunities to certain types or status conditions, stat boosts in particular situations, or other beneficial effects
- Can significantly alter how the Pokémon performs in battle compared to other abilities

**In Battle:**

- Automatically activates under specific conditions during battle, such as when HP is low or weather effects are present
- Can directly influence the Pokémon's stats, move effectiveness, or ability to be affected by certain moves
- Creates unique strategic opportunities that skilled trainers can leverage to their advantage
- May interact with teammates' abilities or moves in interesting ways

**Pokémon with this Ability:**

- Found on multiple Pokémon species across different generations of the games
- Can appear as either a standard ability that Pokémon normally have, or as a hidden ability that requires special methods to obtain
- Often thematically connected to the Pokémon's design, type, or role in battle
- May be signature to certain evolutionary lines or legendary Pokémon

**Competitive Use:**

- Carefully considered during team building as it can enable or enhance specific battle strategies
- Overall effectiveness and usage rates vary depending on the current competitive metagame and popular strategies
- Can complement particular move sets and team compositions to create powerful combinations
- May influence whether certain Pokémon are viable choices in competitive play

**Interesting Facts:**

- Originally introduced in one of the core Pokémon games as part of the ability system
- Balance adjustments may have been made in subsequent generations to strengthen or weaken its effects
- The ability's name typically reflects its function or effect in an intuitive way
- Part of the ongoing evolution of Pokémon battle mechanics since Generation III
"""

        return fallback_template
