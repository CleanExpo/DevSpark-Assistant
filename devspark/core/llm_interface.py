"""
Module for all interactions with Large Language Models (LLMs).

This module will handle:
- Formatting prompts.
- Sending requests to LLM APIs (e.g., Gemini, OpenAI).
- Parsing responses from LLMs.
- Error handling for API interactions.
- Caching responses to avoid redundant API calls.
"""

import os
import json
import time
import hashlib
import typer
from typing import Dict, Optional, Any, Tuple, Callable, List
from functools import wraps
try:
    import google.generativeai as genai
    from google.api_core.exceptions import GoogleAPIError, RetryError, ResourceExhausted, InvalidArgument
except ImportError:
    # This allows the module to be imported even if google-generativeai is not yet installed,
    # but functions using it will fail.
    genai = None
    GoogleAPIError = Exception
    RetryError = Exception
    ResourceExhausted = Exception
    InvalidArgument = Exception
    typer.secho("Warning: 'google-generativeai' package not found. LLM features will not work.", fg=typer.colors.YELLOW)

# OpenAI support
try:
    import openai
    from openai import OpenAI
    from openai.error import APIError, RateLimitError, InvalidRequestError
except ImportError:
    openai = None
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception
    InvalidRequestError = Exception

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# In-memory cache for LLM responses
_response_cache = {}

def with_cache(ttl_seconds: int = 3600):
    """
    Decorator to cache function responses based on arguments.
    
    Args:
        ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5("_".join(key_parts).encode()).hexdigest()
            
            # Check if response is in cache and not expired
            if cache_key in _response_cache:
                cache_time, cached_result = _response_cache[cache_key]
                if time.time() - cache_time < ttl_seconds:
                    return cached_result
            
            # Call the function if not in cache or expired
            result = func(*args, **kwargs)
            
            # Cache the result
            _response_cache[cache_key] = (time.time(), result)
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear the response cache."""
    global _response_cache
    _response_cache = {}

