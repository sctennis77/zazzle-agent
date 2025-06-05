# Zazzle Affiliate Marketing Agent

This project automates the process of scraping Zazzle bestseller pages, generating affiliate links, and creating tweet-sized descriptions using GPT-4.

## Features

- Scrapes Zazzle bestseller pages
- Generates affiliate links with your Zazzle affiliate ID
- Creates engaging tweet-sized descriptions using GPT-4
- Saves results to CSV files
- Comprehensive test suite with high coverage

## Prerequisites

- Python 3.8+
- Chrome browser (for web scraping)
- OpenAI API key
- Zazzle affiliate ID

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
ZAZZLE_AFFILIATE_ID=your_affiliate_id
SCRAPE_DELAY=2
MAX_PRODUCTS=100
```

## Development

This project uses a Makefile to simplify common development tasks. Here are the available commands:

- `make venv` — Create a Python virtual environment (if not already created)
- `make install` — Install dependencies into the virtual environment
- `make test` — Run the test suite with coverage
- `make run` — Run the app locally
- `make clean` — Remove the virtual environment, outputs, and coverage files
- `make docker-build` — Build the Docker image (only if tests pass)
- `make docker-run` — Run the Docker container, mounting the outputs directory

Example usage:
```sh
make venv
make install
make test
make run
# or for Docker
make docker-build
make docker-run
```

## Docker

Build and run the application using Docker:

```bash
docker build -t zazzle-affiliate-agent .
docker run -v $(pwd)/outputs:/app/outputs zazzle-affiliate-agent
```

## Testing

Run the test suite:

```bash
python -m pytest tests/ --cov=app
```

## License

MIT 