import json
import asyncio

from typing_extensions import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph import START, END, StateGraph

from ollama_deep_researcher.configuration import Configuration, SearchAPI
from ollama_deep_researcher.utils import (
    deduplicate_and_format_sources, format_sources, duckduckgo_search_sync, 
    strip_thinking_tokens, get_config_value, log_progress, parallel_search
)
from ollama_deep_researcher.state import SummaryState, SummaryStateInput, SummaryStateOutput
from ollama_deep_researcher.prompts import query_writer_instructions, summarizer_instructions, reflection_instructions, get_current_date

# Nodes

def generate_query(state: SummaryState, config: RunnableConfig):
    """LangGraph node that generates a search query based on the research topic.
    
    Uses an LLM to create an optimized search query for web research based on
    the user's research topic. Defaults to Ollama as LLM provider.
    
    Args:
        state: Current graph state containing the research topic
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state update, including search_query key containing the generated query
    """

    log_progress("Generating initial search query", f"Topic: {state.research_topic}")

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=state.research_topic
    )

    # Generate a query
    configurable = Configuration.from_runnable_config(config)

    # Default to Ollama
    llm_json_mode = ChatOllama(
        base_url=configurable.ollama_base_url,
        model=configurable.local_llm,
        temperature=0,
        format="json"
    )

    result = llm_json_mode.invoke(
        [SystemMessage(content=formatted_prompt),
         HumanMessage(content=f"Generate a query for web search:")]
    )

    # Get the content
    content = result.content

    # Parse the JSON response and get the query
    search_query = None
    try:
        query = json.loads(content)
        search_query = query.get('query')
        if search_query:
            log_progress("Query generated successfully", f"Search query: {search_query}")
        else:
            raise KeyError("No query key found")
    except (json.JSONDecodeError, KeyError) as e:
        # If parsing fails, try to extract a reasonable search query
        if configurable.strip_thinking_tokens:
            content = strip_thinking_tokens(content)
        
        # If content is still empty or just braces, create a fallback query
        if not content or content.strip() in ['{}', '[]', '']:
            search_query = f"{state.research_topic}"
            log_progress("Using topic as search query", f"Search query: {search_query}")
        else:
            # Try to find a quote-enclosed string or use the cleaned content
            import re
            quoted_match = re.search(r'"([^"]+)"', content)
            if quoted_match:
                search_query = quoted_match.group(1)
                log_progress("Extracted query from quotes", f"Search query: {search_query}")
            else:
                search_query = content.strip()
                log_progress("Using cleaned content as query", f"Search query: {search_query}")
    
    # Final fallback if search_query is still empty or invalid
    if not search_query or search_query.strip() in ['{}', '[]', '']:
        search_query = f"{state.research_topic}"
        log_progress("Final fallback to topic", f"Search query: {search_query}")
    
    return {"search_query": search_query}


