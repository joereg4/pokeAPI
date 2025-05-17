import requests
import re
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary, format_generation


def generate_type_summary(
    type_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon type using OpenAI with the type template."""
    try:
        # Get the display name
        display_name = type_name.replace("-", " ").title()

        # Try to get Type data from the API
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

- **Super Effective Against:** Various types, dealing double damage to certain Pokémon types based on established type matchups
- **Not Very Effective Against:** Various types that resist this type's moves, only dealing half damage
- **No Effect Against:** Certain types may be completely immune to moves of this type, dealing no damage at all
- **Weak To:** Takes double damage from moves of specific types that are super effective against it
- **Resistant To:** Only takes half damage from moves of certain types due to defensive advantages
- **Immune To:** May have complete immunity to certain types of moves, taking no damage from them

**Notable Pokémon:**

- Several pure {display_name}-type Pokémon that exemplify the core characteristics of this type
- Various dual-type Pokémon featuring {display_name} as either their primary or secondary typing, creating interesting type combinations
- Some notable Legendary or Mythical Pokémon may have this typing, highlighting its significance in the Pokémon world

**Move Pool:**

- Extensive variety of moves available to {display_name}-type Pokémon, ranging from basic attacks to powerful signature moves
- Different power levels and effects, including status moves, utility moves, and powerful finishing moves
- Mix of physical and special attacks that cater to different Pokémon's offensive stats and battle styles

**Competitive Analysis:**

- Has strategic uses in competitive play, with specific roles and niches in various formats
- Strengths against certain types and strategies make it valuable for countering common threats
- Weaknesses that need to be considered when team building, requiring proper support from teammates

**Historical Changes:**

- Present since early generations of Pokémon games, forming part of the core type system
- May have undergone balance changes over time to maintain competitive fairness
- Type effectiveness might have changed across generations as new types were introduced or mechanics were adjusted

**Interesting Facts:**

- Based on elemental or conceptual themes that reflect real-world phenomena or ideas
- Represented by specific colors and symbols in the games that reinforce its thematic identity
- Featured in various Pokémon media beyond the games, including the anime, manga, and merchandise
"""

        return fallback_template
