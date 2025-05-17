import re
import os
from openai import OpenAI
from flask import current_app


def get_openai_client():
    """Get OpenAI client with API key from environment"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def format_pokemon_summary(summary):
    """
    Ensure proper markdown formatting with extra line breaks after headers.
    This makes bullet point lists render properly in markdown.
    """
    # Add a line break after each section header (bold text followed by a colon)
    formatted_summary = re.sub(r"(\*\*[^*]+:\*\*)\n-", r"\1\n\n-", summary)

    # Handle edge cases where there might be no bullet points by ensuring consistent structure
    formatted_summary = re.sub(
        r"(\*\*[^*]+:\*\*)\n([^\n-])", r"\1\n\n\2", formatted_summary
    )

    return formatted_summary


def format_generation(generation_text):
    """
    Format generation text with properly capitalized Roman numerals.
    Example: "generation ix" -> "Generation IX"
    """
    if not generation_text:
        return "Unknown"

    # First capitalize the word "generation"
    result = generation_text.replace("-", " ").title()

    # Find Roman numerals and make them uppercase
    roman_numeral_pattern = r"\b([IiVvXxLlCcDdMm]+)\b"

    def uppercase_roman(match):
        return match.group(0).upper()

    result = re.sub(roman_numeral_pattern, uppercase_roman, result)

    return result
