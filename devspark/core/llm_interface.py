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
import logging
from typing import Dict, Optional, Any, Tuple, Callable, List
from functools import wraps
import traceback
import re
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

# Set up logging
logger = logging.getLogger("devspark.llm")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Default level, can be changed via set_log_level()

def set_log_level(level):
    """Set the logging level for the LLM interface.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logger.setLevel(level)
    logger.info(f"LLM interface logging level set to {logging.getLevelName(level)}")

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
    Extract JSON object from LLM response text.
    
    Args:
        response_text: Raw text response from LLM
        
    Returns:
        Extracted JSON object or empty dict if extraction failed
    """
    if not response_text:
        return {}
    
    # Try to find JSON in response - look for text between ```json and ``` markers
    json_match = re.search(r'```(?:json)?\s*({[\s\S]+?})\s*```', response_text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # If no json block markers, try to extract anything that looks like valid JSON
        json_match = re.search(r'({[\s\S]*})', response_text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = response_text.strip()
    
    # Pre-processing to fix common issues
    
    # 1. Fix backtick template literals
    # Find patterns like "content": `...` and replace with "content": "..."
    pattern = r'"([^"]+)":\s*`([^`]*)`'
    
    def replace_backticks(match):
        property_name = match.group(1)
        content = match.group(2)
        # Escape newlines and quotes
        content = content.replace('\n', '\\n')
        content = content.replace('"', '\\"')
        return f'"{property_name}": "{content}"'
        
    json_str = re.sub(pattern, replace_backticks, json_str)
    
    # 2. Fix invalid patterns like using string as a key without quotes
    # Example: ".gitignore": "content" -> "path": ".gitignore", "content": "content"
    json_str = re.sub(r'["\'](\.[\w]+)["\']:\s*["\'](.*?)["\']', r'"files": [{"path": "\1", "content": "\2"}]', json_str)
    
    # 3. Create an old-format structure for compatibility
    try:
        # First try to parse the JSON as is
        result = json.loads(json_str)
        
        # If it doesn't have the expected structure with files or directories,
        # try to create a compatible structure
        if "files" in result and "directories" in result:
            # Structure is good
            # Convert to old format for compatibility
            directory_structure = []
            files_to_create = {}
            
            # Handle root files
            for file_info in result.get("files", []):
                if isinstance(file_info, dict) and "path" in file_info and "content" in file_info:
                    files_to_create[file_info["path"]] = file_info["content"]
            
            # Handle directories and their files
            for dir_info in result.get("directories", []):
                if isinstance(dir_info, dict) and "path" in dir_info:
                    directory_structure.append(dir_info["path"])
                    
                    if "files" in dir_info:
                        for file_info in dir_info["files"]:
                            if isinstance(file_info, dict) and "path" in file_info and "content" in file_info:
                                full_path = os.path.join(dir_info["path"], file_info["path"])
                                files_to_create[full_path] = file_info["content"]
            
            # Update result with converted format
            result["directory_structure"] = directory_structure
            result["files_to_create"] = files_to_create
            
        elif "directory_structure" not in result or "files_to_create" not in result:
            print("LLM response missing required keys: directory_structure, files_to_create")
            return {"error": "LLM response format error.", "raw_response": response_text}
            
        return result
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as JSON: {e}")
        print(f"LLM Raw Text: {response_text}")
        return {"error": f"Failed to parse LLM response as JSON: {e}", "raw_response": response_text}

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

@with_cache(ttl_seconds=3600)  # Cache for 1 hour
@with_retries(max_retries=3, base_delay=2.0)
def get_template_customization(
    project_details: Dict[str, Any], 
    template_data: Dict[str, Any],
    provider: str = "GOOGLE"
) -> Dict[str, Any]:
    """
    Get customized project scaffold suggestions from LLM, starting with an existing template.
    
    Args:
        project_details: Dictionary with project details (name, type, language, etc.)
        template_data: Dictionary with the template structure to customize
        provider: LLM provider to use
        
    Returns:
        Dictionary with customized project structure or error
    """
    try:
        model, error = setup_llm(provider)
        if error:
            return error
        
        # Convert template structure to pretty-printed JSON string
        template_json = json.dumps(template_data, indent=2)
        
        # Prepare prompt for LLM
        prompt = f"""
You are an expert software development assistant tasked with customizing project templates.

IMPORTANT INSTRUCTIONS:
1. You will be given a BASE PROJECT TEMPLATE in JSON format.
2. You must MODIFY this template based on the project details and description.
3. Return the COMPLETE, CUSTOMIZED project structure as a JSON object.

The JSON object MUST have these two main keys:
- "directory_structure": A list of strings, where each string is a relative path for a directory
- "files_to_create": A JSON object where keys are relative file paths and values are the file contents

PROJECT DETAILS:
- Name: {project_details.get('name', 'MyProject')}
- Type: {project_details.get('type', 'Application')}
- Language: {project_details.get('language', 'JavaScript')}
- Description: {project_details.get('description', 'A new project')}

BASE PROJECT TEMPLATE:
```json
{template_json}
```

YOUR TASK:
1. START with the base template structure provided above
2. ADAPT and EXTEND it to fulfill the specific requirements in the project description
3. ENSURE all files reference the correct project name: {project_details.get('name', 'MyProject')}
4. ADD appropriate files/directories based on the project description
5. MODIFY existing file content to reflect the specific needs
6. Return ONLY the final JSON object with NO explanations

CONSTRAINTS:
- Use double quotes for JSON strings, not backticks
- Format any multi-line content with escaped newlines (\\n)
- Include ALL necessary directories in the directory_structure
- Make sure ALL file paths in files_to_create are relative to the project root
- Your response must be VALID JSON that can be parsed directly
"""
        
        if provider.upper() == "GOOGLE":
            response = model.generate_content(prompt)
            response_text = response.text
        elif provider.upper() == "OPENAI":
            response = model.chat.completions.create(
                model="gpt-4-0125-preview",  # Use an appropriate model
                messages=[
                    {"role": "system", "content": "You are an expert software developer specializing in project templating."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            response_text = response.choices[0].message.content
        else:
            return {"error": f"Unsupported provider: {provider}", "error_type": "ValueError"}
            
        # Process response
        results = extract_json_from_llm_response(response_text)
        
        # If extraction failed and we have a response, return it for debugging
        if not results and response_text:
            return {
                "error": "Failed to extract valid JSON from LLM response",
                "error_type": "JSONParseError",
                "raw_response": response_text
            }
            
        return results
        
    except Exception as e:
        return {
            "error": f"LLM interface error: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@with_cache(ttl_seconds=3600)  # Cache for 1 hour
@with_retries(max_retries=3, base_delay=2.0)
def get_ai_customized_template(
    project_details: Dict[str, Any], 
    template_data: Dict[str, Any],
    provider: str = "GOOGLE"
) -> Dict[str, Any]:
    """
    Get AI-enhanced customization for project templates based on detailed user requirements.
    
    Args:
        project_details: Dictionary with project details (name, type, language, etc.) and ai_customization_description
        template_data: Dictionary with the template structure to customize
        provider: LLM provider to use
        
    Returns:
        Dictionary with AI-customized project structure or error
    """
    try:
        logger.info(f"Starting AI template customization for project '{project_details.get('name', 'unnamed')}'")
        logger.debug(f"Project details: {json.dumps(project_details, indent=2)}")
        
        model, error = setup_llm(provider)
        if error:
            logger.error(f"Failed to set up LLM: {error}")
            return error
        
        # Convert template structure to pretty-printed JSON string
        template_json = json.dumps(template_data, indent=2)
        
        # Get the AI customization description from project details
        customization_description = project_details.get('ai_customization_description', "")
        logger.info(f"Customization description: {customization_description}")
        
        # Extract other project details
        project_name = project_details.get('name', 'MyProject')
        project_type = project_details.get('type', 'Application')
        project_language = project_details.get('language', 'Python')
        project_description = project_details.get('description', 'A new project')
        
        # Get additional template-specific parameters
        api_prefix = project_details.get('api_prefix', None)
        resource_name = project_details.get('resource_name', None)
        author_name = project_details.get('author_name', None)
        python_version = project_details.get('python_version', None)
        # Node.js specific parameters
        api_base_path = project_details.get('api_base_path', None)
        main_resource_name = project_details.get('main_resource_name', None)
        node_version = project_details.get('node_version', None)
        
        # Determine if this is a database integration request
        is_database_request = any(term in customization_description.lower() 
                                 for term in ['database', 'db', 'sqlalchemy', 'sql', 'mongo', 'mongoose', 'orm'])
        
        if is_database_request:
            logger.info("Database integration request detected")
            
        # Prepare a more detailed prompt for LLM
        prompt = f"""
You are an expert software development assistant.
You will be given a base project template in JSON string format and a description of desired customizations.
Your task is to take the base template, apply the customizations, and return the COMPLETE, MODIFIED project structure as a JSON object.
This JSON object must strictly adhere to the following format:
{{
  "directory_structure": ["list", "of", "relative/paths/to/create"],
  "files_to_create": {{
    "relative/path/to/file1.py": "content of file1...",
    "relative/path/to/another_file.md": "content for another file..."
  }}
}}
Ensure all file content is properly escaped for JSON string values (e.g., newlines as \\n, quotes as \\").

Base Project Template (JSON string):
```json
{template_json}
```

Project Details and Desired Customizations:
Project Name: {project_name}
Project Type: {project_type}
Main Language: {project_language}
Project Description: {project_description}
"""

        # Add template-specific parameters if they exist
        if api_prefix:
            prompt += f"API Prefix: {api_prefix}\n"
        if resource_name:
            prompt += f"Resource Name: {resource_name}\n"
        if author_name:
            prompt += f"Author: {author_name}\n"
        if python_version:
            prompt += f"Python Version: {python_version}\n"
        if api_base_path:
            prompt += f"API Base Path: {api_base_path}\n"
        if main_resource_name:
            prompt += f"Main Resource Name: {main_resource_name}\n"
        if node_version:
            prompt += f"Node.js Version: {node_version}\n"

        # Add the customization description
        prompt += f"""
Specific Customizations Requested: {customization_description}

IMPORTANT INSTRUCTIONS:
1. Make ONLY the changes specified in the customization description
2. Keep the rest of the template structure intact
3. Maintain consistency with the existing file naming and code style
"""

        # Add language-specific instructions
        if project_language.lower() == "python":
            prompt += """
4. For Python Flask API templates:
   - Properly update imports when adding new files
   - Register new blueprints in the app/__init__.py file if needed
   - Maintain RESTful API patterns for any new endpoints
"""
        elif project_language.lower() == "node.js":
            prompt += """
4. For Node.js Express API templates:
   - Properly update imports/requires when adding new files
   - Register new routes in the appropriate route files
   - Maintain RESTful API patterns for any new endpoints
   - Update package.json dependencies as needed
"""

        # Add database-specific instructions if this is a database integration request
        if is_database_request:
            prompt += """
5. For database integration requests:
"""
            if project_language.lower() == "python":
                prompt += """
   - Add appropriate database dependencies in requirements.txt
   - Create a database extension/configuration file (e.g., app/extensions.py)
   - Add proper model definitions with SQLAlchemy classes
   - Update services to use the models for CRUD operations
   - Add database connection configuration to app/__init__.py
   - Include environment variables for database connection in .env.example
   - Add migration setup if using Flask-Migrate/Alembic
   - Ensure proper error handling for database operations
"""
            elif project_language.lower() == "node.js":
                prompt += """
   - Add appropriate database dependencies in package.json
   - Create a database configuration file (e.g., src/config/db.js)
   - Add proper model definitions (Mongoose schemas for MongoDB)
   - Update services to use the models for CRUD operations
   - Connect to the database in the main application file
   - Include environment variables for database connection in .env.example
   - Ensure proper error handling for database operations
"""
        
        # Final instructions
        prompt += """
6. Make sure your output is properly formatted JSON with escaped quotes and newlines

Please provide ONLY the complete, customized JSON object output representing the new project structure.
Do not add any explanatory text before or after the JSON object.
"""

        # Log the prompt for debugging
        typer.echo("\n--- Sending AI Customization Prompt to LLM ---")
        logger.debug(f"LLM Prompt:\n{prompt}")
        
        # Make API call
        logger.info(f"Sending request to {provider} LLM")
        
        if provider.upper() == "GOOGLE":
            response = model.generate_content(prompt)
            response_text = response.text
        elif provider.upper() == "OPENAI":
            response = model.chat.completions.create(
                model="gpt-4-0125-preview",  # Use an appropriate model
                messages=[
                    {"role": "system", "content": "You are an expert software developer specializing in project templating."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            response_text = response.choices[0].message.content
        else:
            logger.error(f"Unsupported provider: {provider}")
            return {"error": f"Unsupported provider: {provider}", "error_type": "ValueError"}
        
        typer.echo("--- Received response from LLM ---")
        logger.info("Response received from LLM")
        logger.debug(f"Raw LLM Response:\n{response_text}")
        
        # Process response
        logger.info("Extracting JSON from LLM response")
        results = extract_json_from_llm_response(response_text)
        
        # If extraction failed and we have a response, return it for debugging
        if not results and response_text:
            logger.error("Failed to extract valid JSON from LLM response")
            return {
                "error": "Failed to extract valid JSON from LLM response",
                "error_type": "JSONParseError",
                "raw_response": response_text
            }
        
        # Validate that the results have the required structure
        if "directory_structure" not in results and "files_to_create" not in results:
            if "files" in results and "directories" in results:
                # The response is in the new template format
                logger.info("LLM response uses new template format, converting")
                typer.echo("LLM response uses new template format, which is compatible")
            else:
                logger.error("LLM response doesn't have the expected structure")
                typer.secho("LLM response doesn't have the expected structure", fg=typer.colors.YELLOW)
                typer.echo("Raw LLM Response: \n" + response_text)
                return {
                    "error": "LLM response missing required keys: directory_structure and/or files_to_create",
                    "error_type": "InvalidStructure",
                    "raw_response": response_text
                }
        
        logger.info("Successfully processed LLM response")
        logger.debug(f"Generated {len(results.get('files_to_create', {}))} files and {len(results.get('directory_structure', []))} directories")
        return results
        
    except Exception as e:
        logger.exception(f"Error in AI template customization: {str(e)}")
        return {
            "error": f"LLM interface error: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

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
    
    print("\n--- Testing AI Template Customization with Database Integration ---")
    # Test Flask SQLAlchemy Integration
    db_flask_project = {
        "name": "FlaskSQLAPI",
        "type": "API",
        "language": "Python",
        "description": "Flask API with SQLAlchemy database",
        "api_prefix": "api/v1",
        "resource_name": "user",
        "author_name": "Test Author",
        "python_version": "3.9",
        "ai_customization_description": "Add SQLAlchemy integration with a User model"
    }
    
    # Test MongoDB Integration
    db_node_project = {
        "name": "MongoExpressAPI",
        "type": "API",
        "language": "Node.js",
        "description": "Express API with MongoDB",
        "api_base_path": "/api/v1",
        "main_resource_name": "user",
        "author_name": "Test Author",
        "node_version": "18.x",
        "ai_customization_description": "Add MongoDB database connection with Mongoose"
    }
    
    # Load a template to test with
    try:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'python_flask_api.json')
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Test if database integration detection works
        model, _ = setup_llm()
        if model:  # Only try this if we have a valid API key
            print("Testing if database integration detection is working...")
            print(f"Flask SQLAlchemy request detected: {any(term in db_flask_project['ai_customization_description'].lower() for term in ['database', 'db', 'sqlalchemy', 'sql', 'mongo', 'mongoose', 'orm'])}")
            print(f"MongoDB request detected: {any(term in db_node_project['ai_customization_description'].lower() for term in ['database', 'db', 'sqlalchemy', 'sql', 'mongo', 'mongoose', 'orm'])}")
            
            # Uncomment to test the actual LLM call
            # print("Sending request to LLM (uncomment to test with real API call)...")
            # customization = get_ai_customized_template(db_flask_project, template_data)
            # if "error" in customization:
            #     print(f"Error in customization: {customization['error']}")
            # else:
            #     print("Successfully generated customized template with database integration")
            #     print(f"Files to create: {len(customization.get('files_to_create', {}))}")
    except Exception as e:
        print(f"Error testing database integration: {str(e)}")
        
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