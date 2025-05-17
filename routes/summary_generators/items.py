import requests
import re
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary


def generate_item_summary(
    item_name, base_summary="", custom_instructions="", max_tokens=2000
):
    """Generate a summary specifically for a Pokémon item using OpenAI with the item template."""
    try:
        # Get the display name
        display_name = item_name.replace("-", " ").title()

        # Try to get Item data from the API
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
