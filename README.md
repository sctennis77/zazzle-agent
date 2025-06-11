# Zazzle Dynamic Product Generator

This project automates the process of dynamically generating products on Zazzle based on Reddit interactions. The system uses the Zazzle Create a Product API to create new products in real-time, focusing on custom stickers as the initial product type.

## System Components

### 1. Pipeline
- Orchestrates the complete product generation process
- Manages concurrent operations and error handling
- Implements retry logic with exponential backoff
- Coordinates between all system components
- Provides a unified interface for end-to-end product generation

### 2. Reddit Agent
- Monitors and interacts with r/golf subreddit
- Uses LLM to analyze posts and comments for product opportunities
- Generates engaging and marketing-focused comments
- Makes voting decisions based on content relevance
- Operates in test mode for safe development

### 3. Product Designer
- Receives design instructions from Reddit Agent
- Uses DTOs (Data Transfer Objects) for product configuration
- Integrates with Zazzle Create-a-Product API
- Manages product creation and listing
- Handles URL encoding for product parameters

### 4. Integration Layer
- Coordinates between Reddit Agent and Product Designer
- Manages API authentication and rate limiting
- Handles error recovery and retry logic
- Maintains system state and logging

## Workflow Diagram

```mermaid
graph TD
    subgraph "Pipeline Orchestration"
        PL[Pipeline] --> |orchestrates| RA[RedditAgent]
        PL --> |manages| IG[ImageGenerator]
        PL --> |coordinates| ZPD[ZazzleProductDesigner]
        PL --> |handles| AL[AffiliateLinker]
    end

    subgraph "Content Discovery"
        RC[RedditContext] --> |post_id, title, content| PI[ProductIdea]
        RC --> |subreddit, comments| RA
    end

    subgraph "Product Generation"
        PI --> |theme, image_description| IG
        IG --> |imgur_url, local_path| DI[DesignInstructions]
        DI --> |image, theme, text| ZPD
        ZPD --> |product_id, name, urls| PF[ProductInfo]
    end

    subgraph "Distribution"
        PF --> |product_url, affiliate_link| DM[DistributionMetadata]
        DM --> |channel, status| DC[DistributionChannel]
        DC --> |published_at, channel_url| DS[DistributionStatus]
    end

    subgraph "Configuration"
        PC[PipelineConfig] --> |model, template_id| IG
        PC --> |tracking_code| ZPD
        PC --> |settings| PL
    end

    subgraph "Data Flow"
        RC --> |serialize| JSON[JSON Storage]
        PF --> |to_csv| CSV[CSV Storage]
        DM --> |to_dict| DB[Database]
    end

    classDef model fill:#f9f,stroke:#333,stroke-width:2px
    classDef agent fill:#bbf,stroke:#333,stroke-width:2px
    classDef storage fill:#bfb,stroke:#333,stroke-width:2px
    classDef config fill:#fbb,stroke:#333,stroke-width:2px
    classDef pipeline fill:#fbf,stroke:#333,stroke-width:2px

    class RC,PI,PF,DM model
    class RA,ZPD,IG,DC agent
    class JSON,CSV,DB storage
    class PC config
    class PL pipeline
```

## Component Details

### Pipeline Orchestration
- **Pipeline**: Central orchestrator for the product generation process:
  - Manages the complete product generation workflow
  - Handles concurrent operations and error recovery
  - Implements retry logic with exponential backoff
  - Coordinates between all system components
  - Provides a unified interface for end-to-end product generation
  - Supports both single and batch product generation
  - Maintains comprehensive logging and error tracking

### Content Discovery
- **RedditContext**: Captures all relevant information from a Reddit post, including:
  - Post ID, title, and content
  - Subreddit information
  - Comments and engagement metrics
  - URL and metadata
- **ProductIdea**: Represents the initial concept for a product, containing:
  - Theme and image description
  - Design instructions
  - Source Reddit context
  - Model and prompt version information

### Product Generation
- **ImageGenerator**: Creates product images using DALL-E models:
  - Accepts theme and image descriptions
  - Generates images using specified DALL-E model
  - Stores images locally and on Imgur
  - Returns image URLs and local paths
- **DesignInstructions**: Contains all parameters needed for product creation:
  - Image URL and theme
  - Text and color specifications
  - Product type and quantity
  - Template and model information
- **ZazzleProductDesigner**: Creates products on Zazzle:
  - Uses design instructions to configure products
  - Integrates with Zazzle's Create-a-Product API
  - Generates affiliate links
  - Returns complete product information

### Distribution
- **DistributionMetadata**: Tracks content distribution:
  - Channel-specific information
  - Publication status and timestamps
  - Error handling and recovery
  - URL and ID tracking
- **DistributionChannel**: Manages content publishing:
  - Handles different distribution platforms
  - Manages rate limiting and quotas
  - Tracks engagement metrics
  - Handles error recovery