def with_retries(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to add retry logic to functions that make LLM API calls.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds (exponential backoff applied)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (GoogleAPIError, RetryError, ResourceExhausted) as e:
                    # Retryable Google API errors
                    last_error = e
                    retries += 1
                    if retries > max_retries:
                        break
                    # Exponential backoff
                    delay = base_delay * (2 ** (retries - 1))
                    time.sleep(delay)
                except (APIError, RateLimitError) as e:
                    # Retryable OpenAI errors
                    last_error = e
                    retries += 1
                    if retries > max_retries:
                        break
                    # Exponential backoff
                    delay = base_delay * (2 ** (retries - 1))
                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable errors
                    return {"error": f"LLM API call failed: {str(e)}", "error_type": type(e).__name__}
            
            # If we've exhausted retries
            return {
                "error": f"LLM API call failed after {max_retries} retries: {str(last_error)}",
                "error_type": type(last_error).__name__,
                "retried": retries
            }
        return wrapper
    return decorator

def get_llm_api_key(service_name: str = "GOOGLE") -> Optional[str]:
    """
    Retrieves the API key for the specified LLM service from environment variables.
    
    Args:
        service_name: The name of the LLM service ("GOOGLE" or "OPENAI")
        
    Returns:
        The API key if found, None otherwise
    """
    if service_name.upper() == "GOOGLE":
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            typer.secho("ERROR: GOOGLE_API_KEY not found in environment variables or .env file.", fg=typer.colors.RED)
            typer.echo("Please ensure your .env file is in the project root and contains your GOOGLE_API_KEY.")
        return key
    elif service_name.upper() == "OPENAI":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            typer.secho("ERROR: OPENAI_API_KEY not found in environment variables or .env file.", fg=typer.colors.RED)
            typer.echo("Please ensure your .env file is in the project root and contains your OPENAI_API_KEY.")
        return key
    else:
        typer.secho(f"ERROR: Unsupported LLM service: {service_name}", fg=typer.colors.RED)
        return None

def setup_llm(provider: str = "GOOGLE") -> Tuple[Any, Dict[str, Any]]:
    """
    Setup LLM client based on available API keys.
    
    Args:
        provider: The LLM provider to use ("GOOGLE" or "OPENAI")
        
    Returns:
        Tuple of (model object, error_dict)
        If successful, model is returned and error_dict is empty
        If failed, model is None and error_dict contains error information
    """
    if provider.upper() == "GOOGLE":
        if not genai:
            return None, {"error": "'google-generativeai' package is required for Google models", "error_type": "ModuleNotFoundError"}
        
        api_key = get_llm_api_key("GOOGLE")
        if not api_key:
            return None, {"error": "GOOGLE_API_KEY not found in environment variables", "error_type": "KeyError"}
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            return model, {}
        except Exception as e:
            return None, {"error": f"Failed to setup Google Gemini model: {str(e)}", "error_type": type(e).__name__}
            
    elif provider.upper() == "OPENAI":
        if not openai:
            return None, {"error": "'openai' package is required for OpenAI models", "error_type": "ModuleNotFoundError"}
        
        api_key = get_llm_api_key("OPENAI")
        if not api_key:
            return None, {"error": "OPENAI_API_KEY not found in environment variables", "error_type": "KeyError"}
        
        try:
            client = OpenAI(api_key=api_key)
            return client, {}
        except Exception as e:
            return None, {"error": f"Failed to setup OpenAI client: {str(e)}", "error_type": type(e).__name__}
    
    else:
        return None, {"error": f"Unsupported LLM provider: {provider}", "error_type": "ValueError"}

def extract_json_from_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response text.
    
    Args:
        response_text: The raw text response from the LLM
        
    Returns:
        Parsed JSON as dictionary
    
    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    text = response_text.strip()
    
    # Handle markdown code blocks
    if "```json" in text or "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.strip().startswith("json"):
                # Extract content after "json" line
                json_str = part[part.find("json") + 4:].strip()
            else:
                json_str = part.strip()
            
            # Try to parse this part
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    
    # If no code blocks or parsing failed, try the full text
    return json.loads(text)

@with_cache(ttl_seconds=3600)  # Cache for 1 hour
@with_retries(max_retries=3, base_delay=2.0)
def get_scaffolding_suggestions(project_details: Dict[str, Any], provider: str = "GOOGLE") -> Dict[str, Any]:
    """
    Get project scaffolding suggestions from LLM.
    
    Args:
        project_details: Dictionary containing project information
        provider: The LLM provider to use ("GOOGLE" or "OPENAI")
        
    Returns:
        Dictionary containing suggested project structure and files
    """
    model, error = setup_llm(provider)
    if error:
        return error
    
    try:
        prompt = f"""
        Create a project structure for a {project_details['type']} project named {project_details['name']} 
        using {project_details['language']} as the primary language.
        
        Provide the response in the following JSON format:
        {{
            "files": [
                {{
                    "path": "file/path",
                    "content": "file content"
                }}
            ],
            "directories": [
                {{
                    "path": "directory/path",
                    "files": [
                        {{
                            "path": "file/path",
                            "content": "file content"
                        }}
                    ]
                }}
            ]
        }}
        
        Include:
        - Standard project structure
        - Configuration files
        - Basic implementation files
        - Test directory structure
        - Documentation files
        """
        
        typer.echo("\n--- Sending prompt to LLM for scaffolding suggestions... ---")
        
        if provider.upper() == "GOOGLE":
            response = model.generate_content(prompt)
            response_text = response.text
        elif provider.upper() == "OPENAI":
            response = model.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates project structure suggestions as requested."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content
        else:
            return {"error": f"Unsupported provider: {provider}", "error_type": "ValueError"}
        
        typer.echo("--- Received response from LLM. ---")

        try:
            # Extract JSON from response
            suggestions = extract_json_from_llm_response(response_text)
            
            # Validate structure
            valid_structure = True
            missing_keys = []
            
            if "files" not in suggestions:
                valid_structure = False
                missing_keys.append("files")
            
            if "directories" not in suggestions:
                valid_structure = False
                missing_keys.append("directories")
            
            if not valid_structure:
                typer.secho(f"LLM response missing required keys: {', '.join(missing_keys)}", fg=typer.colors.RED)
                
                # For backward compatibility, convert old format if present
                if "directory_structure" in suggestions and "files_to_create" in suggestions:
                    files = []
                    for file_path, content in suggestions["files_to_create"].items():
                        files.append({"path": file_path, "content": content})
                    
                    directories = []
                    for dir_path in suggestions["directory_structure"]:
                        directories.append({"path": dir_path, "files": []})
                    
                    return {"files": files, "directories": directories}
                
                return {"error": "LLM response format error.", "raw_response": response_text}
            
            return suggestions
        
        except json.JSONDecodeError as e:
            typer.secho(f"Failed to parse LLM response as JSON: {str(e)}", fg=typer.colors.RED)
            typer.echo("LLM Raw Text: \n" + response_text)
            return {"error": "Failed to parse LLM response as JSON.", "error_type": "JSONDecodeError", "raw_response": response_text}
        
        except Exception as e:
            typer.secho(f"An unexpected error occurred processing the LLM response: {str(e)}", fg=typer.colors.RED)
            raw_text = getattr(response, "text", "N/A")
            return {"error": f"Unexpected error processing response: {str(e)}", "error_type": type(e).__name__, "raw_response": raw_text}

    except Exception as e:
        typer.secho(f"ERROR: LLM API call failed: {str(e)}", fg=typer.colors.RED)
        return {"error": f"LLM API call failed: {str(e)}", "error_type": type(e).__name__}

@with_cache(ttl_seconds=3600)  # Cache for 1 hour
@with_retries(max_retries=3, base_delay=2.0)
def review_config_file(content: str, file_type: str, provider: str = "GOOGLE") -> Dict[str, Any]:
    """
    Review configuration file using LLM.
    
    Args:
        content: File content to review
        file_type: Type of configuration file
        provider: The LLM provider to use ("GOOGLE" or "OPENAI")
        
    Returns:
        Dictionary containing review findings
    """
    model, error = setup_llm(provider)
    if error:
        return error
    
    try:
        prompt = f"""
        Review this {file_type} configuration file for best practices, security issues, and potential improvements:

        {content}
        
        Provide the response in the following JSON format:
        {{
            "issues": [
                {{"severity": "high|medium|low", "message": "description"}},
            ],
            "suggestions": [
                "list of suggestions"
            ],
            "best_practices": [
                "list of best practices being followed"
            ]
        }}
        """
        
        typer.echo(f"\n--- Sending prompt to LLM for config review ({file_type})... ---")
        
        if provider.upper() == "GOOGLE":
            generation_config = {"temperature": 0.5, "max_output_tokens": 1024}
            response = model.generate_content(prompt, generation_config=generation_config)
            response_text = response.text
        elif provider.upper() == "OPENAI":
            response = model.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that reviews configuration files."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1024
            )
            response_text = response.choices[0].message.content
        else:
            return {"error": f"Unsupported provider: {provider}", "error_type": "ValueError"}
        
        typer.echo("--- Received response from LLM. ---")

        try:
            # Extract JSON from response
            review = extract_json_from_llm_response(response_text)
            
            # Validate structure
            valid_structure = True
            missing_keys = []
            
            if "issues" not in review:
                valid_structure = False
                missing_keys.append("issues")
            
            if "suggestions" not in review:
                valid_structure = False
                missing_keys.append("suggestions")
            
            if "best_practices" not in review:
                valid_structure = False
                missing_keys.append("best_practices")
            
            if not valid_structure:
                typer.secho(f"LLM response missing required keys: {', '.join(missing_keys)}", fg=typer.colors.RED)
                
                # Create a minimal valid structure if missing
                if "issues" not in review:
                    review["issues"] = []
                if "suggestions" not in review:
                    review["suggestions"] = []
                if "best_practices" not in review:
                    review["best_practices"] = []
            
            return review
        
        except json.JSONDecodeError as e:
            typer.secho(f"Failed to parse LLM config review response as JSON: {str(e)}", fg=typer.colors.RED)
            typer.echo("LLM Raw Text: \n" + response_text)
            return {"error": "Failed to parse LLM response as JSON.", "error_type": "JSONDecodeError", "raw_response": response_text}
        
        except Exception as e:
            typer.secho(f"An unexpected error occurred processing the LLM response: {str(e)}", fg=typer.colors.RED)
            raw_text = getattr(response, "text", "N/A") 
            return {"error": f"Unexpected error processing response: {str(e)}", "error_type": type(e).__name__, "raw_response": raw_text}

    except Exception as e:
        typer.secho(f"ERROR: LLM API config review call failed: {str(e)}", fg=typer.colors.RED)
        return {"error": f"LLM API config review call failed: {str(e)}", "error_type": type(e).__name__}

