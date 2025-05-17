"""
Module for checking configurations and project health.

This module will handle:
- Performing simple local checks (e.g., .env file existence).
- Identifying key configuration files in a project.
- Preparing data/content to be sent to the LLM for review via llm_interface.
"""

import os
import pathlib
import typer # Using typer here for echo, in a real app might use logging or pass callbacks

# from . import llm_interface # We'll import this when we use it

def perform_local_checks(project_dir_path: str) -> list:
    """
    Performs a series of predefined local checks on the project directory.

    Args:
        project_dir_path (str): The path to the project directory.

    Returns:
        list: A list of strings, where each string is a finding or suggestion.
    """
    findings = []
    project_path = pathlib.Path(project_dir_path)

    typer.echo(f"Performing local checks in: {project_path.resolve()}")

    # Check 1: .env file if .env.example exists
    env_example_file = project_path / ".env.example"
    env_file = project_path / ".env"
    if env_example_file.exists():
        if not env_file.exists():
            findings.append(
                "Suggestion: '.env.example' exists but '.env' file is missing. "
                "Consider creating a .env file for your local environment variables."
            )
        else:
            findings.append("Info: '.env' file found.")
    else:
        findings.append("Info: No '.env.example' file found, skipping .env check.")

    # Check 2: requirements.txt existence (if it's a Python project - needs context)
    # For now, just a placeholder check
    req_file = project_path / "requirements.txt"
    if req_file.exists():
        findings.append(f"Info: 'requirements.txt' found. Size: {req_file.stat().st_size} bytes.")
    else:
        # This might be okay if it's not a Python project or uses other dependency mgmt
        findings.append("Info: 'requirements.txt' not found.")


    # Check 3: Check for a .git directory (is it a git repo?)
    git_dir = project_path / ".git"
    if git_dir.is_dir():
        findings.append("Info: Project appears to be a Git repository.")
    else:
        findings.append("Suggestion: Project does not appear to be a Git repository. Consider 'git init'.")

    # --- TODO: Add more local checks ---
    # - Check for README.md
    # - Check for LICENSE file
    # - Check common config files for basic syntax (e.g., JSON, YAML - using libraries)
    # - Check for common directories like 'tests', 'docs' etc.

    if not findings:
        findings.append("No specific issues or suggestions from basic local checks.")

    return findings


def review_specific_file_with_llm(file_path_str: str):
    """
    Reads a specific file and sends its content to the LLM for review.
    (This function will primarily call the llm_interface module).
    """
    file_path = pathlib.Path(file_path_str)
    if not file_path.is_file():
        typer.secho(f"Error: File not found at '{file_path_str}'", fg=typer.colors.RED)
        return

    typer.echo(f"Preparing to review file: {file_path.name} with LLM...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        typer.secho(f"Error reading file '{file_path_str}': {e}", fg=typer.colors.RED)
        return

    file_type = file_path.suffix.lstrip('.') if file_path.suffix else "unknown"
    if file_path.name.lower() == "dockerfile": # More specific type for Dockerfile
        file_type = "Dockerfile"

    # --- TODO: Integrate with llm_interface ---
    # from . import llm_interface # Make sure this import works relative to 'core'
    # review = llm_interface.review_config_file(content, file_type=file_type)
    # typer.echo("\n--- LLM Review ---")
    # # Process and print the review nicely
    # if review.get("error"):
    #     typer.secho(f"LLM Review Error: {review['error']}", fg=typer.colors.RED)
    # else:
    #     typer.secho("Summary:", bold=True)
    #     typer.echo(review.get("review_summary", "No summary provided."))
    #     if review.get("suggestions"):
    #         typer.secho("\nSuggestions:", bold=True)
    #         for sug in review["suggestions"]:
    #             typer.echo(f"- {sug}")
    #     if review.get("issues_found"):
    #         typer.secho("\nPotential Issues Found:", bold=True, fg=typer.colors.YELLOW)
    #         for issue in review["issues_found"]:
    #             typer.echo(f"- {issue}")
    # --- End of TODO ---

    typer.secho(
        f"\nLLM review for '{file_path.name}' not yet fully implemented in config_checker.",
        fg=typer.colors.YELLOW
    )
    typer.echo(f"File content (first 100 chars): '{content[:100]}...'") # For demonstration
    typer.echo(f"Detected file type: {file_type}")


if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print("Testing config_checker module...")

    # Create a dummy project structure for testing local checks
    test_project_dir = pathlib.Path(".") / "temp_test_project_for_checker"
    test_project_dir.mkdir(exist_ok=True)
    (test_project_dir / ".env.example").write_text("EXAMPLE_KEY=example_value")
    (test_project_dir / "requirements.txt").write_text("flask>=2.0")
    (test_project_dir / "README.md").write_text("# Test Project")


    typer.echo("\n--- Testing Local Checks ---")
    local_findings = perform_local_checks(str(test_project_dir))
    for finding in local_findings:
        if "Suggestion:" in finding:
            typer.secho(finding, fg=typer.colors.YELLOW)
        elif "Error:" in finding:
            typer.secho(finding, fg=typer.colors.RED)
        else:
            typer.echo(finding)

    typer.echo("\n--- Testing Specific File Review (Placeholder) ---")
    # This will use the placeholder from llm_interface if not fully implemented there
    review_specific_file_with_llm(str(test_project_dir / "README.md"))

    # Cleanup dummy directory (optional)
    # import shutil
    # shutil.rmtree(test_project_dir)
    # print(f"\nCleaned up {test_project_dir}")