- **DistributionStatus**: Monitors distribution state:
  - Tracks pending, published, and failed states
  - Manages retry logic
  - Records timestamps and metadata

### Configuration
- **PipelineConfig**: Central configuration management:
  - AI model selection (DALL-E 2/3)
  - Zazzle template and tracking settings
  - Prompt versioning
  - System-wide parameters

### Data Flow
- **JSON Storage**: Stores Reddit context and metadata
- **CSV Storage**: Records product information and metrics
- **Database**: Maintains distribution status and history

## Data Model Relationships

1. **Content to Product Flow**:
   ```
   RedditContext → ProductIdea → DesignInstructions → ProductInfo
   ```
   - Each step enriches the data with additional information
   - Maintains traceability back to source content
   - Preserves metadata throughout the pipeline

2. **Product to Distribution Flow**:
   ```
   ProductInfo → DistributionMetadata → DistributionStatus
   ```
   - Tracks product lifecycle
   - Manages distribution state
   - Records engagement metrics

3. **Configuration Flow**:
   ```
   PipelineConfig → (ImageGenerator, ZazzleProductDesigner)
   ```
   - Centralizes configuration
   - Ensures consistency across components
   - Manages versioning and updates

## Error Handling and Recovery

The system implements comprehensive error handling at each stage:

1. **Pipeline Orchestration**:
   - Manages concurrent operations safely
   - Implements retry logic with exponential backoff
   - Handles component failures gracefully
   - Maintains system state during errors

2. **Content Discovery**:
   - Validates Reddit API responses
   - Handles rate limiting
   - Manages API timeouts

3. **Product Generation**:
   - Retries failed image generation
   - Validates design instructions
   - Handles Zazzle API errors

4. **Distribution**:
   - Tracks failed distributions
   - Implements retry logic
   - Maintains error logs

## Monitoring and Logging

Each component includes detailed logging:
- Operation status and timing
- Error conditions and recovery
- Performance metrics
- Data flow tracking

## Features

- **Pipeline Orchestration**: Centralized management of the product generation process
- **Reddit Integration**: Automated monitoring and interaction with r/golf
- **LLM-Powered Analysis**: Dynamic product idea generation using OpenAI GPT
- **Product Generation**: Dynamic sticker design creation with configurable image generation models (DALL-E 2 and DALL-E 3)
- **Marketing Automation**: Context-aware comment generation
- **Test Mode**: Safe development environment with dry-run capabilities
- **Comprehensive Testing**: Unit, integration, and end-to-end test coverage with dedicated test output directory
- **DTO-Based Configuration**: Type-safe product configuration using Python DTOs

## Prerequisites

- Python 3.8+
- Zazzle API credentials
- Reddit API credentials
- OpenAI API key

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id
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
make run-full  # Run the complete end-to-end pipeline
make clean     # Clean up development artifacts
```

### Example Commands

Run the full pipeline with DALL-E 2 (default):
```bash
make run
```

Run the full pipeline with DALL-E 3:
```bash
make run MODEL=dall-e-3
```

Generate an image with a custom prompt using DALL-E 2 (default):
```bash
make run-generate-image IMAGE_PROMPT="A cat playing chess" MODEL=dall-e-2
```

Generate an image with a custom prompt using DALL-E 3:
```bash
make run-generate-image IMAGE_PROMPT="A cat playing chess" MODEL=dall-e-3
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

## CSV Output

The system saves product information to a CSV file (`processed_products.csv`) with the following columns:

- theme
- text
- color
- quantity
- post_title
- post_url
- product_url
- image_url
- model
- prompt_version
- product_type
- zazzle_template_id
- zazzle_tracking_code
- design_instructions

The CSV output is designed to handle extra fields gracefully, ensuring that only the required fields are written to the file.

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
make test

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
- **Product Designer Tests**: URL encoding and parameter handling
- **Image Generation Tests**: Tests for both DALL-E 2 and DALL-E 3 models

### Test Output Directory

Test outputs, including generated images and product data, are stored in a dedicated `test_output` directory. This ensures that test artifacts are properly isolated and managed.

## License

MIT 

## Zazzle Product Designer Agent

The Zazzle Product Designer Agent is responsible for generating custom products on Zazzle based on instructions received from the Reddit agent. This agent utilizes the Zazzle Create-a-Product API to design and create products dynamically.

### Initial Focus: Custom Stickers

The initial focus of the Product Designer Agent is on creating custom stickers. The agent will:

- Receive design instructions from the Reddit agent
- Use the Zazzle Create-a-Product API to generate custom sticker designs
- Ensure proper URL encoding of product parameters
- Handle dynamic text and color customization

### Integration with Reddit Agent

The Product Designer Agent works in conjunction with the Reddit agent to:

- Process LLM-generated product ideas
- Generate product designs based on the context and relevance of the conversation
- Create and list the products on Zazzle for potential sales

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