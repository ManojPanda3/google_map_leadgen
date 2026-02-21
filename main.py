"""Entry point for running the package as a CLI tool."""

import asyncio

from google_map_leadgen.main import main

if __name__ == "__main__":
    asyncio.run(main())
