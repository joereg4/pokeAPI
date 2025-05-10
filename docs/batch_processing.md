# Batch Processing Pokémon Summaries

When generating summaries for a large number of Pokémon, you may encounter memory issues that can cause the server to crash with "Internal Server Error". This happens because generating summaries using OpenAI's API can be memory-intensive, especially when processing many Pokémon at once.

This documentation explains how to use the batch processing scripts to generate summaries for multiple Pokémon without running into memory issues.

## Scripts Overview

Two scripts have been created to help with batch processing:

1. `scripts/generate_pokemon_list.py` - Fetches a list of Pokémon from the PokeAPI and saves it to a file
2. `scripts/batch_summary_generator.py` - Processes Pokémon in smaller batches to avoid memory issues

## Step 1: Generate a List of Pokémon

First, generate a list of Pokémon you want to process:

```bash
python scripts/generate_pokemon_list.py --limit 100 --output my_pokemon_list.txt
```

Options:
- `--limit`: Maximum number of Pokémon to fetch (default: 1000)
- `--offset`: Offset in the API results (default: 0)
- `--output`: Output file name (default: pokemon_list.txt)

## Step 2: Process Pokémon in Batches

Next, use the batch summary generator to process the Pokémon in smaller batches:

```bash
python scripts/batch_summary_generator.py --file my_pokemon_list.txt --batch-size 5 --delay 3
```

Options:
- `--file`: File containing list of Pokémon names (one per line)
- `--names`: Alternative to --file, you can provide a comma-separated list of Pokémon names
- `--batch-size`: Number of Pokémon to process in each batch (default: 5)
- `--delay`: Delay in seconds between batches to allow memory cleanup (default: 2)

## Example Workflow

Here's a complete example workflow:

1. Generate a list of the first 50 Pokémon:
   ```bash
   python scripts/generate_pokemon_list.py --limit 50 --output gen1_pokemon.txt
   ```

2. Process them in batches of 5 with a 3-second delay between batches:
   ```bash
   python scripts/batch_summary_generator.py --file gen1_pokemon.txt --batch-size 5 --delay 3
   ```

3. If some Pokémon fail, you can retry just those specific ones:
   ```bash
   python scripts/batch_summary_generator.py --names "pikachu,charizard,bulbasaur" --batch-size 1 --delay 5
   ```

## Recommended Batch Sizes

- **For development environments**: 5-10 Pokémon per batch with a 2-3 second delay
- **For production environments**: 3-5 Pokémon per batch with a 3-5 second delay
- **For problematic Pokémon**: Process them one at a time with a longer delay (5-10 seconds)

## Troubleshooting

If you still encounter memory issues:
1. Reduce the batch size to 1
2. Increase the delay between batches
3. Check the server logs for specific error messages
4. Consider restarting the server before processing large batches

## Server Memory Management

For more permanent solutions to memory issues:
1. Increase the server's available memory (RAM)
2. Optimize the `summary_review.py` code to use less memory
3. Configure the web server to have better memory limits and management 