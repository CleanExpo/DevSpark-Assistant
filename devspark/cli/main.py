"""
DevSpark Assistant CLI
Main entry point for the CLI application
"""

import typer
from pathlib import Path
from typing import Optional
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import core modules
try:
    from devspark.core import llm_interface, project_generator, config_checker
    from devspark.utils import dev_rules, shell_helper
except ImportError as e:
    typer.secho(f"Error importing core modules: {e}", fg=typer.colors.RED)
    typer.echo("Please ensure all dependencies are installed.")
    llm_interface = None
    project_generator = None
    config_checker = None
    dev_rules = None
    shell_helper = None

app = typer.Typer(
    name="devspark",
    help="DevSpark Assistant: Your AI-powered co-pilot for project setup and development environment management",
    add_completion=False,
)

@app.command()
def init(
    name: str = typer.Option(None, "--name", "-n", prompt="Project name", help="Name of the project"),
    type: str = typer.Option(
        "web app",
        "--type",
        "-t",
        prompt="Project type",
        help="Type of project (e.g., web app, API, library)",
    ),
    language: str = typer.Option(
        "Python",
        "--lang",
        "-l",
        prompt="Primary programming language",
        help="Primary programming language",
    ),
):
    """
    Initialize a new project with AI-guided scaffolding.
    """
    if not all([llm_interface, project_generator, dev_rules]):
        typer.secho("Required modules not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    project_details = {
        "name": name,
        "type": type,
        "language": language,
    }

    typer.echo("\n--- Project Details ---")
    typer.echo(f"Project Name: {name}")
    typer.echo(f"Project Type: {type}")
    typer.echo(f"Main Language: {language}")
    typer.echo("--------------------")

    if not typer.confirm(f"\nProceed to get scaffolding suggestions from AI for '{name}'?", default=True):
        typer.echo("Initialization cancelled by user.")
        raise typer.Exit()

    typer.echo("\nRequesting scaffolding suggestions from the AI...")
    suggestions = llm_interface.get_scaffolding_suggestions(project_details)

    if suggestions.get("error"):
        typer.secho(f"Error getting suggestions from LLM: {suggestions['error']}", fg=typer.colors.RED)
        if "raw_response" in suggestions:
            typer.echo("Raw LLM Response was:")
            typer.echo(suggestions["raw_response"])
        raise typer.Exit(1)

    typer.secho("\n--- AI Scaffolding Suggestions ---", fg=typer.colors.CYAN)
    typer.echo(json.dumps(suggestions, indent=2))
    typer.echo("--------------------------------")

    if not typer.confirm(f"\nCreate this project structure for '{name}' in the current directory?", default=True):
        typer.echo("Project generation cancelled by user.")
        raise typer.Exit()

    try:
        # Create project structure
        base_creation_path = str(Path.cwd())
        project_path = Path(base_creation_path) / name
        
        project_generator.create_project_structure(
            base_path=base_creation_path,
            project_name=name,
            structure_suggestions=suggestions
        )

        # Setup development environment
        typer.echo("\nSetting up development environment...")
        success, message = dev_rules.dev_rules.setup_dev_environment(str(project_path))
        if not success:
            typer.secho(f"Error setting up environment: {message}", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Install development dependencies
        typer.echo("\nInstalling development dependencies...")
        success, message = dev_rules.dev_rules.install_dev_dependencies(str(project_path))
        if not success:
            typer.secho(f"Error installing dependencies: {message}", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Setup development tools
        typer.echo("\nConfiguring development tools...")
        success, message = dev_rules.dev_rules.setup_dev_tools(str(project_path))
        if not success:
            typer.secho(f"Error setting up tools: {message}", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Initialize git repository if requested
        if typer.confirm("\nWould you like to initialize a Git repository?", default=True):
            success, message = dev_rules.dev_rules.setup_git_hooks(str(project_path))
            if not success:
                typer.secho(f"Error setting up Git: {message}", fg=typer.colors.RED)
            else:
                typer.secho("Git repository initialized successfully!", fg=typer.colors.GREEN)

        typer.secho(f"\n✨ Project {name} initialized successfully!", fg=typer.colors.GREEN)
        typer.echo("\nNext steps:")
        typer.echo(f"  1. cd {name}")
        typer.echo(f"  2. Activate virtual environment:")
        typer.echo(f"     - Windows: .\\venv\\Scripts\\activate")
        typer.echo(f"     - Unix: source venv/bin/activate")
        typer.echo(f"  3. Start coding!")

    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command()
def check(
    file: str = typer.Option(None, "--file", "-f", help="Path to a specific configuration file to check"),
    project_dir: str = typer.Option(".", "--dir", "-d", help="Path to the project directory to check"),
):
    """
    Check development environment setup and configuration.
    """
    if not all([llm_interface, config_checker, dev_rules]):
        typer.secho("Required modules not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if file:
        target_file = Path(file)
        if not target_file.is_file():
            typer.secho(f"Error: File not found at '{file}'", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.echo(f"Inspecting configuration file: {target_file.name} with AI...")
        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            typer.secho(f"Error reading file '{file}': {e}", fg=typer.colors.RED)
            raise typer.Exit(1)

        file_type = target_file.suffix.lstrip('.') if target_file.suffix else "unknown"
        if target_file.name.lower() == "dockerfile":
            file_type = "Dockerfile"

        review = llm_interface.review_config_file(content, file_type=file_type)

        if review.get("error"):
            typer.secho(f"Error getting review from LLM: {review['error']}", fg=typer.colors.RED)
            if "raw_response" in review:
                typer.echo("Raw LLM Response was:")
                typer.echo(review["raw_response"])
            raise typer.Exit(1)

        typer.secho(f"\n--- AI Review for {target_file.name} ---", fg=typer.colors.CYAN)
        typer.echo(json.dumps(review, indent=2))
        typer.echo("-----------------------------------")

    # Run development environment checks
    typer.echo(f"\nChecking development environment in: {project_dir}")
    findings = dev_rules.dev_rules.run_dev_checks(project_dir)

    for finding in findings:
        if finding["type"] == "error":
            typer.secho(f"❌ {finding['message']}", fg=typer.colors.RED)
        elif finding["type"] == "warning":
            typer.secho(f"⚠️ {finding['message']}", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"ℹ️ {finding['message']}", fg=typer.colors.BLUE)

    # Run local configuration checks
    local_findings = config_checker.perform_local_checks(project_dir)
    if local_findings:
        typer.secho("\n--- Local Configuration Checks ---", fg=typer.colors.CYAN)
        for finding in local_findings:
            if "Suggestion:" in finding:
                typer.secho(finding, fg=typer.colors.YELLOW)
            elif "Error:" in finding or "Warning:" in finding:
                typer.secho(finding, fg=typer.colors.RED)
            else:
                typer.echo(finding)

@app.command()
def config(
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to the project directory",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode",
    ),
    env: str = typer.Option(
        "development",
        "--env",
        "-e",
        help="Environment (development, staging, production)",
    ),
):
    """
    Configure development environment settings.
    """
    if not dev_rules:
        typer.secho("Required modules not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    config = {
        "environment": env,
        "debug_mode": debug,
        "timestamp": "auto",
    }

    success, message = dev_rules.dev_rules.create_dev_config(path, config)

    if success:
        typer.secho("✨ Configuration updated successfully!", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Error updating configuration: {message}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.callback()
def main():
    """
    DevSpark Assistant CLI.
    Use --help for more information on commands.
    """
    if not os.getenv("GOOGLE_API_KEY") and any([llm_interface, config_checker, project_generator]):
        typer.secho(
            "Warning: GOOGLE_API_KEY not found in .env file or environment variables. LLM features may not work.",
            fg=typer.colors.YELLOW
        )

if __name__ == "__main__":
    app() 