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
try:
    import google.generativeai as genai
except ImportError:
    # This allows the module to be imported even if google-generativeai is not yet installed,
    # but functions using it will fail.
    genai = None
    typer.secho("Warning: 'google-generativeai' package not found. LLM features will not work.", fg=typer.colors.YELLOW)

# Example: If using OpenAI
# import openai

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

def get_scaffolding_suggestions(project_details: dict) -> dict:
    """
    Queries the LLM to get project scaffolding suggestions.

    Args:
        project_details (dict): A dictionary containing details about the project
                                (name, type, language, frameworks, etc.).

    Returns:
        dict: A dictionary containing LLM suggestions (e.g., directory structure,
              file names, basic config content).
    """
    if not genai:
        return {"error": "'google-generativeai' package is required for this feature."}

    api_key = get_llm_api_key()
    if not api_key:
        return {"error": "API key not found. Please set GOOGLE_API_KEY."}

    try:
        genai.configure(api_key=api_key)
        generation_config = {
            "temperature": 0.7, # Adjust for creativity vs. predictability
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048, # Adjust as needed
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest", # Or "gemini-pro" or other compatible model
            generation_config=generation_config,
        )

        prompt_parts = [
            "You are an expert software development assistant specializing in project scaffolding.",
            "Based on the following project details, please provide a clear and actionable scaffolding plan.",
            f"Project Name: {project_details.get('name', 'N/A')}",
            f"Project Type: {project_details.get('type', 'N/A')}",
            f"Main Programming Language: {project_details.get('language', 'N/A')}",
            "\nProvide the output as a JSON object with two main keys:",
            "1. 'directory_structure': A list of strings, where each string is a relative path for a directory to be created (e.g., 'src', 'tests', 'src/components').",
            "2. 'files_to_create': A JSON object where keys are relative file paths (e.g., 'src/main.py', 'README.md') and values are the suggested initial content for these files.",
            "Keep file content concise and functional for a starter project.",
            "Example for 'files_to_create': {\"README.md\": \"# Project Title\\nDescription...\", \"src/app.py\": \"print('Hello World')\"}",
            "Ensure all paths are relative to the project root.",
            "If suggesting a .gitignore, include common ignores for the specified language and also '.env', 'venv/', '.venv.'."
        ]
        prompt = "\n".join(prompt_parts)

        typer.echo("\n--- Sending prompt to LLM for scaffolding suggestions... ---")

        response = model.generate_content(prompt)

        typer.echo("--- Received response from LLM. ---")

        try:
            clean_response_text = response.text.strip()
            if clean_response_text.startswith("```json"):
                clean_response_text = clean_response_text[7:]
            if clean_response_text.endswith("```"):
                clean_response_text = clean_response_text[:-3]
            
            suggestions = json.loads(clean_response_text.strip())
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

def review_config_file(file_content: str, file_type: str = "unknown") -> dict:
    """
    Queries the LLM to review a configuration file content.

    Args:
        file_content (str): The content of the configuration file.
        file_type (str): The type of the configuration file (e.g., Dockerfile, package.json).

    Returns:
        dict: A dictionary containing LLM review (e.g., suggestions, potential issues).
    """
    if not genai:
        return {"error": "'google-generativeai' package is required for this feature."}

    api_key = get_llm_api_key()
    if not api_key:
        return {"error": "API key not found. Please set GOOGLE_API_KEY."}

    try:
        genai.configure(api_key=api_key)
        generation_config = {"temperature": 0.5, "max_output_tokens": 1024}
        model = genai.GenerativeModel("gemini-1.5-flash-latest", generation_config=generation_config)

        prompt_parts = [
            f"You are an expert software development assistant. Please review the following configuration file (type: {file_type}).",
            "Identify potential issues, suggest improvements, or highlight best practices.",
            "Provide your review as a JSON object with keys like 'summary', 'suggestions' (a list of strings), and 'potential_issues' (a list of strings).",
            "File content:",
            "```" + file_type,
            file_content,
            "```"
        ]
        prompt = "\n".join(prompt_parts)
        
        typer.echo(f"\n--- Sending prompt to LLM for config review ({file_type})... ---")
        response = model.generate_content(prompt)
        typer.echo("--- Received response from LLM. ---")

        try:
            clean_response_text = response.text.strip()
            if clean_response_text.startswith("```json"):
                clean_response_text = clean_response_text[7:]
            if clean_response_text.endswith("```"):
                clean_response_text = clean_response_text[:-3]

            review = json.loads(clean_response_text.strip())
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