"""
Module for generating project structures and files.

This module will handle:
- Creating directories based on LLM suggestions or predefined templates.
- Creating files with content provided by LLM or from templates.
- Ensuring basic file operations are handled correctly (e.g., path joining).
"""

import os
import pathlib
import typer # Using typer here for echo, in a real app might use logging or pass callbacks

def create_project_structure(base_path: str, project_name: str, structure_suggestions: dict):
    """
    Creates the project directory structure and files based on suggestions.

    Args:
        base_path (str): The base path where the project directory will be created
                         (usually the current working directory).
        project_name (str): The name of the project (top-level project directory).
        structure_suggestions (dict): A dictionary from llm_interface containing
                                      'directory_structure' (list of paths) and
                                      'files_to_create' (dict of filepath: content).
    """
    project_root = pathlib.Path(base_path) / project_name
    typer.echo(f"Attempting to create project root at: {project_root}")

    try:
        project_root.mkdir(parents=True, exist_ok=True)
        typer.secho(f"Successfully created project directory: {project_root}", fg=typer.colors.GREEN)
    except OSError as e:
        typer.secho(f"Error creating project directory {project_root}: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Create directory structure
    suggested_dirs = structure_suggestions.get("directory_structure", [])
    for dir_path_str in suggested_dirs:
        # Ensure paths from LLM are relative to project_name or handle absolute paths if necessary
        # For now, assume dir_path_str might include the project_name itself, or be relative within it.
        # A more robust way is for LLM to provide paths *relative* to the project root.
        if project_name in dir_path_str: # If LLM included project name
             # Construct path relative to base_path if LLM gives full-like path
            full_dir_path = pathlib.Path(base_path) / dir_path_str
        else: # Assume relative to project_root
            full_dir_path = project_root / dir_path_str

        try:
            full_dir_path.mkdir(parents=True, exist_ok=True)
            typer.echo(f"  Created directory: {full_dir_path}")
        except OSError as e:
            typer.secho(f"  Error creating directory {full_dir_path}: {e}", fg=typer.colors.RED)
            # Decide if we should continue or stop

    # Create files with content
    files_to_create = structure_suggestions.get("files_to_create", {})
    for file_path_str, content in files_to_create.items():
        if project_name in file_path_str:
            full_file_path = pathlib.Path(base_path) / file_path_str
        else:
            full_file_path = project_root / file_path_str

        try:
            # Ensure parent directory for the file exists
            full_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            typer.echo(f"  Created file: {full_file_path}")
        except OSError as e:
            typer.secho(f"  Error creating file {full_file_path}: {e}", fg=typer.colors.RED)
            # Decide if we should continue or stop

    typer.secho(f"\nProject '{project_name}' structure generated successfully!", fg=typer.colors.GREEN)

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print("Testing project_generator module...")
    # Create a dummy 'test_output' directory to generate the project into
    test_output_path = pathlib.Path(".") / "test_generated_project_output"
    test_output_path.mkdir(exist_ok=True)

    sample_project_name = "MyGeneratedApp"
    sample_suggestions = {
        "directory_structure": [
            # These paths are expected to be relative to the project root, or include the project root
            # If the LLM gives "MyGeneratedApp/src", Path("MyGeneratedApp") / "src" handles it.
            # If the LLM gives "src", Path("MyGeneratedApp") / "src" handles it.
            "src",
            "src/components",
            "data",
            "tests"
        ],
        "files_to_create": {
            "README.md": f"# Welcome to {sample_project_name}\n\nThis is a sample project.",
            "src/main.py": "def main():\n    print(\"Hello from main.py\")\n\nif __name__ == \"__main__\":\n    main()",
            "src/components/__init__.py": "",
            ".gitignore": "*.pyc\n__pycache__/\n.env\nvenv/\n.venv/\n*.log\n/test_generated_project_output/\n",
            "requirements.txt": "typer>=0.9.0\npython-dotenv>=1.0.0"
        }
    }
    # We pass "." as base_path so project_name "MyGeneratedApp" is created in "test_generated_project_output"
    # The actual project will be at "test_generated_project_output/MyGeneratedApp"
    create_project_structure(str(test_output_path), sample_project_name, sample_suggestions)
    print(f"\nTest project generated in: {test_output_path / sample_project_name}")
    print("Please review the 'test_generated_project_output' directory.")
    # Consider adding a cleanup step for the test_generated_project_output directory