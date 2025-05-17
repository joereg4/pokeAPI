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
