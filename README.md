# Zazzle Dynamic Product Generator

This project automates the process of dynamically generating products on Zazzle based on Reddit interactions. The system uses the Zazzle Create a Product API to create new products in real-time, focusing on custom golf balls as the initial product type.

## System Components

### 1. Reddit Agent
- Monitors and interacts with r/golf subreddit
- Analyzes posts and comments for product opportunities
- Generates engaging and marketing-focused comments
- Makes voting decisions based on content relevance
- Operates in test mode for safe development

### 2. Product Designer
- Receives design instructions from Reddit Agent
- Generates custom golf ball designs
- Integrates with Zazzle Create-a-Product API
- Manages product creation and listing

### 3. Integration Layer
- Coordinates between Reddit Agent and Product Designer
- Manages API authentication and rate limiting
- Handles error recovery and retry logic
- Maintains system state and logging

## Workflow Diagram

```mermaid
graph TD
    A[Reddit Agent] -->|Monitors| B[r/golf Subreddit]
    B -->|Identifies Opportunity| A
    A -->|Design Request| C[Product Designer]
    C -->|API Call| D[Zazzle API]
    D -->|Product Created| E[Zazzle Store]
    A -->|Marketing Comment| B
```

## Features

- **Reddit Integration**: Automated monitoring and interaction with r/golf
- **Product Generation**: Dynamic golf ball design creation
- **Marketing Automation**: Context-aware comment generation
- **Test Mode**: Safe development environment with dry-run capabilities
- **Comprehensive Testing**: Unit, integration, and end-to-end test coverage

## Prerequisites

- Python 3.8+
- Zazzle API credentials
- Reddit API credentials
- OpenAI API key

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

This project uses a Makefile to simplify common development tasks:

```bash
make venv      # Create Python virtual environment
make install   # Install dependencies
make test      # Run test suite
make run       # Run the app locally
make clean     # Clean up development artifacts
```

### Command Line Options

The application supports different modes of operation:

```bash
# Run the full end-to-end pipeline
python main.py full

# Test Reddit agent's voting behavior
python main.py test-voting
python main.py test-voting-comment

# Test comment generation
python main.py test-post-comment
python main.py test-engaging-comment
python main.py test-marketing-comment
python main.py test-marketing-comment-reply
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

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Complete pipeline testing
- **Reddit Agent Tests**: Voting and interaction pattern testing

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

## Reddit Agent Voting and Commenting

The Reddit agent can interact with posts and comments in several ways:

- **Voting**: Upvote and downvote both posts and comments
  - `test-voting`: Upvotes and downvotes a trending post in r/golf
  - `test-voting-comment`: Upvotes and downvotes a comment in a trending post, printing the comment text, author, link, and action taken for manual verification

- **Commenting**: Comment on posts (test mode only)
  - `test-post-comment`: Simulates commenting on a trending post, printing the proposed comment text, post details, and action for manual verification
  - In test mode, comments are not actually posted to Reddit, but the system shows what would be posted 

- **Marketing Commenting**: Reply to comments with marketing content (test mode only)
  - `test-marketing-comment-reply`: Simulates replying to a top-level comment in a trending post with a marketing message, printing the proposed reply text, product information, and action for manual verification. 