# Deep Researcher

A flexible web research tool that extracts, analyzes, and summarizes information using web scraping and local Large Language Models.

## Features

- **Web Research**: Searches, extracts content, and summarizes information from multiple sources
- **Google Trends Analysis**: Extracts trending topics from Google Trends
- **Late Night Comedy Script Generation**: Creates comedy content based on trending topics
- **Local LLM Integration**: Uses Ollama for all text generation (no API keys required)
- **Anti-Detection Measures**: Implements browser techniques to avoid blocking

## Requirements

- Python 3.8+
- Chrome/Chromium browser
- Ollama (running locally with models like Mistral)

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/deep-researcher.git
cd deep-researcher
```

2. Create a virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Make sure Ollama is running with required models
```bash
# Install required models first
ollama pull mistral
ollama pull deepseek-r1

# Run Ollama server
ollama serve

# Or run the specific model directly
ollama run mistral
```

## Usage

### Research Mode

Research a specific topic and generate a comprehensive summary:

```bash
python main.py --mode research --query "open source LLMs"
```

### Comedy Mode

Generate a late-night comedy script based on current Google Trends:

```bash
python main.py --mode comedy
```

### Additional Options

- `--articles`: Number of articles to analyze per topic (default: 3)
- `--ollama-url`: Ollama API URL (default: http://localhost:11434)
- `--ollama-model`: Ollama model to use for basic tasks (default: mistral)
- `--reasoning-model`: Ollama model to use for advanced reasoning tasks (default: deepseek-r1)
- `--output-dir`: Directory to store output files (default: output)
- `--debug`: Enable debug mode with additional logging
- `--validate`: Enable content validation mode to verify extraction

## Output

All research results, screenshots, and generated content are saved to the output directory (configurable with `--output-dir`).

### Debug and Validation

For troubleshooting content extraction issues:

```bash
# Run with debug logging and content validation
python main.py --mode research --query "open source LLMs" --debug --validate
```

This will:
1. Enable verbose logging with detailed debug information
2. Save verification screenshots and extracted content for inspection
3. Create additional validation files to help diagnose extraction issues
4. Attempt alternative extraction methods when content appears to be missing

## Project Structure

```
deep-researcher/
├── main.py                  # Main entry point
├── researcher/              # Main package
│   ├── __init__.py          # Package initialization
│   ├── browser.py           # Browser handling
│   ├── config.py            # Configuration
│   ├── deep_researcher.py   # Main research functionality
│   ├── llm_client.py        # LLM interaction
│   └── utils.py             # Utility functions
├── logs/                    # Log files
└── output/                  # Research outputs
```

## License

GPL3

## Disclaimer

This tool is designed for educational and research purposes only. Be mindful of website terms of service when scraping content. The developers are not responsible for any misuse of this tool or violation of terms of service of any website.
