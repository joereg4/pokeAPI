import requests
from flask import current_app
from .utils import get_openai_client, format_pokemon_summary


def generate_type_summary(type_name, custom_instructions="", max_tokens=2000):
    """Generate a summary for a Pokémon type using OpenAI with the Fire example template."""
    try:
        # Get the display name
        display_name = type_name.replace("-", " ").title()

        # Try to get Type data from the API
        type_data = {}
        generation = "Unknown"

        try:
            # Fetch from type endpoint
            type_response = requests.get(f"https://pokeapi.co/api/v2/type/{type_name}")
            if type_response.status_code == 200:
                type_data = type_response.json()

                # Get generation information
                if "generation" in type_data and "name" in type_data["generation"]:
                    generation = (
                        type_data["generation"]["name"]
                        .replace("generation-", "")
                        .upper()
                    )

        except Exception as e:
            current_app.logger.error(f"Error fetching Type data: {e}")

        # Example template to show the desired format and structure
        example_template = """**Fire** is one of the eighteen Pokémon types, introduced in Generation I.

**Basic Information:**

- **Introduced:** Generation I
- **Strong Against:** Bug, Steel, Grass, Ice
- **Weak Against:** Rock, Fire, Water, Dragon
- **Resistant To:** Fire, Grass, Ice, Bug, Steel, Fairy
- **Vulnerable To:** Ground, Rock, Water

**Characteristics:**

- Associated with heat, passion, and energy
- Often represents power and intensity
- Many Fire-type Pokémon have high Special Attack stats
- Commonly found in volcanic regions and hot climates

**Notable Pokémon:**

- Charizard (Fire/Flying)
- Arcanine (Fire)
- Blaziken (Fire/Fighting)
- Volcarona (Bug/Fire)

**Competitive Use:**

- Strong offensive presence with powerful STAB moves
- Good coverage against common defensive types
- Often used as wallbreakers or sweepers
- Can be vulnerable to common coverage moves

**Interesting Facts:**

- One of the three starter types in the original games
- Has maintained consistent type matchups since Generation I
- Many Fire-type Pokémon are based on mythical creatures
- Often associated with the color red in the games
"""

        # Prepare the prompt with specific instructions and the example
        prompt = f"""{custom_instructions}

You are a Pokémon type expert. Create a comprehensive and detailed summary for {display_name} following the same structure and level of detail as this example:

{example_template}

IMPORTANT INSTRUCTIONS:
1. Create a complete summary for {display_name} with the same sections and formatting as the example.
2. Include specific, accurate information about {display_name}'s:
   - Generation introduced: {generation}
   - Type matchups (super effective, not very effective, etc.)
   - Characteristics and themes
   - Notable Pokémon of this type
   - Competitive applications
   - Interesting facts and trivia
3. Search the web for the most current and accurate information.
4. Keep the markdown formatting with bold section headers.
5. Maintain the exact spacing format with a blank line after each section header.
6. Be specific and detailed in your descriptions.
7. If you don't have enough information for a section, provide your best educated description based on similar types rather than leaving it vague.
"""

        # Call OpenAI API with GPT-4o and web search capability
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Pokémon type expert who creates detailed, accurate summaries about types. Use web search to ensure your information is current and accurate.",
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
        current_app.logger.error(f"Error generating type summary with OpenAI: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")
