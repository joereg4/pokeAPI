# Memory Management in Batch Processing

When generating summaries for multiple resources (Pokémon, Moves, Abilities, etc.) using OpenAI's API, memory usage can become an issue. This can lead to "Internal Server Error" messages when the system runs out of memory and kills the worker process (SIGKILL).

This document explains the memory management features implemented in the batch processing system.

## Memory Management Features

The batch processing system includes several features to help manage memory usage:

### 1. Batch Processing

Resources are processed in smaller batches rather than all at once. This helps limit memory usage by allowing garbage collection and memory cleanup between batches.

- **Batch Size**: Controls how many resources are processed before a longer delay and garbage collection
- **Default**: 10 items per batch
- **Recommendation**: 5-10 items for regular use, 3-5 for larger resources

### 2. Configurable Delays

Two types of delays help manage memory:

- **Delay Between Items**: A short pause between processing individual resources
  - Default: 1 second
  - Purpose: Allows small garbage collection and prevents API rate limiting

- **Delay Between Batches**: A longer pause after each batch
  - Default: 5 seconds
  - Purpose: Allows more thorough garbage collection and memory cleanup

### 3. Explicit Garbage Collection

After each batch is processed, the system:
- Forces Python's garbage collector to run with `gc.collect()`
- Logs how many objects were collected
- Waits for the specified delay to allow memory to be released back to the system

### 4. Memory Usage Monitoring

When enabled, the system will log:
- Initial memory usage at the start of processing
- Memory usage before and after each batch
- Memory difference (increase or decrease) after each batch
- Total memory change after all processing is complete

This is helpful for debugging memory issues and optimizing batch sizes and delays.

## How to Use Memory Management Features

1. Go to the Batch Refresh page for any resource type (e.g., `/admin/batch-refresh-summaries/pokemon`)
2. Select the resources you want to process
3. Configure the memory management options:
   - Set the batch size (recommended: 5-10)
   - Set delays between items and batches
   - Enable memory usage logging if needed
4. Click "Refresh Selected Summaries"

## Recommended Settings

### For Small Numbers of Resources (< 20)
- Batch Size: 10
- Delay Between Items: 1 second
- Delay Between Batches: 3 seconds

### For Medium Numbers of Resources (20-50)
- Batch Size: 5
- Delay Between Items: 1 second
- Delay Between Batches: 5 seconds

### For Large Numbers of Resources (> 50)
- Batch Size: 3
- Delay Between Items: 2 seconds
- Delay Between Batches: 10 seconds

### For Problematic Resources
- Batch Size: 1
- Delay Between Items: 0 seconds (not applicable for batch size 1)
- Delay Between Batches: 10-15 seconds

## Troubleshooting Memory Issues

If you're still experiencing memory issues:

1. **Reduce batch size**: Try processing just 1-3 resources at a time
2. **Increase delays**: Set longer delays between batches (10-30 seconds)
3. **Check logs**: Enable memory usage logging and check for patterns
4. **Server configuration**: Consider increasing server memory allocation
5. **Restart the server**: Memory fragmentation can sometimes be resolved by restarting

## Technical Details

The memory management system uses:
- Python's `gc` module for garbage collection
- `psutil` library for memory monitoring
- Batch processing with configurable parameters
- Memory usage logging to help identify issues

For advanced debugging, you can check the server logs which include detailed memory information when logging is enabled. 