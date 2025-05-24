import os
import httpx
import requests
import asyncio
from typing import Dict, Any, List, Union, Optional
from datetime import datetime

from markdownify import markdownify
from langsmith import traceable
from tavily import TavilyClient
from duckduckgo_search import DDGS

from langchain_community.utilities import SearxSearchWrapper

def get_config_value(value: Any) -> str:
    """
    Convert configuration values to string format, handling both string and enum types.
    
    Args:
        value (Any): The configuration value to process. Can be a string or an Enum.
    
    Returns:
        str: The string representation of the value.
        
    Examples:
        >>> get_config_value("tavily")
        'tavily'
        >>> get_config_value(SearchAPI.TAVILY)
        'tavily'
    """
    return value if isinstance(value, str) else value.value

def strip_thinking_tokens(text: str) -> str:
    """
    Remove <think> and </think> tags and their content from the text.
    
    Iteratively removes all occurrences of content enclosed in thinking tokens.
    
    Args:
        text (str): The text to process
        
    Returns:
        str: The text with thinking tokens and their content removed
    """
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text

def deduplicate_and_format_sources(
    search_response: Union[Dict[str, Any], List[Dict[str, Any]]], 
    max_tokens_per_source: int, 
    fetch_full_page: bool = False
) -> str:
    """
    Format and deduplicate search responses from various search APIs.
    
    Takes either a single search response or list of responses from search APIs,
    deduplicates them by URL, and formats them into a structured string.
    
    Args:
        search_response (Union[Dict[str, Any], List[Dict[str, Any]]]): Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results
        max_tokens_per_source (int): Maximum number of tokens to include for each source's content
        fetch_full_page (bool, optional): Whether to include the full page content. Defaults to False.
            
    Returns:
        str: Formatted string with deduplicated sources
        
    Raises:
        ValueError: If input is neither a dict with 'results' key nor a list of search results
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response['results']
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and 'results' in response:
                sources_list.extend(response['results'])
            else:
                sources_list.extend(response)
    else:
        raise ValueError("Input must be either a dict with 'results' or a list of search results")
    
    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source['url'] not in unique_sources:
            unique_sources[source['url']] = source
    
    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source: {source['title']}\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['content']}\n===\n"
        if fetch_full_page:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get('raw_content', '')
            if raw_content is None:
                raw_content = ''
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
                
    return formatted_text.strip()

def format_sources(search_results: Dict[str, Any]) -> str:
    """
    Format search results into a bullet-point list of sources with URLs.
    
    Creates a simple bulleted list of search results with title and URL for each source.
    
    Args:
        search_results (Dict[str, Any]): Search response containing a 'results' key with
                                        a list of search result objects
        
    Returns:
        str: Formatted string with sources as bullet points in the format "* title : url"
    """
    return '\n'.join(
        f"* {source['title']} : {source['url']}"
        for source in search_results['results']
    )

async def fetch_raw_content(url: str) -> Optional[str]:
    """
    Asynchronously fetch HTML content from a URL and convert it to markdown format.
    
    Uses a 10-second timeout to avoid hanging on slow sites or large pages.
    
    Args:
        url (str): The URL to fetch content from
        
    Returns:
        Optional[str]: The fetched content converted to markdown if successful,
                      None if any error occurs during fetching or conversion
    """
    try:                
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return markdownify(response.text)
    except Exception as e:
        print(f"Warning: Failed to fetch full page content for {url}: {str(e)}")
        return None

@traceable
async def duckduckgo_search(query: str, max_results: int = 3, fetch_full_page: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search the web using DuckDuckGo and return formatted results.
    
    Uses the DDGS library to perform web searches through DuckDuckGo.
    
    Args:
        query (str): The search query to execute
        max_results (int, optional): Maximum number of results to return. Defaults to 3.
        fetch_full_page (bool, optional): Whether to fetch full page content from result URLs. 
                                         Defaults to False.
    Returns:
        Dict[str, List[Dict[str, Any]]]: Search response containing:
            - results (list): List of search result dictionaries, each containing:
                - title (str): Title of the search result
                - url (str): URL of the search result
                - content (str): Snippet/summary of the content
                - raw_content (str or None): Full page content if fetch_full_page is True,
                                            otherwise same as content
    """
    
    def _sync_ddg_search(query: str, max_results: int) -> List[Dict[str, Any]]:
        """Synchronous DuckDuckGo search to be run in a separate thread."""
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            print(f"Error in sync DuckDuckGo search: {str(e)}")
            return []
    
    try:
        # Run the synchronous DDGS search in a separate thread to avoid blocking
        search_results = await asyncio.to_thread(_sync_ddg_search, query, max_results)
        
        results = []
        # Prepare tasks for parallel content fetching
        content_tasks = []
        
        for r in search_results:
            url = r.get('href')
            title = r.get('title')
            content = r.get('body')
            
            if not all([url, title, content]):
                print(f"Warning: Incomplete result from DuckDuckGo: {r}")
                continue

            if fetch_full_page:
                content_tasks.append(fetch_raw_content(url))
            else:
                content_tasks.append(asyncio.create_task(asyncio.sleep(0, result=content)))
        
        # Fetch all content in parallel
        if content_tasks:
            raw_contents = await asyncio.gather(*content_tasks, return_exceptions=True)
        else:
            raw_contents = []
        
        # Combine results
        for i, r in enumerate(search_results):
            url = r.get('href')
            title = r.get('title')
            content = r.get('body')
            
            if not all([url, title, content]):
                continue
            
            raw_content = content
            if i < len(raw_contents) and not isinstance(raw_contents[i], Exception):
                raw_content = raw_contents[i] if raw_contents[i] is not None else content
            
            result = {
                "title": title,
                "url": url,
                "content": content,
                "raw_content": raw_content
            }
            results.append(result)
        
        return {"results": results}
    except Exception as e:
        print(f"Error in DuckDuckGo search: {str(e)}")
        print(f"Full error details: {type(e).__name__}")
        return {"results": []}