if __name__ == '__main__':
    # This block is for testing this module directly.
    # Ensure you have a .env file in the project root with GOOGLE_API_KEY.
    print("Testing llm_interface module...")

    from dotenv import load_dotenv
    # Load .env from the project root, assuming this script is in devspark/core
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    print("\n--- Testing Scaffolding Suggestions ---")
    sample_project_details = {"name": "AIScaffoldApp", "type": "Web API", "language": "Python"}
    scaffolding = get_scaffolding_suggestions(sample_project_details)
    if "error" in scaffolding:
        print(f"Error in scaffolding: {scaffolding['error']}")
        if "raw_response" in scaffolding:
            print(f"Raw LLM Response: {scaffolding['raw_response']}")
    else:
        print("\nScaffolding Suggestions (from LLM if successful, or placeholder):")
        print(json.dumps(scaffolding, indent=2))

    print("\n--- Testing Config File Review ---")
    sample_dockerfile = "FROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]"
    review = review_config_file(sample_dockerfile, file_type="Dockerfile")
    if "error" in review:
        print(f"Error in review: {review['error']}")
        if "raw_response" in review:
            print(f"Raw LLM Response: {review['raw_response']}")
    else:
        print("\nConfig Review (from LLM if successful, or placeholder):")
        print(json.dumps(review, indent=2))
        
    # Test cache
    print("\n--- Testing Cache ---")
    print("Making second call to get_scaffolding_suggestions with same parameters (should use cache)...")
    start_time = time.time()
    cached_scaffolding = get_scaffolding_suggestions(sample_project_details)
    end_time = time.time()
    print(f"Second call completed in {end_time - start_time:.4f} seconds (should be faster if cached)")
    
    # Test clearing cache
    print("\n--- Testing Clear Cache ---")
    clear_cache()
    print("Cache cleared. Next call should not use cache.")