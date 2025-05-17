import typer
from dotenv import load_dotenv
import os
import pathlib # For path operations
import json # For pretty printing dicts

# Load environment variables from .env file at the earliest opportunity
# This should be called before other modules that might need the env vars are imported
load_dotenv()

# Import core logic modules
# We use try-except here to give a graceful message if core modules are missing
# or if their dependencies (like google-generativeai) weren't installed.
try:
    from .core import llm_interface, project_generator, config_checker
except ImportError as e:
    typer.secho(f"Error importing core modules: {e}", fg=typer.colors.RED)
    typer.echo("Please ensure all dependencies are installed and core modules are in devspark/core/.")
    # Optionally, exit here or disable commands that rely on these modules
    # For now, we'll let it proceed so basic Typer help works, but commands will fail.
    llm_interface = None
    project_generator = None
    config_checker = None


app = typer.Typer(
    name="devspark",
    help="DevSpark Assistant: Your AI-powered co-pilot for project setup and pre-flight checks!", # Emoji removed for safety
    add_completion=False,
)

@app.command()
def init():
    """
    Initialize a new project with AI-guided scaffolding.
    Walks you through defining your project and generates starter files.
    """
    if not llm_interface or not project_generator:
        typer.secho("Core modules (llm_interface or project_generator) not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("Welcome to DevSpark Project Initialization!") # Emoji removed
    typer.echo("This feature will guide you through setting up a new project.")
    typer.echo("Let's gather some information about your project...")

    project_name = typer.prompt("What is the name of your project (e.g., MyCoolApp)?")
    if not project_name:
        typer.secho("Project name cannot be empty.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    project_type = typer.prompt(
        "What type of project is it (e.g., web app, API, script, library)?",
        default="web app"
    )
    main_language = typer.prompt(
        "What is the primary programming language (e.g., Python, JavaScript)?",
        default="Python"
    )
    # --- You can add more prompts here for details like framework, database, Docker ---
    # Example:
    # framework = typer.prompt(f"Any specific framework for {main_language} (e.g., Flask, React, leave blank if none)?", default="", show_default=False)
    # use_docker = typer.confirm("Do you plan to use Docker for this project?", default=False)


    project_details = {
        "name": project_name,
        "type": project_type,
        "language": main_language,
        # "framework": framework if framework else "N/A",
        # "docker": use_docker,
        # Add other details as you collect them
    }

    typer.echo("\n--- Project Details Collected ---")
    typer.echo(f"Project Name: {project_details['name']}") # Emojis removed
    typer.echo(f"Project Type: {project_details['type']}")
    typer.echo(f"Main Language: {project_details['language']}")
    # typer.echo(f"Framework: {project_details['framework']}")
    # typer.echo(f"Use Docker: {'Yes' if project_details['docker'] else 'No'}")
    typer.echo("--------------------------------")

    if not typer.confirm(f"\nProceed to get scaffolding suggestions from AI for '{project_name}'?", default=True):
        typer.echo("Initialization cancelled by user.")
        raise typer.Exit()

    typer.echo("\nRequesting scaffolding suggestions from the AI...")
    suggestions = llm_interface.get_scaffolding_suggestions(project_details)

    if suggestions.get("error"):
        typer.secho(f"Error getting suggestions from LLM: {suggestions['error']}", fg=typer.colors.RED)
        if "raw_response" in suggestions:
             typer.echo("Raw LLM Response was:")
             typer.echo(suggestions["raw_response"])
        raise typer.Exit(code=1)

    typer.secho("\n--- AI Scaffolding Suggestions Received ---", fg=typer.colors.CYAN)
    # Pretty print the suggestions (optional, good for debugging)
    typer.echo(json.dumps(suggestions, indent=2))
    typer.echo("------------------------------------------")

    if not typer.confirm(f"\nDo you want to create this project structure for '{project_name}' in the current directory?", default=True):
        typer.echo("Project generation cancelled by user.")
        raise typer.Exit()

    try:
        # Assuming current directory is where the new project folder should be created
        base_creation_path = str(pathlib.Path.cwd())
        project_generator.create_project_structure(
            base_path=base_creation_path,
            project_name=project_name, # The generator will create a folder with this name
            structure_suggestions=suggestions
        )
        typer.secho(f"\nProject '{project_name}' successfully scaffolded in '{pathlib.Path(base_creation_path) / project_name}'!", fg=typer.colors.GREEN) # Emoji removed
        typer.echo("Next steps: cd into your new project directory and start coding!")
    except typer.Exit: # Catch exits from project_generator if it uses typer.Exit
        raise
    except Exception as e:
        typer.secho(f"An error occurred during project generation: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def check(
    file: str = typer.Option(None, "--file", "-f", help="Path to a specific configuration file to check."),
    project_dir: str = typer.Option(".", "--dir", "-d", help="Path to the project directory to perform general checks on.")
):
    """
    Perform pre-flight checks on your project or a specific configuration file.
    Uses AI to review for common issues and best practices.
    """
    if not llm_interface or not config_checker:
        typer.secho("Core modules (llm_interface or config_checker) not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if file:
        target_file = pathlib.Path(file)
        if not target_file.is_file():
            typer.secho(f"Error: File not found at '{file}'", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        typer.echo(f"Inspecting configuration file: {target_file.name} with AI...") # Emoji removed
        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            typer.secho(f"Error reading file '{file}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        file_type = target_file.suffix.lstrip('.') if target_file.suffix else "unknown"
        if target_file.name.lower() == "dockerfile":
            file_type = "Dockerfile"

        review = llm_interface.review_config_file(content, file_type=file_type)

        if review.get("error"):
            typer.secho(f"Error getting review from LLM: {review['error']}", fg=typer.colors.RED)
            if "raw_response" in review:
                typer.echo("Raw LLM Response was:")
                typer.echo(review["raw_response"])
            raise typer.Exit(code=1)

        typer.secho(f"\n--- AI Review for {target_file.name} ---", fg=typer.colors.CYAN)
        typer.echo(json.dumps(review, indent=2)) # Pretty print the review
        typer.echo("-----------------------------------")


    elif project_dir:
        typer.echo(f"Performing general checks on project directory: {project_dir}") # Emoji removed
        findings = config_checker.perform_local_checks(project_dir)
        typer.secho("\n--- Local Check Findings ---", fg=typer.colors.CYAN)
        if findings:
            for finding in findings:
                if "Suggestion:" in finding:
                    typer.secho(finding, fg=typer.colors.YELLOW)
                elif "Error:" in finding or "Warning:" in finding: # Assuming you might add Warning:
                    typer.secho(finding, fg=typer.colors.RED)
                else:
                    typer.echo(finding)
        else:
            typer.echo("No specific findings from local checks.")
        typer.echo("---------------------------")
        # TODO: Optionally, identify key config files in project_dir and send for LLM review
        # For example:
        # for common_config in ["Dockerfile", "docker-compose.yml", "package.json", "requirements.txt"]:
        #     config_file_path = pathlib.Path(project_dir) / common_config
        #     if config_file_path.exists():
        #         # Call the file review logic similar to the `if file:` block
        #         typer.echo(f"\n--- Reviewing {common_config} with AI ---")
        #         # ... (call review_config_file) ...
        typer.echo("AI review for all project config files not yet implemented for --dir.")

    else:
        typer.secho(
            "Please specify a file to check with --file OR a project directory with --dir.",
            fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

@app.callback()
def main():
    """
    DevSpark Assistant CLI.
    Use --help for more information on commands.
    """
    # Ensure API key is loaded and core modules are available
    if not os.getenv("GOOGLE_API_KEY") and (llm_interface or config_checker or project_generator) : # only warn if modules are loaded but key is missing
        # This check is basic. llm_interface.get_llm_api_key() does a more specific check when called.
        typer.secho(
            "Warning: GOOGLE_API_KEY not found in .env file or environment variables. LLM features may not work.",
            fg=typer.colors.YELLOW
        )
    if not all([llm_interface, project_generator, config_checker]):
         typer.secho(
            "Warning: One or more core modules could not be imported. Some functionality may be unavailable.",
            fg=typer.colors.YELLOW
        )

if __name__ == "__main__":
    app()