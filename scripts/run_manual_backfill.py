import asyncio
import logging
import sys

from backend.learning.backfill import BackfillEngine

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


async def run_backfill():
    print("Initializing BackfillEngine...")
    engine = BackfillEngine()
    print("Starting BackfillEngine.run()...")
    await engine.run()
    print("BackfillEngine.run() completed.")


if __name__ == "__main__":
    asyncio.run(run_backfill())
