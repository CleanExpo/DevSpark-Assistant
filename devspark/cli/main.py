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
import sys
from enum import Enum

# Load environment variables
load_dotenv()

# Add parent directory to sys.path to import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

class LogLevel(str, Enum):
    """Log levels for the CLI"""
    NONE = "none"  # No logging output (default)
    INFO = "info"  # Basic information
    DEBUG = "debug"  # Detailed debug information
    TRACE = "trace"  # Very detailed trace information (including LLM prompts/responses)

# Global options
verbose_option = typer.Option(
    LogLevel.NONE, 
    "--verbose", 
    "-v", 
    help="Set verbosity level"
)

@app.callback()
def callback(
    verbose: LogLevel = verbose_option,
):
    """
    Configure global options for DevSpark Assistant
    """
    import logging
    
    # Set up root logger
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure logging based on verbosity level
    if verbose == LogLevel.NONE:
        # Disable logging except for critical errors
        root_logger.setLevel(logging.CRITICAL)
        llm_interface.set_log_level(logging.CRITICAL)
    elif verbose == LogLevel.INFO:
        root_logger.setLevel(logging.INFO)
        llm_interface.set_log_level(logging.INFO)
    elif verbose == LogLevel.DEBUG:
        root_logger.setLevel(logging.DEBUG)
        llm_interface.set_log_level(logging.DEBUG)
    elif verbose == LogLevel.TRACE:
        # Set to most detailed level
        root_logger.setLevel(logging.DEBUG)
        llm_interface.set_log_level(logging.DEBUG)
        # Add additional trace handling if needed

    if verbose != LogLevel.NONE:
        typer.echo(f"Verbosity level set to: {verbose.value}")

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
    template: str = typer.Option(
        None,
        "--template",
        help="Use a specific template for project initialization (e.g., nodejs_express_api)",
    ),
    description: str = typer.Option(
        None, 
        "--desc", 
        "-d", 
        help="Brief description of the project"
    ),
    use_ai: bool = typer.Option(
        None,
        "--ai/--no-ai",
        help="Whether to use AI for project scaffolding or use template directly",
    ),
    # Additional options for python_flask_api template
    api_prefix: str = typer.Option(
        None,
        "--api-prefix",
        help="The URL prefix for API endpoints (e.g., 'api', 'v1', 'api/v1')"
    ),
    resource_name: str = typer.Option(
        None,
        "--resource",
        help="The main resource name for the API (e.g., 'product', 'user', 'post')"
    ),
    author_name: str = typer.Option(
        None,
        "--author",
        help="The name of the project author"
    ),
    python_version: str = typer.Option(
        None,
        "--python-version",
        help="The Python version to use (e.g., '3.9', '3.10')"
    ),
    # Additional options for nodejs_express_api template
    node_version: str = typer.Option(
        None,
        "--node-version",
        help="The Node.js version to use (e.g., '18.x', '20.x')"
    ),
    api_base_path: str = typer.Option(
        None,
        "--api-base-path",
        help="Base path for API routes (e.g., '/api/v1')"
    ),
    main_resource_name: str = typer.Option(
        None,
        "--main-resource",
        help="Name for the primary resource in an Express API (e.g., 'item', 'user')"
    ),
):
    """
    Initialize a new project with AI-guided scaffolding or from a template.
    """
    if not all([llm_interface, project_generator, dev_rules]):
        typer.secho("Required modules not loaded. Cannot proceed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    project_details = {
        "name": name,
        "type": type,
        "language": language,
    }

    # If no description was provided, prompt for it
    if not description:
        description = typer.prompt("Project description", default="A new project")
    project_details["description"] = description
    
    # Get available templates
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    available_templates = [os.path.splitext(f)[0] for f in os.listdir(templates_dir) if f.endswith('.json')]

    typer.echo("\n--- Project Details ---")
    typer.echo(f"Project Name: {name}")
    typer.echo(f"Project Type: {type}")
    typer.echo(f"Main Language: {language}")
    typer.echo(f"Description: {description}")
    typer.echo("--------------------")

    # Template selection logic
    selected_template = None
    if template:
        # User provided template name via --template option
        if template not in available_templates:
            typer.secho(f"Template '{template}' not found. Available templates: {', '.join(available_templates)}", fg=typer.colors.RED)
            raise typer.Exit(1)
        selected_template = template
    elif not use_ai:
        # User didn't specify --ai, so check if a template should be suggested
        suggested_template = None
        
        # Simple matching logic for suggesting templates based on project type and language
        if type.lower() in ["api", "rest api"]:
            if language.lower() in ["javascript", "node", "node.js", "nodejs"]:
                suggested_template = "nodejs_express_api"
            elif language.lower() in ["python", "flask", "python flask"]:
                suggested_template = "python_flask_api"
        
        if suggested_template and suggested_template in available_templates:
            if typer.confirm(f"Use '{suggested_template}' template for your {type} project?", default=True):
                selected_template = suggested_template
            else:
                # User declined suggested template, show all available templates
                if available_templates:
                    typer.echo("\nAvailable templates:")
                    for i, tmpl in enumerate(available_templates, 1):
                        typer.echo(f"{i}. {tmpl}")
                    
                    template_choice = typer.prompt("Select template (or 0 for AI suggestions)", type=int, default=0)
                    if 1 <= template_choice <= len(available_templates):
                        selected_template = available_templates[template_choice - 1]
        elif available_templates:
            # No automatic suggestion, but templates are available - offer to choose
            use_template = typer.confirm("Use a pre-defined template for your project?", default=False)
            if use_template:
                typer.echo("\nAvailable templates:")
                for i, tmpl in enumerate(available_templates, 1):
                    typer.echo(f"{i}. {tmpl}")
                
                template_choice = typer.prompt("Select template (or 0 for AI suggestions)", type=int, default=0)
                if 1 <= template_choice <= len(available_templates):
                    selected_template = available_templates[template_choice - 1]
    
    # Determine if we should use AI customization
    use_ai_customization = use_ai is True and selected_template is not None
    use_template_only = selected_template is not None and use_ai is False
    use_ai_only = selected_template is None or (use_ai is True and selected_template is None)
    
    # Create base paths that will be used in various scenarios
    base_creation_path = str(Path.cwd())
    project_path = Path(base_creation_path) / name
    
    # Check if we should use a template (with or without AI customization) or AI only
    if selected_template:
        # Either use template with AI customization or just template
        typer.echo(f"\nCreating project from '{selected_template}' template...")
        
        # Prepare context for template substitution
        context = {
            "project_name": name,
            "project_description": description
        }
        
        # Add template-specific placeholder values
        if selected_template == "python_flask_api":
            # Prompt for required placeholders if they weren't provided via CLI options
            if not api_prefix and typer.confirm("Would you like to specify an API prefix?", default=False):
                api_prefix = typer.prompt("API prefix", default="api")
            
            if not resource_name and typer.confirm("Would you like to specify a main resource name?", default=False):
                resource_name = typer.prompt("Main resource name", default="example")
            
            if not author_name and typer.confirm("Would you like to add author information?", default=False):
                author_name = typer.prompt("Author name")
            
            if not python_version and typer.confirm("Would you like to specify a Python version?", default=False):
                python_version = typer.prompt("Python version", default="3.9")
            
            # Add values to context if provided
            if api_prefix:
                context["api_prefix"] = api_prefix
            if resource_name:
                context["resource_name"] = resource_name
            if author_name:
                context["author_name"] = author_name
            if python_version:
                context["python_version"] = python_version
        
        elif selected_template == "nodejs_express_api":
            # Prompt for required placeholders if they weren't provided via CLI options
            if not api_base_path and typer.confirm("Would you like to specify an API base path?", default=False):
                api_base_path = typer.prompt("API base path", default="/api")
            
            if not main_resource_name and typer.confirm("Would you like to specify a main resource name?", default=False):
                main_resource_name = typer.prompt("Main resource name", default="example")
            
            if not author_name and typer.confirm("Would you like to add author information?", default=False):
                author_name = typer.prompt("Author name")
            
            if not node_version and typer.confirm("Would you like to specify a Node.js version?", default=False):
                node_version = typer.prompt("Node.js version", default="18.x")
            
            # Add values to context if provided
            if api_base_path:
                context["api_base_path"] = api_base_path
            if main_resource_name:
                context["main_resource_name"] = main_resource_name
            if author_name:
                context["author_name"] = author_name
            if node_version:
                context["node_version"] = node_version
        
        try:
            # If AI customization is requested, use the template as a basis and enhance it
            if use_ai_customization:
                # Get the template data
                template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
                template_path = os.path.join(template_dir, f"{selected_template}.json")
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # More detailed information about the process
                typer.secho("\n--- AI Template Customization ---", fg=typer.colors.CYAN)
                typer.echo(f"Using template '{selected_template}' as a base")
                typer.echo(f"Customizing for: {description}")
                
                # For enhanced AI customization of templates
                ai_customization_description = ""
                if selected_template == "python_flask_api":
                    ai_customization_description = typer.prompt(
                        "\nDescribe any specific features or changes for this Flask API",
                        default="",
                        type=str
                    )
                elif selected_template == "nodejs_express_api":
                    ai_customization_description = typer.prompt(
                        "\nDescribe any specific features or changes for this Express API",
                        default="",
                        type=str
                    )
                
                # Update project details with AI customization description and template-specific parameters
                project_details["ai_customization_description"] = ai_customization_description
                project_details.update(context)  # Include all context values in project_details
                
                typer.echo("Requesting AI to customize the template for your specific needs...")
                
                # Get customized suggestions from LLM using the template as a base
                if ai_customization_description:
                    # Use the enhanced AI customization function
                    suggestions = llm_interface.get_ai_customized_template(
                        project_details, 
                        template_data
                    )
                else:
                    # Use the regular template customization function
                    suggestions = llm_interface.get_template_customization(
                        project_details, 
                        template_data
                    )
                
                if suggestions.get("error"):
                    typer.secho(f"Error getting AI customization: {suggestions['error']}", fg=typer.colors.RED)
                    
                    # Show the raw response if available for debugging
                    if "raw_response" in suggestions:
                        if typer.confirm("Would you like to see the raw LLM response for debugging?", default=False):
                            typer.echo("\nRaw LLM Response:")
                            typer.echo(suggestions["raw_response"])
                    
                    typer.echo("\nFalling back to using the template directly...")
                    
                    # Confirm template use
                    if not typer.confirm(f"\nProceed to create '{name}' using the '{selected_template}' template without AI customization?", default=True):
                        typer.echo("Project creation cancelled by user.")
                        raise typer.Exit()
                        
                    # Fall back to using the template directly
                    project_generator.create_project_from_template(
                        base_path=base_creation_path,
                        project_name=name,
                        template_name=selected_template,
                        context=context
                    )
                else:
                    typer.secho("\n✅ AI has successfully customized the template!", fg=typer.colors.GREEN)
                    
                    # Show a summary of the customization
                    typer.echo("\nCustomization Summary:")
                    
                    # Count directories and files
                    if "directory_structure" in suggestions:
                        typer.echo(f"- {len(suggestions['directory_structure'])} directories")
                    if "files_to_create" in suggestions:
                        typer.echo(f"- {len(suggestions['files_to_create'])} files")
                        
                        # Show a few sample files that were created or modified
                        sample_files = list(suggestions['files_to_create'].keys())[:3]
                        if sample_files:
                            typer.echo("\nSample files:")
                            for file in sample_files:
                                typer.echo(f"  - {file}")
                    
                    # Debug the structure to help diagnose issues
                    typer.secho("\nDEBUG: Suggestions Structure", fg=typer.colors.MAGENTA)
                    typer.echo(f"Type: {type(suggestions)}")
                    if isinstance(suggestions, dict):
                        typer.echo(f"Keys: {list(suggestions.keys())}")
                    else:
                        typer.echo(f"Non-dictionary type: {suggestions}")
                    
                    # Check for proper structure
                    if isinstance(suggestions, dict) and ("directory_structure" not in suggestions or "files_to_create" not in suggestions):
                        typer.secho("\nWARNING: The AI output doesn't have the expected structure.", fg=typer.colors.YELLOW)
                        typer.echo("Attempting to convert to the correct format...")
                        
                        # Try to convert from new format to old format if needed
                        if "files" in suggestions and "directories" in suggestions:
                            typer.echo("Converting from new format to old format...")
                            
                            # Convert to old format
                            directory_structure = []
                            files_to_create = {}
                            
                            # Process files
                            for file_info in suggestions.get("files", []):
                                if isinstance(file_info, dict) and "path" in file_info and "content" in file_info:
                                    files_to_create[file_info["path"]] = file_info["content"]
                            
                            # Process directories
                            for dir_info in suggestions.get("directories", []):
                                if isinstance(dir_info, dict) and "path" in dir_info:
                                    directory_structure.append(dir_info["path"])
                                    
                                    # Process files in this directory
                                    if "files" in dir_info:
                                        for file_info in dir_info["files"]:
                                            if isinstance(file_info, dict) and "path" in file_info and "content" in file_info:
                                                full_path = os.path.join(dir_info["path"], file_info["path"])
                                                files_to_create[full_path] = file_info["content"]
                            
                            # Update suggestions
                            suggestions = {
                                "directory_structure": directory_structure,
                                "files_to_create": files_to_create
                            }
                            
                            typer.secho("Conversion complete!", fg=typer.colors.GREEN)
                    
                    typer.echo("--------------------------------")
                    
                    if typer.confirm("\nUse the AI-customized template?", default=True):
                        # Use the customized structure
                        project_generator.create_project_structure(
                            base_path=base_creation_path,
                            project_name=name,
                            structure_suggestions=suggestions
                        )
                    else:
                        # Confirm template use
                        if not typer.confirm(f"\nProceed to create '{name}' using the '{selected_template}' template without customization?", default=True):
                            typer.echo("Project creation cancelled by user.")
                            raise typer.Exit()
                            
                        # Fall back to using the template directly
                        project_generator.create_project_from_template(
                            base_path=base_creation_path,
                            project_name=name,
                            template_name=selected_template,
                            context=context
                        )
            else:
                # Use the template directly without AI customization
                if not typer.confirm(f"\nProceed to create '{name}' using the '{selected_template}' template?", default=True):
                    typer.echo("Project creation cancelled by user.")
                    raise typer.Exit()
                    
                # Create project structure
                project_generator.create_project_from_template(
                    base_path=base_creation_path,
                    project_name=name,
                    template_name=selected_template,
                    context=context
                )
            
            # Setup development environment
            typer.echo("\nSetting up development environment...")
            success, message = dev_rules.dev_rules.setup_dev_environment(str(project_path))
            if not success:
                typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)
            
            # Install development dependencies
            typer.echo("\nInstalling development dependencies...")
            success, message = dev_rules.dev_rules.install_dev_dependencies(str(project_path))
            if not success:
                typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)
            
            # Setup development tools
            typer.echo("\nConfiguring development tools...")
            success, message = dev_rules.dev_rules.setup_dev_tools(str(project_path))
            if not success:
                typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)
            
            # Initialize git repository if requested
            if typer.confirm("\nWould you like to initialize a Git repository?", default=True):
                success, message = dev_rules.dev_rules.setup_git_hooks(str(project_path))
                if not success:
                    typer.secho(f"Error setting up Git: {message}", fg=typer.colors.RED)
                else:
                    typer.secho("Git repository initialized successfully!", fg=typer.colors.GREEN)
            
            typer.secho(f"\n✨ Project {name} initialized successfully from '{selected_template}' template!", fg=typer.colors.GREEN)
            typer.echo("\nNext steps:")
            typer.echo(f"  1. cd {name}")
            if language.lower() in ["javascript", "node", "node.js", "nodejs"]:
                typer.echo(f"  2. npm install")
                typer.echo(f"  3. npm run dev")
            else:
                typer.echo(f"  2. Activate virtual environment:")
                typer.echo(f"     - Windows: .\\venv\\Scripts\\activate")
                typer.echo(f"     - Unix: source venv/bin/activate")
                typer.echo(f"  3. Start coding!")
                
        except Exception as e:
            typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)
            raise typer.Exit(1)
            
    else:
        # Use AI suggestions
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