# Synchronous wrapper for backward compatibility
def duckduckgo_search_sync(query: str, max_results: int = 3, fetch_full_page: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    Synchronous wrapper for duckduckgo_search for backward compatibility.
    """
    return asyncio.run(duckduckgo_search(query, max_results, fetch_full_page))

def log_progress(step: str, details: str = ""):
    """
    Log research progress with timestamp for better user experience.
    
    Args:
        step (str): The current research step
        details (str): Additional details about the step
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔍 {step}")
    if details:
        print(f"    └─ {details}")

def assess_source_credibility(url: str, title: str, content: str) -> float:
    """
    Basic source credibility assessment.
    
    Args:
        url (str): Source URL
        title (str): Source title
        content (str): Source content
        
    Returns:
        float: Credibility score between 0.0 and 1.0
    """
    score = 0.5  # Base score
    
    # Domain-based scoring
    trusted_domains = ['wikipedia.org', 'edu', 'gov', 'nature.com', 'sciencedirect.com']
    if any(domain in url.lower() for domain in trusted_domains):
        score += 0.3
    
    # Content quality indicators
    if len(content) > 500:  # Substantial content
        score += 0.1
    if any(word in content.lower() for word in ['research', 'study', 'analysis']):
        score += 0.1
    
    return min(score, 1.0)

async def parallel_search(query: str, max_results: int = 3, fetch_full_page: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    Perform parallel web searches using multiple search engines for faster results.
    
    Args:
        query (str): The search query to execute
        max_results (int, optional): Maximum number of results per search engine. Defaults to 3.
        fetch_full_page (bool, optional): Whether to fetch full page content. Defaults to False.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Combined search results from all engines
    """
    log_progress("Starting parallel search", f"Query: {query}")
    
    # Create tasks for parallel execution
    tasks = []
    
    # Add DuckDuckGo search
    tasks.append(duckduckgo_search(query, max_results, fetch_full_page))
    
    # You can add more search engines here in the future
    # tasks.append(bing_search_async(query, max_results, fetch_full_page))
    # tasks.append(google_scholar_search_async(query, max_results, fetch_full_page))
    
    try:
        # Execute all searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results from all successful searches
        combined_results = []
        for result in results:
            if isinstance(result, dict) and 'results' in result:
                combined_results.extend(result['results'])
            elif isinstance(result, Exception):
                print(f"Search error: {str(result)}")
        
        log_progress("Parallel search completed", f"Found {len(combined_results)} total results")
        return {"results": combined_results}
        
    except Exception as e:
        print(f"Error in parallel search: {str(e)}")
        # Fallback to single search
        return await duckduckgo_search(query, max_results, fetch_full_page)