async def web_research(state: SummaryState, config: RunnableConfig):
    """LangGraph node that performs web research using the generated search query.
    
    Executes a web search using the configured search API and formats the results 
    for further processing. Now supports parallel search for improved performance.
    
    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings
        
    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    
    # Configure
    configurable = Configuration.from_runnable_config(config)
    
    log_progress(f"Research Loop {state.research_loop_count + 1}", f"Searching for: {state.search_query}")
    
    # Get the search API
    search_api = get_config_value(configurable.search_api)
    max_sources = configurable.max_sources_per_loop

    # Search the web with parallel processing when possible
    if search_api == "duckduckgo":
        # Use parallel search for better performance
        search_results = await parallel_search(
            state.search_query, 
            max_results=max_sources, 
            fetch_full_page=configurable.fetch_full_page
        )
        search_str = deduplicate_and_format_sources(
            search_results, 
            max_tokens_per_source=1000, 
            fetch_full_page=configurable.fetch_full_page
        )
    else:
        # Fallback to original synchronous search for other APIs
        if search_api == "tavily":
            search_results = tavily_search(
                state.search_query, fetch_full_page=configurable.fetch_full_page, max_results=1)
            search_str = deduplicate_and_format_sources(
                search_results, max_tokens_per_source=1000, fetch_full_page=configurable.fetch_full_page)
        elif search_api == "perplexity":
            search_results = perplexity_search(
                state.search_query, state.research_loop_count)
            search_str = deduplicate_and_format_sources(
                search_results, max_tokens_per_source=1000, fetch_full_page=configurable.fetch_full_page)
        elif search_api == "searxng":
            search_results = searxng_search(
                state.search_query, max_results=max_sources, fetch_full_page=configurable.fetch_full_page)
            search_str = deduplicate_and_format_sources(
                search_results, max_tokens_per_source=1000, fetch_full_page=configurable.fetch_full_page)
        else:
            raise ValueError(f"Unsupported search API: {configurable.search_api}")

    # Apply source credibility scoring if enabled
    if configurable.enable_source_verification:
        from ollama_deep_researcher.utils import assess_source_credibility
        log_progress("Assessing source credibility", "Scoring sources for reliability")
        
        for result in search_results.get('results', []):
            credibility_score = assess_source_credibility(
                result.get('url', ''), 
                result.get('title', ''), 
                result.get('content', '')
            )
            result['credibility_score'] = credibility_score
        
        # Sort by credibility score (highest first)
        search_results['results'] = sorted(
            search_results.get('results', []), 
            key=lambda x: x.get('credibility_score', 0.5), 
            reverse=True
        )

    log_progress("Search completed", f"Found {len(search_results.get('results', []))} sources")
    
    return {
        "sources_gathered": [format_sources(search_results)], 
        "research_loop_count": state.research_loop_count + 1, 
        "web_research_results": [search_str]
    }


def summarize_sources(state: SummaryState, config: RunnableConfig):
    """LangGraph node that summarizes web research results.
    
    Uses an LLM to create or update a running summary based on the newest web research 
    results, integrating them with any existing summary.
    
    Args:
        state: Current graph state containing research topic, running summary,
              and web research results
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state update, including running_summary key containing the updated summary
    """

    log_progress("Summarizing research results", "Analyzing and integrating new information")

    # Existing summary
    existing_summary = state.running_summary

    # Most recent web research
    most_recent_web_research = state.web_research_results[-1]

    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
            f"<New Context> \n {most_recent_web_research} \n <New Context>"
            f"Update the Existing Summary with the New Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
        )
        log_progress("Updating existing summary", "Integrating new findings with previous research")
    else:
        human_message_content = (
            f"<Context> \n {most_recent_web_research} \n <Context>"
            f"Create a Summary using the Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
        )
        log_progress("Creating initial summary", "Building first research summary")

    # Run the LLM
    configurable = Configuration.from_runnable_config(config)

    # Default to Ollama
    llm = ChatOllama(
        base_url=configurable.ollama_base_url,
        model=configurable.local_llm,
        temperature=0
    )

    result = llm.invoke(
        [SystemMessage(content=summarizer_instructions),
         HumanMessage(content=human_message_content)]
    )

    # Strip thinking tokens if configured
    running_summary = result.content
    if configurable.strip_thinking_tokens:
        running_summary = strip_thinking_tokens(running_summary)

    log_progress("Summary completed", f"Summary length: {len(running_summary)} characters")
    return {"running_summary": running_summary}


def reflect_on_summary(state: SummaryState, config: RunnableConfig):
    """LangGraph node that identifies knowledge gaps and generates follow-up queries.
    
    Analyzes the current summary to identify areas for further research and generates
    a new search query to address those gaps. Uses structured output to extract
    the follow-up query in JSON format.
    
    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """

    log_progress("Reflecting on current knowledge", "Identifying research gaps")

    # Generate a query
    configurable = Configuration.from_runnable_config(config)

    # Default to Ollama
    llm_json_mode = ChatOllama(
        base_url=configurable.ollama_base_url,
        model=configurable.local_llm,
        temperature=0,
        format="json"
    )

    result = llm_json_mode.invoke(
        [SystemMessage(content=reflection_instructions.format(research_topic=state.research_topic)),
         HumanMessage(content=f"Reflect on our existing knowledge: \n === \n {state.running_summary}, \n === \n And now identify a knowledge gap and generate a follow-up web search query:")]
    )

    # Strip thinking tokens if configured
    query = None
    try:
        # Try to parse as JSON first
        reflection_content = json.loads(result.content)
        # Get the follow-up query
        query = reflection_content.get('follow_up_query')
        if query:
            log_progress("Generated follow-up query", f"Query: {query}")
        else:
            raise KeyError("No follow_up_query key found")
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        # If parsing fails, extract useful content or use fallback
        content = result.content
        if configurable.strip_thinking_tokens:
            content = strip_thinking_tokens(content)
        
        # Try to extract a meaningful query from the content
        if content and content.strip() not in ['{}', '[]', '']:
            import re
            # Look for questions or quoted strings
            question_match = re.search(r'[?]\s*([^?\n]+)', content)
            quoted_match = re.search(r'"([^"]+)"', content)
            
            if question_match:
                query = question_match.group(1).strip()
                log_progress("Extracted question from content", f"Query: {query}")
            elif quoted_match:
                query = quoted_match.group(1)
                log_progress("Extracted quoted content", f"Query: {query}")
            else:
                # Use a more specific fallback
                query = f"{state.research_topic} detailed analysis"
                log_progress("Using enhanced topic fallback", f"Query: {query}")
        else:
            query = f"{state.research_topic} detailed analysis"
            log_progress("Using topic fallback", f"Query: {query}")
    
    # Final fallback check
    if not query or query.strip() in ['{}', '[]', '']:
        query = f"{state.research_topic} detailed analysis"
        log_progress("Final fallback for reflection", f"Query: {query}")
    
    return {"search_query": query}


def finalize_summary(state: SummaryState):
    """LangGraph node that finalizes the research summary.
    
    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations.
    
    Args:
        state: Current graph state containing the running summary and sources gathered
        
    Returns:
        Dictionary with state update, including running_summary key containing the formatted final summary with sources
    """

    log_progress("Finalizing research report", "Compiling sources and formatting output")

    # Deduplicate sources before joining
    seen_sources = set()
    unique_sources = []

    for source in state.sources_gathered:
        # Split the source into lines and process each individually
        for line in source.split('\n'):
            # Only process non-empty lines
            if line.strip() and line not in seen_sources:
                seen_sources.add(line)
                unique_sources.append(line)

    # Join the deduplicated sources
    all_sources = "\n".join(unique_sources)
    state.running_summary = f"## Summary\n{state.running_summary}\n\n ### Sources:\n{all_sources}"
    
    log_progress("Research completed", f"Final report ready with {len(unique_sources)} unique sources")
    return {"running_summary": state.running_summary}


def route_research(state: SummaryState, config: RunnableConfig) -> Literal["finalize_summary", "web_research"]:
    """LangGraph routing function that determines the next step in the research flow.
    
    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.
    
    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_web_research_loops setting
        
    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """

    configurable = Configuration.from_runnable_config(config)
    if state.research_loop_count <= configurable.max_web_research_loops:
        return "web_research"
    else:
        return "finalize_summary"


# Add nodes and edges
builder = StateGraph(SummaryState, input=SummaryStateInput,
                     output=SummaryStateOutput, config_schema=Configuration)
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("summarize_sources", summarize_sources)
builder.add_node("reflect_on_summary", reflect_on_summary)
builder.add_node("finalize_summary", finalize_summary)

# Add edges
builder.add_edge(START, "generate_query")
builder.add_edge("generate_query", "web_research")
builder.add_edge("web_research", "summarize_sources")
builder.add_edge("summarize_sources", "reflect_on_summary")
builder.add_conditional_edges("reflect_on_summary", route_research)
builder.add_edge("finalize_summary", END)

graph = builder.compile()
