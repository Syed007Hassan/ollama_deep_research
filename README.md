# Ollama Deep Research

![image](https://github.com/user-attachments/assets/49d0e7cb-e547-4e85-bee1-481f2c18db9b)


Ollama Deep Research is a fully local web research assistant powered by any LLM hosted on [Ollama](https://ollama.com/search). 

Simply provide a research topic, and the assistant will intelligently generate web search queries, gather relevant results, and create comprehensive summaries. It then analyzes these summaries to identify knowledge gaps, generates follow-up queries to fill those gaps, and repeats this iterative process for a configurable number of research cycles.

The final output is a well-structured markdown report with cited sources from all research conducted.

## ✨ Features

- 🏠 **Fully Local**: No external API keys required - runs entirely on your machine with Ollama
- 🔄 **Iterative Research**: Automatically identifies knowledge gaps and conducts follow-up research loops
- 🔍 **Smart Query Generation**: LLM-powered search query optimization for better results
- 📊 **Source Verification**: Optional credibility scoring and assessment for research sources
- ⚙️ **Highly Configurable**: Adjust research depth, models, strategies, and output formats
- 📝 **Multiple Output Formats**: Support for Markdown, JSON, and HTML output
- 🎯 **Research Strategies**: Choose from broad overview, deep dive, or comparative analysis modes
- 🔗 **Proper Citations**: All findings include proper source citations with URLs
- ⚡ **Parallel Processing**: Asynchronous web searches for improved performance
- 🌐 **Extensible Search**: DuckDuckGo by default, with architecture for additional search APIs
- 🧠 **Context-Aware**: Maintains research context across multiple iterations
- 📈 **Progress Tracking**: Real-time logging of research steps and progress

## 🚀 Quickstart

### Option 1: Docker (Recommended for Easy Setup)

1. **Clone the project**:
```bash
git clone https://github.com/Syed007Hassan/ollama_deep_research.git
cd ollama_deep_research
```

2. **Copy environment configuration**:
```bash
cp .env.example .env
```

3. **Run with Docker Compose**:
```bash
# Start both Ollama and the research assistant
docker-compose up -d

# Pull the model you want to use (after Ollama is running)
docker exec ollama-server ollama pull deepseek-r1:14b

# Check logs
docker-compose logs -f
```

4. **Access the application**:
   - LangGraph Studio: http://localhost:2024
   - Ollama API: http://localhost:11434

### Option 2: Local Installation

1. **Install Poetry** (for dependency management):
```bash
pip install poetry
```

2. **Clone and setup the project**:
```shell
git clone https://github.com/Syed007Hassan/ollama_deep_research.git
cd ollama_deep_research

# Install dependencies with Poetry
poetry install

# Copy environment configuration
cp .env.example .env
```

**Note:** Poetry automatically creates and manages virtual environments, so you don't need to manually create one with `python -m venv`.

### Selecting local model with Ollama

1. Download the Ollama app for Mac [here](https://ollama.com/download).

2. Pull a local LLM from [Ollama](https://ollama.com/search). As an [example](https://ollama.com/library/deepseek-r1:8b):
```shell
ollama pull deepseek-r1:14b
```

### Selecting search tool

By default, it will use [DuckDuckGo](https://duckduckgo.com/) for web search, cause it  does not require an API key. 

## ⚙️ Configuration Options

You can configure the research assistant using environment variables in the `.env` file or through the LangGraph Studio UI. Below are all available configuration options:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_LLM` | `deepseek-r1:14b` | Name of the LLM model to use with Ollama |
| `LLM_PROVIDER` | `ollama` | LLM provider (currently only Ollama supported) |
| `OLLAMA_BASE_URL` | `http://localhost:11434/` | Base URL for Ollama API |

### Research Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_WEB_RESEARCH_LOOPS` | `3` | Number of research iterations to perform |
| `RESEARCH_STRATEGY` | `broad` | Research approach: `broad`, `deep`, or `comparative` |
| `MAX_SOURCES_PER_LOOP` | `3` | Maximum number of sources to gather per research loop |
| `ENABLE_SOURCE_VERIFICATION` | `false` | Enable basic source credibility checking |

### Search Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_API` | `duckduckgo` | Web search API to use (currently only DuckDuckGo) |
| `FETCH_FULL_PAGE` | `true` | Include full page content in search results |

### Output Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_FORMAT` | `markdown` | Format for final output: `markdown`, `json`, or `html` |
| `STRIP_THINKING_TOKENS` | `true` | Remove `<think>` tokens from model responses |

### Example .env Configuration

```shell
# Core LLM Settings
LOCAL_LLM=qwen3:14b
OLLAMA_BASE_URL=http://localhost:11434/

# Research Configuration  
MAX_WEB_RESEARCH_LOOPS=5
RESEARCH_STRATEGY=deep
MAX_SOURCES_PER_LOOP=5
ENABLE_SOURCE_VERIFICATION=true

# Search Settings
SEARCH_API=duckduckgo
FETCH_FULL_PAGE=true

# Output Settings
OUTPUT_FORMAT=markdown
STRIP_THINKING_TOKENS=true
```

### Configuration Priority

Keep in mind that configuration values are loaded in the following priority order:

```
1. Environment variables (highest priority)
2. LangGraph Studio UI configuration
3. Default values in the Configuration class (lowest priority)
```

### Running with LangGraph Studio

#### Mac

1. Start Ollama service:
```bash
ollama serve
```

2. Launch LangGraph server with Poetry:
```bash
# Method 1: Using uv with Poetry
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev

# Method 2: Direct Poetry command
poetry run langgraph dev
```

#### Windows

1. Start Ollama service:
```powershell
ollama serve
```

2. Launch LangGraph server with Poetry:
```powershell
# Install LangGraph CLI in Poetry environment
poetry add --group dev "langgraph-cli[inmem]"

# Start the LangGraph server
poetry run langgraph dev
```

### Using the LangGraph Studio UI

When you launch LangGraph server, you should see the following output and Studio will open in your browser:
> Ready!

> API: http://127.0.0.1:2024

> Docs: http://127.0.0.1:2024/docs

> LangGraph Studio Web UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

Open `LangGraph Studio Web UI` via the URL above. In the `configuration` tab, you can directly set various assistant configurations. Keep in mind that the priority order for configuration values is:

```
1. Environment variables (highest priority)
2. LangGraph UI configuration
3. Default values in the Configuration class (lowest priority)
```

![image](https://github.com/user-attachments/assets/00a02b65-1067-43e1-ae67-a1d7ceda7509)

## How it works

https://github.com/user-attachments/assets/ff494b16-74ce-4a09-85ec-f9428a94090a




