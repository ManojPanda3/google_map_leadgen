# Google Maps Lead Generator

A high-performance Python library for extracting business leads from Google Maps using a stealth browser (Camoufox).

## Features

- **Two-phase scraping architecture** - Efficiently collects URLs first, then extracts data
- **Parallel processing** - Uses multiple browser tabs concurrently
- **Resource optimization** - Blocks heavy resources (images, media, fonts) during data extraction
- **Stealth browsing** - Uses Camoufox to avoid detection
- **Flexible output** - Save results to CSV or JSON

## Installation

```bash
pip install google-map-leadgen
```

Or install from source:

```bash
pip install -e .
```

## Usage

### Command Line

```bash
# Basic usage
python -m google_map_leadgen.main "Restaurants in San Francisco"

# Specify number of leads and tabs
python -m google_map_leadgen.main "Plumbers in NYC" --leads 50 --tabs 4

# Output as JSON
python -m google_map_leadgen.main "Coffee shops" --json
```

### As a Library

```python
import asyncio
from google_map_leadgen import scrape

async def main():
    # You can specify target leads and concurrent tabs
    results = await scrape("Mobile Repair Shop in New York", target=10, max_tabs=3)
    
    for lead in results:
        print(f"Name: {lead['name']}")
        print(f"Address: {lead['address']}")
        print(f"Phone: {lead['phone']}")
        print(f"Website: {lead['website']}")
        print("---")

asyncio.run(main())
```

### Configuration

Set environment variables to customize behavior:

```bash
export LEADS=50              # Number of leads to collect
export MAX_TAB_ALLOWED=4     # Concurrent browser tabs
export HEADLESS=true         # Run browser in headless mode
export DEBUG=false           # Enable debug logging
```

## Output Format

Results are returned as a list of dictionaries:

```python
[
    {
        "name": "Business Name",
        "address": "123 Main St, City, State",
        "phone": "+1 (555) 123-4567",
        "website": "https://example.com"
    },
    ...
]
```

## Project Structure

```
google-map-leadgen/
├── .github/             # GitHub Actions workflows (CI/CD)
├── google_map_leadgen/  # Core package source
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Configuration settings
│   ├── main.py          # CLI entry point
│   └── scraper.py       # Core scraping logic
├── tests/               # Unit and integration tests
├── pyproject.toml       # Package configuration and dependencies
└── README.md            # Project documentation
```

## Development

### Prerequisites

- [uv](https://github.com/astral-sh/setup-uv) (Recommended) or Python 3.12+

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/google-map-leadgen.git
cd google-map-leadgen

# Install dependencies
uv sync --all-extras
```

### Running Tests

```bash
uv run pytest tests/ -v
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## CI/CD

This project uses GitHub Actions for:

- **CI**: Automated testing and linting on every push and pull request.
- **CD**: Automated publishing to PyPI on GitHub release.

## Requirements

- Python 3.12+
- Camoufox (stealth browser)

## License

MIT License

## Disclaimer

This tool is for educational purposes. Scraping Google Maps may violate their Terms of Service. Use responsibly and at your own risk.
