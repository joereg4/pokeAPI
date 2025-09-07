# Interactive Summary Updater

The Interactive Summary Updater is a powerful tool for reviewing and updating summaries for specific resource types. It provides both interactive mode (manual review) and batch mode (automatic updates) with progress tracking and resume capabilities.

## Overview

This tool addresses the need to improve existing summaries that may have been generated earlier with less sophisticated prompts or templates. It allows you to:

- **Review current summaries** with nice markdown formatting
- **Generate new summaries** using the latest AI templates
- **Approve or reject** each new summary
- **Track progress** and resume interrupted sessions
- **Process in batches** for efficiency

## Features

### Interactive Mode (Default)
- Shows current summary for each resource
- Asks for decision: Skip, Update, or Quit
- Generates new summary using existing templates
- Shows new summary for approval
- Saves progress automatically

### Batch Mode (`--update-all`)
- Automatically updates all remaining resources
- 1-second delay between updates (as requested)
- Progress bar with real-time updates
- No manual approval required

### Progress Tracking
- Saves progress to `data/summary_progress.json`
- Tracks completed resources per resource type
- Resumes from where you left off
- File is automatically gitignored

### Resume Capability
- Interrupt and resume anytime
- Skip already completed resources
- Start from specific resource with `--start-from`

## Prerequisites

### Required Dependencies

Install the required Python packages:

```bash
pipenv install rich
```

### Database Setup

Ensure your local PostgreSQL database is running and accessible:

```bash
# Check if database is running
psql -d pokeapi -c "SELECT COUNT(*) FROM resources WHERE resource = 'pokemon';"
```

## Usage

### Interactive Mode

Review and update summaries one by one:

```bash
# Basic interactive mode
python3 scripts/interactive_summary_updater.py --resource pokemon

# Start from a specific resource
python3 scripts/interactive_summary_updater.py --resource pokemon --start-from "charmander"
```

**Interactive Flow:**
```
=== Pokemon Summary Updater ===
Mode: Interactive
Total resources: 1308
Already completed: 25
Remaining: 1283

Progress: 1/1283
Current: bulbasaur

┌─ Current Summary ─────────────────────────────────────────┐
│ # Bulbasaur                                               │
│ A dual-type Grass/Poison Pokémon, Bulbasaur is known for │
│ the plant bulb on its back that grows as it evolves...   │
└──────────────────────────────────────────────────────────┘

[S]kip, [U]pdate, [Q]uit? u
Generating new summary...

┌─ New Summary ─────────────────────────────────────────────┐
│ # Bulbasaur                                               │
│ A dual-type Grass/Poison Pokémon, Bulbasaur is known for │
│ the plant bulb on its back that grows as it evolves...   │
│                                                           │
│ ## Biology                                                │
│ Bulbasaur is a small, quadrupedal Pokémon with a green   │
│ body and darker green spots...                            │
└──────────────────────────────────────────────────────────┘

Accept this summary? [Y/n]: y
✓ Summary updated!
```

### Batch Mode

Update all remaining resources automatically:

```bash
# Update all pokemon summaries
python3 scripts/interactive_summary_updater.py --resource pokemon --update-all

# Update all abilities starting from a specific point
python3 scripts/interactive_summary_updater.py --resource ability --update-all --start-from "stench"
```

**Batch Mode Flow:**
```
=== Pokemon Summary Updater ===
Mode: Batch (Update All)
Total resources: 1308
Already completed: 25
Remaining: 1283

Proceed with updating 1283 resources? [Y/n]: y

⠋ Processing bulbasaur ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% 0/1283
⠋ Processing ivysaur  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   1% 13/1283
⠋ Processing venusaur ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   2% 26/1283
...

✓ Batch update completed!
Processed: 1283 resources
```

## Command Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--resource` | Yes | Resource type to process (pokemon, move, ability, item, type) |
| `--update-all` | No | Run in batch mode (update all automatically) |
| `--start-from` | No | Start processing from this resource name (alphabetically) |

