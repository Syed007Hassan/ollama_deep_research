# Ollama Deep Research

![image](https://github.com/user-attachments/assets/49d0e7cb-e547-4e85-bee1-481f2c18db9b)


Ollama Deep Research is a fully local web research assistant powered by any LLM hosted on [Ollama](https://ollama.com/search). 

Simply provide a research topic, and the assistant will intelligently generate web search queries, gather relevant results, and create comprehensive summaries. It then analyzes these summaries to identify knowledge gaps, generates follow-up queries to fill those gaps, and repeats this iterative process for a configurable number of research cycles.

The final output is a well-structured markdown report with cited sources from all research conducted.

## 🚀 Quickstart (after creating a environemnt)

Clone the repository then do a cd:
```shell
cd ollama-deep-research
```

Then edit the `.env` file to customize the environment variables according to your needs. These environment variables control the model selection, search tools, and other configuration settings. When you run the application, these values will be automatically loaded via `python-dotenv` (because `langgraph.json` point to the "env" file).
```shell
cp .env.example .env
```

### Selecting local model with Ollama

1. Download the Ollama app for Mac [here](https://ollama.com/download).

2. Pull a local LLM from [Ollama](https://ollama.com/search). As an [example](https://ollama.com/library/deepseek-r1:8b):
```shell
ollama pull qwen3:14b
```

### Selecting search tool

By default, it will use [DuckDuckGo](https://duckduckgo.com/) for web search, cause it  does not require an API key. 

Optionally, update the `.env` file with the following search tool configuration and API keys. 

If set, these values will take precedence over the defaults set in the `Configuration` class in `configuration.py`. 
```shell
SEARCH_API=xxx # the search API to use, such as `duckduckgo` (default)
MAX_WEB_RESEARCH_LOOPS=xxx # the maximum number of research loop steps, defaults to `3`
FETCH_FULL_PAGE=xxx # fetch the full page content (with `duckduckgo`), defaults to `false`
```

### Running with LangGraph Studio

#### Mac

1. (Recommended) Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Launch LangGraph server:

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev
```

#### Windows

1. (Recommended) Create a virtual environment: 

* Install `Python 3.11` (and add to PATH during installation). 
* Restart your terminal to ensure Python is available, then create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

```powershell
ollama serve
```


2. Launch LangGraph server:

```powershell
# Install dependencies
pip install -e .
pip install -U "langgraph-cli[inmem]"            

# Start the LangGraph server
langgraph dev
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




