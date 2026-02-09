import asyncio
from SiteLivenessTracker import tracker

def main():
    asyncio.run(tracker.run_tracker())

if __name__ == "__main__":
    main()