## Supported Resource Types

- **pokemon** - Pokémon species summaries
- **move** - Move descriptions and effects
- **ability** - Ability descriptions and effects
- **item** - Item descriptions and usage
- **type** - Type effectiveness and characteristics

## Progress Tracking

### Progress File Location

Progress is saved to `data/summary_progress.json`:

```json
{
  "pokemon": {
    "completed": ["bulbasaur", "ivysaur", "venusaur"],
    "last_run": "2024-01-15T10:30:00Z"
  },
  "ability": {
    "completed": ["stench", "drizzle"],
    "last_run": "2024-01-15T11:45:00Z"
  }
}
```

### Resume Capability

The tool automatically:
- Skips resources that have already been processed
- Resumes from where you left off
- Tracks progress per resource type
- Saves progress after each decision

### Interrupt and Resume

You can safely interrupt the tool at any time:
- Press `Ctrl+C` to quit
- Progress is automatically saved
- Restart with the same command to resume

## Integration with Existing Workflow

### Using with Database Management Scripts

After updating summaries locally, use the existing upload script to sync with production:

```bash
# 1. Update summaries locally
python3 scripts/interactive_summary_updater.py --resource pokemon --update-all

# 2. Upload to production (with automatic backup)
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

### Using with Summary Review Interface

The tool uses the same summary generation functions as the web interface:
- Same AI templates and prompts
- Same quality and formatting
- Consistent with existing summaries

## Best Practices

### For Interactive Mode
1. **Start small**: Test with a few resources first
2. **Use --start-from**: Jump to specific sections
3. **Review carefully**: Check new summaries before accepting
4. **Take breaks**: Use 'Q' to quit and resume later

### For Batch Mode
1. **Test first**: Run a few resources in interactive mode
2. **Monitor progress**: Watch for any errors or issues
3. **Backup first**: Use the upload script's backup feature
4. **Verify results**: Check a few updated summaries

### General Tips
1. **One resource type at a time**: Focus on one type per session
2. **Regular commits**: Commit progress to git regularly
3. **Monitor disk space**: Progress file grows with completed items
4. **Check logs**: Monitor for any API or database errors

## Troubleshooting

### Common Issues

**"No module named 'rich'"**
```bash
pipenv install rich
```

**"Database connection error"**
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env file
- Verify database exists and is accessible

**"Progress file not found"**
- The tool creates the directory automatically
- Check file permissions in the project directory

**"API rate limiting"**
- The tool includes delays to prevent rate limiting
- If issues persist, increase delays in the code

### Getting Help

1. **Check the logs**: Look for error messages in the console
2. **Verify dependencies**: Ensure all required packages are installed
3. **Test database connection**: Use the existing database scripts
4. **Check progress file**: Verify `data/summary_progress.json` exists

## Examples

### Complete Workflow Example

```bash
# 1. Start interactive review of pokemon summaries
python3 scripts/interactive_summary_updater.py --resource pokemon

# 2. Review a few, then quit with 'Q'
# 3. Resume from where you left off
python3 scripts/interactive_summary_updater.py --resource pokemon

# 4. When ready, update all remaining
python3 scripts/interactive_summary_updater.py --resource pokemon --update-all

# 5. Upload to production
python3 scripts/upload_pokemon_summaries.py \
  --resource pokemon \
  --host localhost \
  --port 5433 \
  --database pokeapi \
  --user pokeapi \
  --password "your_password"
```

### Working with Different Resource Types

```bash
# Update all pokemon summaries
python3 scripts/interactive_summary_updater.py --resource pokemon --update-all

# Review ability summaries interactively
python3 scripts/interactive_summary_updater.py --resource ability

# Update move summaries starting from "thunderbolt"
python3 scripts/interactive_summary_updater.py --resource move --start-from "thunderbolt"
```

This tool provides a much more efficient and controlled way to improve existing summaries compared to the previous batch processing approach.
