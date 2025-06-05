# Zazzle Affiliate Marketing Agent

An automated system for scraping Zazzle bestsellers, generating affiliate links, and creating social media content.

## Features

- Scrapes Zazzle bestseller pages and category pages
- Extracts product titles and IDs
- Generates affiliate links with your Zazzle affiliate ID
- Creates tweet-sized product descriptions using GPT-4
- Exports data to CSV format
- Containerized for easy deployment

## Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- OpenAI API key
- Zazzle affiliate ID

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/zazzle-affiliate-agent.git
cd zazzle-affiliate-agent
```

2. Create a `.env` file from the example:
```bash
cp .env.example .env
```

3. Edit the `.env` file with your credentials:
```
OPENAI_API_KEY=your_openai_api_key_here
ZAZZLE_AFFILIATE_ID=your_affiliate_id_here
SCRAPE_DELAY=2
MAX_PRODUCTS=100
```

## Usage

### Running with Docker

1. Build the Docker image:
```bash
docker build -t zazzle-affiliate-agent .
```

2. Run the container:
```bash
docker run -v $(pwd)/outputs:/app/outputs zazzle-affiliate-agent
```

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the script:
```bash
python app/main.py
```

## Output

The script generates a CSV file in the `outputs` directory with the following columns:
- Product title
- Affiliate link
- Tweet text

Files are named with timestamps: `listings_YYYYMMDD_HHMMSS.csv`

## Configuration

You can adjust the following parameters in the `.env` file:
- `SCRAPE_DELAY`: Delay between requests (in seconds)
- `MAX_PRODUCTS`: Maximum number of products to scrape

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 