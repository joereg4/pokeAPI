import requests
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary


def generate_item_summary(item_name, custom_instructions="", max_tokens=2000):
    """Generate a summary for a Pokémon item using OpenAI with the Leftovers example template."""
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
            current_app.logger.error(f"Error fetching Item data: {e}")

        # Example template to show the desired format and structure
        example_template = """**Leftovers** is a held item in the Pokémon games.

**Basic Information:**

- **Category:** Held Item
- **Cost:** 200,000 Pokédollars
- **Availability:** Can be purchased at the Battle Tower/Frontier

**Effect:**

- Restores 1/16 of the holder's maximum HP at the end of each turn
- Works in both single and double battles
- Effect is not prevented by most abilities
- Can be used multiple times in a battle

**In-Game Use:**

- Held by defensive Pokémon to increase longevity
- Particularly effective on Pokémon with high HP stats
- Can be used to offset damage from status conditions
- Useful for stalling strategies

**Game Appearances:**

- Introduced in Generation II
- Available in every main series game since
- Often given as a reward for completing difficult challenges
- Can be purchased in post-game facilities

**Strategic Applications:**

- Essential item for defensive and stalling Pokémon
- Commonly used on walls and tanks
- Helps maintain momentum in longer battles
- Can be used to recover HP without using a move

**Interesting Facts:**

- One of the most iconic held items in competitive play
- Has maintained consistent functionality across generations
- The name refers to food scraps that provide sustenance
- Featured in the anime as a common held item
"""

        # Prepare the prompt with specific instructions and the example
        prompt = f"""{custom_instructions}

You are a Pokémon item expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Category: {category}
   - Cost: {cost} Pokédollars
   - Effect: {effect}
   - In-game usage and availability
   - Strategic applications
   - Interesting facts and trivia
3. Search the web for the most current and accurate information.
4. Keep the markdown formatting with bold section headers.
5. Maintain the exact spacing format with a blank line after each section header.
6. Be specific and detailed in your descriptions.
7. If you don't have enough information for a section, provide your best educated description based on similar items rather than leaving it vague.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon item expert who creates detailed, accurate summaries about items. Use web search to ensure your information is current and accurate.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=max_tokens,
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
        current_app.logger.error(f"Error generating item summary with OpenAI: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")
