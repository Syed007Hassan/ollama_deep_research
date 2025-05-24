import os
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Optional, Literal

from langchain_core.runnables import RunnableConfig

class SearchAPI(Enum):
    DUCKDUCKGO = "duckduckgo"

class ResearchStrategy(Enum):
    BROAD_OVERVIEW = "broad"
    DEEP_DIVE = "deep"
    COMPARATIVE = "comparative"

class OutputFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"

class Configuration(BaseModel):
    """The configurable fields for the research assistant."""

    max_web_research_loops: int = Field(
        default=3,
        title="Research Depth",
        description="Number of research iterations to perform"
    )
    local_llm: str = Field(
        default="qwen3:14b",
        title="LLM Model Name",
        description="Name of the LLM model to use"
    )
    llm_provider: Literal["ollama"] = Field(
        default="ollama",
        title="LLM Provider",
        description="Provider for the LLM (Ollama)"
    )
    search_api: Literal["duckduckgo"] = Field(
        default="duckduckgo",
        title="Search API",
        description="Web search API to use"
    )
    fetch_full_page: bool = Field(
        default=True,
        title="Fetch Full Page",
        description="Include the full page content in the search results"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434/",
        title="Ollama Base URL",
        description="Base URL for Ollama API"
    )
    strip_thinking_tokens: bool = Field(
        default=True,
        title="Strip Thinking Tokens",
        description="Whether to strip <think> tokens from model responses"
    )
    research_strategy: Literal["broad", "deep", "comparative"] = Field(
        default="broad",
        title="Research Strategy",
        description="Strategy for conducting research: broad overview, deep dive, or comparative analysis"
    )
    output_format: Literal["markdown", "json", "html"] = Field(
        default="markdown",
        title="Output Format",
        description="Format for the final research output"
    )
    max_sources_per_loop: int = Field(
        default=3,
        title="Sources Per Loop",
        description="Maximum number of sources to gather per research loop"
    )
    enable_source_verification: bool = Field(
        default=False,
        title="Source Verification",
        description="Enable basic source credibility checking"
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        
        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }
        
        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}
        
        return cls(**values)