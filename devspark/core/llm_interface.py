"""
Module for all interactions with Large Language Models (LLMs).

This module will handle:
- Formatting prompts.
- Sending requests to LLM APIs (e.g., Gemini, OpenAI).
- Parsing responses from LLMs.
- Error handling for API interactions.
"""

import os
import json # For parsing LLM JSON responses
import typer # Temporary for user feedback, ideally errors are bubbled up
from typing import Dict, Optional, Any
try:
    import google.generativeai as genai
except ImportError:
    # This allows the module to be imported even if google-generativeai is not yet installed,
    # but functions using it will fail.
    genai = None
    typer.secho("Warning: 'google-generativeai' package not found. LLM features will not work.", fg=typer.colors.YELLOW)

# Example: If using OpenAI
# import openai

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_llm_api_key(service_name: str = "GOOGLE"):
    """
    Retrieves the API key for the specified LLM service from environment variables.
    """
    if service_name.upper() == "GOOGLE":
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            typer.secho("ERROR: GOOGLE_API_KEY not found in environment variables or .env file.", fg=typer.colors.RED)
            typer.echo("Please ensure your .env file is in the project root and contains your GOOGLE_API_KEY.")
        return key
    # elif service_name.upper() == "OPENAI":
    #     return os.getenv("OPENAI_API_KEY")
    else:
        # Placeholder for other services or error handling
        return None

def setup_llm():
    """Setup LLM client based on available API keys."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro')

def get_scaffolding_suggestions(project_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get project scaffolding suggestions from LLM.
    
    Args:
        project_details: Dictionary containing project information
        
    Returns:
        Dictionary containing suggested project structure and files
    """
    if not genai:
        return {"error": "'google-generativeai' package is required for this feature."}

    api_key = get_llm_api_key()
    if not api_key:
        return {"error": "API key not found. Please set GOOGLE_API_KEY."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest", # Or "gemini-pro" or other compatible model
        )

        prompt = f"""
        Create a project structure for a {project_details['type']} project named {project_details['name']} 
        using {project_details['language']} as the primary language.
        
        Provide the response in the following JSON format:
        {{
            "directory_structure": ["list", "of", "directories"],
            "files_to_create": {{
                "file/path": "file content",
                "another/file": "content"
            }}
        }}
        
        Include:
        - Standard project structure
        - Configuration files
        - Basic implementation files
        - Test directory structure
        - Documentation files
        """
        
        typer.echo("\n--- Sending prompt to LLM for scaffolding suggestions... ---")
        response = model.generate_content(prompt)
        typer.echo("--- Received response from LLM. ---")

        try:
            # Extract JSON from response
            json_str = response.text.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1]
            if json_str.endswith("```"):
                json_str = json_str.split("```")[0]
            
            suggestions = json.loads(json_str)
            if "directory_structure" not in suggestions or "files_to_create" not in suggestions:
                typer.secho("LLM response received, but not in the expected JSON format.", fg=typer.colors.RED)
                return {"error": "LLM response format error.", "raw_response": response.text}
            return suggestions
        except json.JSONDecodeError:
            typer.secho("Failed to parse LLM response as JSON.", fg=typer.colors.RED)
            typer.echo("LLM Raw Text: \n" + response.text)
            return {"error": "Failed to parse LLM response as JSON.", "raw_response": response.text}
        except Exception as e:
            typer.secho(f"An unexpected error occurred processing the LLM response: {e}", fg=typer.colors.RED)
            raw_text = "N/A"
            try:
                raw_text = response.text
            except: pass
            return {"error": f"Unexpected error processing response: {e}", "raw_response": raw_text}

    except Exception as e:
        typer.secho(f"ERROR: LLM API call failed: {e}", fg=typer.colors.RED)
        return {"error": f"LLM API call failed: {e}"}

def review_config_file(content: str, file_type: str) -> Dict[str, Any]:
    """
    Review configuration file using LLM.
    
    Args:
        content: File content to review
        file_type: Type of configuration file
        
    Returns:
        Dictionary containing review findings
    """
    if not genai:
        return {"error": "'google-generativeai' package is required for this feature."}

    api_key = get_llm_api_key()
    if not api_key:
        return {"error": "API key not found. Please set GOOGLE_API_KEY."}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest", generation_config={"temperature": 0.5, "max_output_tokens": 1024})

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
        response = model.generate_content(prompt)
        typer.echo("--- Received response from LLM. ---")

        try:
            # Extract JSON from response
            json_str = response.text.strip()
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1]
            if json_str.endswith("```"):
                json_str = json_str.split("```")[0]
            
            review = json.loads(json_str)
            return review
        except json.JSONDecodeError:
            typer.secho("Failed to parse LLM config review response as JSON.", fg=typer.colors.RED)
            typer.echo("LLM Raw Text: \n" + response.text)
            return {"error": "Failed to parse LLM response as JSON.", "raw_response": response.text}
        except Exception as e:
            typer.secho(f"An unexpected error occurred processing the LLM response: {e}", fg=typer.colors.RED)
            raw_text = "N/A"
            try: raw_text = response.text
            except: pass
            return {"error": f"Unexpected error processing response: {e}", "raw_response": raw_text}

    except Exception as e:
        typer.secho(f"ERROR: LLM API config review call failed: {e}", fg=typer.colors.RED)
        return {"error": f"LLM API config review call failed: {e}"}

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