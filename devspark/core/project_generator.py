"""
Project Generator Module
Handles project structure generation and file creation
"""

import os
import pathlib
from typing import Dict, Any, List
from ..utils.shell_helper import shell

def create_project_structure(base_path: str, project_name: str, structure_suggestions: Dict[str, Any]) -> None:
    """
    Creates a project structure based on LLM suggestions.
    
    Args:
        base_path: Base directory where the project should be created
        project_name: Name of the project (will be used as root directory name)
        structure_suggestions: Dictionary containing directory structure and file content suggestions
    """
    try:
        # Ensure structure_suggestions is a dictionary
        if not isinstance(structure_suggestions, dict):
            raise ValueError("structure_suggestions must be a dictionary")
            
        # Create project root directory
        project_root = os.path.join(base_path, project_name)
        os.makedirs(project_root, exist_ok=True)
        
        # Handle root level files
        if "files" in structure_suggestions:
            for file_info in structure_suggestions["files"]:
                file_path = os.path.join(project_root, file_info["path"])
                content = file_info.get("content", "")
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write file content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
        
        # Handle directories and their files
        if "directories" in structure_suggestions:
            for dir_info in structure_suggestions["directories"]:
                dir_path = os.path.join(project_root, dir_info["path"])
                os.makedirs(dir_path, exist_ok=True)
                
                # Handle files inside this directory
                if "files" in dir_info:
                    for file_info in dir_info["files"]:
                        file_path = os.path.join(dir_path, file_info["path"])
                        content = file_info.get("content", "")
                        
                        # Ensure parent directory exists (for nested files)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # Write file content
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
        
        # Handle old format for backward compatibility
        if "directory_structure" in structure_suggestions:
            for dir_path in structure_suggestions["directory_structure"]:
                full_path = os.path.join(project_root, dir_path)
                os.makedirs(full_path, exist_ok=True)
        
        if "files_to_create" in structure_suggestions:
            for file_path, content in structure_suggestions["files_to_create"].items():
                full_path = os.path.join(project_root, file_path)
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Write file content
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
    except Exception as e:
        raise Exception(f"Failed to create project structure: {str(e)}")

def update_project_structure(project_path: str, structure_updates: Dict[str, Any]) -> None:
    """
    Updates an existing project structure with new files and directories.
    
    Args:
        project_path: Path to the existing project
        structure_updates: Dictionary containing new/updated structure and files
    """
    try:
        # Create new directories
        for dir_path in structure_updates.get("directory_structure", []):
            full_path = os.path.join(project_path, dir_path)
            os.makedirs(full_path, exist_ok=True)
        
        # Create/update files
        for file_path, content in structure_updates.get("files_to_create", {}).items():
            full_path = os.path.join(project_path, file_path)
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Check if file exists and should be updated
            if os.path.exists(full_path):
                # Read existing content
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                
                if existing_content.strip() == content.strip():
                    continue  # Skip if content is the same
            
            # Write/update file content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            
    except Exception as e:
        raise Exception(f"Failed to update project structure: {str(e)}")

def generate_gitignore(project_path: str, language: str) -> None:
    """
    Generates a .gitignore file for the project.
    
    Args:
        project_path: Path to the project
        language: Programming language to generate gitignore for
    """
    try:
        gitignore_path = os.path.join(project_path, ".gitignore")
        
        # Common patterns for all projects
        common_patterns = [
            ".env",
            ".env.*",
            "!.env.example",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            ".Python",
            "build/",
            "develop-eggs/",
            "dist/",
            "downloads/",
            "eggs/",
            ".eggs/",
            "lib/",
            "lib64/",
            "parts/",
            "sdist/",
            "var/",
            "wheels/",
            "*.egg-info/",
            ".installed.cfg",
            "*.egg",
            "MANIFEST",
            ".env",
            ".venv",
            "env/",
            "venv/",
            "ENV/",
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            ".DS_Store"
        ]
        
        # Language-specific patterns
        language_patterns = {
            "python": [
                "*.py[cod]",
                "*$py.class",
                "*.so",
                ".Python",
                "build/",
                "develop-eggs/",
                "dist/",
                "downloads/",
                "eggs/",
                ".eggs/",
                "lib/",
                "lib64/",
                "parts/",
                "sdist/",
                "var/",
                "wheels/",
                "*.egg-info/",
                ".installed.cfg",
                "*.egg",
                "MANIFEST",
                ".coverage",
                "coverage.xml",
                "*.cover",
                ".pytest_cache/"
            ],
            "javascript": [
                "node_modules/",
                "npm-debug.log",
                "yarn-debug.log*",
                "yarn-error.log*",
                ".pnpm-debug.log*",
                ".env.local",
                ".env.development.local",
                ".env.test.local",
                ".env.production.local",
                ".next/",
                "out/",
                "build/",
                ".DS_Store",
                "*.pem",
                "coverage/",
                ".nyc_output/",
                ".grunt/",
                "bower_components/",
                ".lock-wscript",
                "build/Release",
                "*.tsbuildinfo",
                ".npm",
                ".eslintcache"
            ]
        }
        
        # Combine patterns
        patterns = common_patterns + language_patterns.get(language.lower(), [])
        content = "\n".join(patterns)
        
        # Write .gitignore file
        if shell._is_powershell:
            write_cmd = f"""
            Set-Content -Path "{gitignore_path}" -Value @"
            {content}
            "@
            """
        else:
            write_cmd = f"""
            echo '{content}' > "{gitignore_path}"
            """
        
        shell.execute_command(write_cmd)
        
    except Exception as e:
        raise Exception(f"Failed to generate .gitignore: {str(e)}")

def cleanup_project(project_path: str) -> None:
    """
    Cleans up temporary files and directories in the project.
    
    Args:
        project_path: Path to the project
    """
    try:
        # Common patterns to clean up
        patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.pyd",
            ".pytest_cache",
            ".coverage",
            "htmlcov",
            "build",
            "dist",
            "*.egg-info"
        ]
        
        for pattern in patterns:
            if shell._is_powershell:
                clean_cmd = f"""
                Get-ChildItem -Path "{project_path}" -Include {pattern} -Recurse -Force | Remove-Item -Force -Recurse
                """
            else:
                clean_cmd = f"""
                find "{project_path}" -type f -name "{pattern}" -exec rm -rf {{}} +
                """
            
            shell.execute_command(clean_cmd)
            
    except Exception as e:
        raise Exception(f"Failed to clean up project: {str(e)}")

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