"""
Module for generating project structures based on LLM suggestions.
"""

import os
import pathlib
import typer
from ..utils import shell

def create_project_structure(base_path: str, project_name: str, structure_suggestions: dict) -> None:
    """
    Creates a project structure based on the provided suggestions.

    Args:
        base_path (str): Base directory where the project should be created.
        project_name (str): Name of the project (will be used as root directory name).
        structure_suggestions (dict): Dictionary containing directory structure and file content suggestions.
    """
    try:
        # Create project root directory
        project_root = os.path.join(base_path, project_name)
        typer.echo(f"\nAttempting to create project root at: {project_root}")
        
        # Use shell helper to create directory
        exit_code, _, stderr = shell.execute_command(
            f"{shell.get_example_commands()['create_dir']} {project_root}",
            cwd=base_path
        )
        if exit_code != 0:
            typer.secho(f"Error creating project directory: {stderr}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        typer.echo(f"\nSuccessfully created project directory: {project_root}")

        # Create directory structure
        for dir_path in structure_suggestions.get("directory_structure", []):
            full_path = os.path.join(project_root, dir_path)
            try:
                os.makedirs(full_path, exist_ok=True)
                typer.echo(f"  Created directory: {full_path}")
            except Exception as e:
                typer.secho(f"Error creating directory {full_path}: {e}", fg=typer.colors.RED)
                continue

        # Create files with content
        for file_path, content in structure_suggestions.get("files_to_create", {}).items():
            full_path = os.path.join(project_root, file_path)
            try:
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Write file content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                typer.echo(f"  Created file: {full_path}")
            except Exception as e:
                typer.secho(f"Error creating file {full_path}: {e}", fg=typer.colors.RED)
                continue

        typer.echo(f"\nProject '{project_name}' structure generated successfully!")
        typer.echo(f"Project created at: {project_root}")

    except Exception as e:
        typer.secho(f"An error occurred while creating project structure: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

if __name__ == '__main__':
    # Test the module
    test_structure = {
        "directory_structure": [
            "src",
            "tests",
            "docs"
        ],
        "files_to_create": {
            "README.md": "# Test Project\nThis is a test project.",
            "src/main.py": "print('Hello World')",
            "tests/__init__.py": "",
        }
    }
    create_project_structure(".", "test_project", test_structure)