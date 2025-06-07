# Zazzle Dynamic Product Generator

This project automates the process of dynamically generating products on Zazzle based on Reddit interactions. Instead of generating marketing content and affiliate links for existing products, the system uses the Zazzle Create a Product API to create new products in real-time.

## Features

- **Dynamic Product Generation**: The Reddit agent interacts with subreddits (posts and comments) and other users to identify opportunities for product creation.
- **Zazzle API Integration**: Utilizes the Zazzle Create a Product API to generate products on-the-fly.
- **Intelligent Decision Making**: The agent analyzes conversations and trends to determine when to create a product, ensuring relevance and potential success.
- **Automated Workflow**: Streamlined process from Reddit interaction to product creation and listing on Zazzle.

## Prerequisites

- Python 3.8+
- Zazzle API credentials
- Reddit API credentials
- OpenAI API key (for content generation and decision-making)

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
ZAZZLE_API_KEY=your_zazzle_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
OPENAI_API_KEY=your_openai_api_key
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

### Command Line Options

The application supports different modes of operation through command-line arguments:

```bash
# Run the full end-to-end pipeline
python main.py --mode pipeline

# Test Reddit agent's voting behavior on posts (without posting affiliate material)
python main.py --mode test-voting

# Test Reddit agent's voting behavior on comments (prints comment, link, and action for manual verification)
python main.py --mode test-voting-comment

# Run with custom configuration
python main.py --mode pipeline --config path/to/config.json
```

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
docker build -t zazzle-dynamic-product-generator .
docker run -v $(pwd)/outputs:/app/outputs zazzle-dynamic-product-generator
```

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tests/ --cov=app

# Run specific test files
python -m pytest tests/test_reddit_agent.py
python -m pytest tests/test_product_designer.py
python -m pytest tests/test_integration.py
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test the complete pipeline
- **Reddit Agent Tests**: Test voting behavior and interaction patterns

## License

MIT 

## Zazzle Product Designer Agent

The Zazzle Product Designer Agent is responsible for generating custom products on Zazzle based on instructions received from the Reddit agent. This agent utilizes the Zazzle Create-a-Product API to design and create products dynamically.

### Initial Focus: Custom Golf Balls

The initial focus of the Product Designer Agent is on creating custom golf balls. The agent will:

- Receive design instructions from the Reddit agent.
- Use the Zazzle Create-a-Product API to generate custom golf ball designs.
- Ensure that the designs are relevant and appealing to potential customers.

### Integration with Reddit Agent

The Product Designer Agent works in conjunction with the Reddit agent to:

- Analyze Reddit interactions to identify opportunities for product creation.
- Generate product designs based on the context and relevance of the conversation.
- Create and list the products on Zazzle for potential sales.

### Future Enhancements

In the future, the Product Designer Agent can be expanded to include other product types and design options, allowing for a broader range of custom products to be generated based on Reddit interactions.

## Reddit Agent Voting

The Reddit agent can upvote and downvote both posts and comments. The `test-voting` and `test-voting-comment` modes allow you to verify this behavior:

- `test-voting`: Upvotes and downvotes a trending post in r/golf.
- `test-voting-comment`: Upvotes and downvotes a comment in a trending post, printing the comment text, author, link, and action taken for manual verification. 