"""
Project Generator Module
Handles project structure generation and file creation
"""

import os
import json
import re
import pathlib
from typing import Dict, Any, List
from ..utils.shell_helper import shell

def create_project_from_template(base_path: str, project_name: str, template_name: str, context: Dict[str, str]) -> None:
    """
    Creates a project structure from a template JSON file.
    
    Args:
        base_path: Base directory where the project should be created
        project_name: Name of the project (will be used as root directory name)
        template_name: Name of the template to use (without .json extension)
        context: Dictionary with values for template placeholders (e.g., {"project_name": "MyApi"})
    """
    try:
        # Get the absolute path to the templates directory
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        template_path = os.path.join(template_dir, f"{template_name}.json")
        
        # Check if template exists
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template '{template_name}' not found at {template_path}")
        
        # Load template
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # Add project_name to context if not already there
        if "project_name" not in context:
            context["project_name"] = project_name
            
        # Process template structure
        processed_structure = _process_template_structure(template_data, context)
        
        # Create project using the processed structure and pass the context
        create_project_structure(base_path, project_name, processed_structure, context)
        
        # Apply specific customizations based on context values
        if template_name == "python_flask_api":
            # Ensure the project has proper file permissions (for Unix-like systems)
            project_path = os.path.join(base_path, project_name)
            if os.name != 'nt':  # Skip on Windows
                try:
                    # Make Python files executable
                    for root, _, files in os.walk(project_path):
                        for file in files:
                            if file.endswith('.py'):
                                file_path = os.path.join(root, file)
                                os.chmod(file_path, 0o755)  # rwxr-xr-x
                except Exception as e:
                    print(f"Warning: Could not set file permissions: {e}")
        
    except Exception as e:
        raise Exception(f"Failed to create project from template: {str(e)}")

def _process_template_structure(template_data: Dict[str, Any], context: Dict[str, str]) -> Dict[str, Any]:
    """
    Process a template structure, performing placeholder substitution.
    
    Args:
        template_data: Template data loaded from JSON file
        context: Dictionary with values for template placeholders
        
    Returns:
        Processed structure ready to be used by create_project_structure
    """
    processed_structure = {}
    
    # Check if the template uses the newer structure format
    if "structure" in template_data:
        # Convert from new template format to the format expected by create_project_structure
        root_files = []
        directories = []
        
        # Process root files
        if "files" in template_data["structure"]:
            for file_info in template_data["structure"]["files"]:
                path = file_info["path"]
                content = file_info["content"]
                
                # Handle content based on file type and content type
                if path.lower() == "package.json" and isinstance(content, dict):
                    # Special handling for package.json
                    # Create a deep copy to avoid modifying the original
                    package_data = content.copy()
                    
                    # Handle description field specially
                    if "description" in package_data and "{{project_description}}" in package_data["description"]:
                        # Replace the placeholder with the actual value, properly escaped
                        description_value = context.get("project_description", "")
                        if description_value:
                            # Keep package_data as a dictionary
                            package_data["description"] = description_value
                    
                    # Process all other placeholders in the package.json
                    for key, value in package_data.items():
                        if isinstance(value, str) and "{{" in value and "}}" in value:
                            # Process placeholders
                            for context_key, context_value in context.items():
                                placeholder = f"{{{{{context_key}}}}}"
                                if context_value is None:
                                    context_value = ""
                                value = value.replace(placeholder, str(context_value))
                            
                            # Handle any remaining placeholders
                            import re
                            remaining_placeholders = re.findall(r'{{([^}]+)}}', value)
                            for placeholder in remaining_placeholders:
                                value = value.replace(f"{{{{{placeholder}}}}}", "")
                            
                            package_data[key] = value
                    
                    # Convert the processed dictionary to a pretty-printed JSON string
                    processed_content = json.dumps(package_data, indent=2, ensure_ascii=False)
                    
                elif isinstance(content, dict):
                    # Convert other dict content to string with pretty formatting
                    # First substitute placeholders in all string values
                    processed_dict = _process_dict_placeholders(content, context)
                    processed_content = json.dumps(processed_dict, indent=2, ensure_ascii=False)
                else:
                    # For regular string content
                    processed_content = _replace_placeholders(content, context)
                
                root_files.append({
                    "path": path,
                    "content": processed_content
                })
        
        # Process directories and their files
        if "directories" in template_data["structure"]:
            for dir_info in template_data["structure"]["directories"]:
                dir_path = dir_info["path"]
                dir_entry = {
                    "path": dir_path,
                    "files": []
                }
                
                # Process files in this directory
                if "files" in dir_info:
                    for file_info in dir_info["files"]:
                        file_path = file_info["path"]
                        content = file_info["content"]
                        
                        # Perform placeholder substitution in content
                        processed_content = _replace_placeholders(content, context)
                        
                        dir_entry["files"].append({
                            "path": file_path,
                            "content": processed_content
                        })
                
                directories.append(dir_entry)
        
        processed_structure = {
            "files": root_files,
            "directories": directories
        }
    else:
        # Handle old format for backward compatibility
        directory_structure = template_data.get("directory_structure", [])
        files_to_create = {}
        
        for file_path, content in template_data.get("files_to_create", {}).items():
            # Perform placeholder substitution
            processed_content = _replace_placeholders(content, context)
            files_to_create[file_path] = processed_content
        
        processed_structure = {
            "directory_structure": directory_structure,
            "files_to_create": files_to_create
        }
    
    return processed_structure

def _process_package_json(package_data: Dict[str, Any], context: Dict[str, str]) -> str:
    """
    Process package.json data, handling placeholders and ensuring valid JSON output.
    
    Args:
        package_data: Dictionary containing package.json data
        context: Dictionary mapping placeholder names to their values
        
    Returns:
        JSON string with placeholders replaced
    """
    # Create a copy to avoid modifying the original
    processed_data = package_data.copy()
    
    # Replace placeholders in all string values
    for key, value in processed_data.items():
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # This is a string with placeholders
            for context_key, context_value in context.items():
                placeholder = f"{{{{{context_key}}}}}"
                if placeholder in value:
                    if context_value is None:
                        context_value = ""
                    value = value.replace(placeholder, str(context_value))
            
            # Handle any remaining placeholders
            import re
            remaining_placeholders = re.findall(r'{{([^}]+)}}', value)
            for placeholder in remaining_placeholders:
                value = value.replace(f"{{{{{placeholder}}}}}", "")
                
            processed_data[key] = value
    
    # Return the processed data as a JSON string
    try:
        return json.dumps(processed_data, indent=2, ensure_ascii=False)
    except Exception as e:
        # Fallback: manually escape problematic characters
        for key, value in processed_data.items():
            if isinstance(value, str):
                # Manually escape quotes for JSON compatibility
                processed_data[key] = value.replace('"', '\\"')
        return json.dumps(processed_data, indent=2, ensure_ascii=False)

def _process_dict_placeholders(data: Dict[str, Any], context: Dict[str, str]) -> Dict[str, Any]:
    """
    Process placeholders in a dictionary structure recursively.
    
    Args:
        data: Dictionary to process
        context: Dictionary mapping placeholder names to their values
        
    Returns:
        Processed dictionary with placeholders replaced
    """
    result = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = _process_dict_placeholders(value, context)
        elif isinstance(value, list):
            # Process lists
            result[key] = [
                _process_dict_placeholders(item, context) if isinstance(item, dict)
                else _replace_placeholders(item, context) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            # Replace placeholders in strings
            result[key] = _replace_placeholders(value, context)
        else:
            # Keep other values unchanged
            result[key] = value
    
    return result

def _replace_placeholders(content: str, context: Dict[str, str]) -> str:
    """
    Replace placeholders in content with values from context using Jinja2 for more advanced templating.
    
    Args:
        content: String content with Jinja2-style templates including placeholders like {{placeholder}},
                 filters like {{placeholder|filter}}, and conditionals like {% if condition %}...{% endif %}
        context: Dictionary mapping placeholder names to their values
        
    Returns:
        Content with placeholders replaced by actual values and conditionals processed
    """
    if not isinstance(content, str):
        return content
    
    try:
        # Use Jinja2 for more advanced template processing
        from jinja2 import Template
        
        # Create a Jinja2 template from the content
        template = Template(content)
        
        # Render the template with the context
        result = template.render(**context)
        
        return result
    except ImportError:
        # Fallback to simple placeholder replacement if Jinja2 is not available
        result = content
        for key, value in context.items():
            if value is None:
                value = ""  # Default to empty string for None values
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        
        # Find any remaining placeholders that weren't replaced
        remaining_placeholders = re.findall(r'{{([^}]+)}}', result)
        
        # Replace remaining placeholders with empty strings
        for placeholder in remaining_placeholders:
            result = result.replace(f"{{{{{placeholder}}}}}", "")
        
        return result

def create_project_structure(base_path: str, project_name: str, structure_suggestions: Dict[str, Any], context: Dict[str, Any] = None) -> None:
    """
    Creates a project structure based on LLM suggestions.
    
    Args:
        base_path: Base directory where the project should be created
        project_name: Name of the project (will be used as root directory name)
        structure_suggestions: Dictionary containing directory structure and file content suggestions
        context: Dictionary with template values for placeholder substitution (optional)
    """
    try:
        # Ensure structure_suggestions is a dictionary
        if not isinstance(structure_suggestions, dict):
            raise ValueError("structure_suggestions must be a dictionary")
            
        # Create project root directory
        project_root = os.path.join(base_path, project_name)
        os.makedirs(project_root, exist_ok=True)
        
        # Create context dictionary if not provided or ensure project_name is included
        if context is None:
            context = {"project_name": project_name}
        else:
            # Make a copy to avoid modifying the original
            context = context.copy()
            # Ensure project_name is in context
            if "project_name" not in context:
                context["project_name"] = project_name
        
        # Handle root level files
        if "files" in structure_suggestions:
            for file_info in structure_suggestions["files"]:
                # Process file path with placeholders
                file_path_template = file_info["path"]
                file_path = _replace_placeholders(file_path_template, context)
                full_path = os.path.join(project_root, file_path)
                
                content = file_info.get("content", "")
                # Handle case where content is a list
                if isinstance(content, list):
                    content = "\n".join(content)
                
                # Process content with placeholders
                processed_content = _replace_placeholders(content, context)
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Special handling for package.json to ensure valid JSON
                if full_path.endswith("package.json") and "description" in processed_content:
                    try:
                        # Try to parse it as JSON
                        package_data = json.loads(processed_content)
                        # Write the file using json.dump directly
                        with open(full_path, "w", encoding="utf-8") as f:
                            json.dump(package_data, f, indent=2, ensure_ascii=False)
                        continue  # Skip the normal file writing
                    except json.JSONDecodeError:
                        # If it fails to parse, continue with normal file writing
                        pass
                
                # Write file content normally
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(processed_content)
        
        # Handle directories and their files
        if "directories" in structure_suggestions:
            for dir_info in structure_suggestions["directories"]:
                # Process directory path with placeholders
                dir_path_template = dir_info["path"]
                dir_path = _replace_placeholders(dir_path_template, context)
                full_dir_path = os.path.join(project_root, dir_path)
                os.makedirs(full_dir_path, exist_ok=True)
                
                # Handle files inside this directory
                if "files" in dir_info:
                    for file_info in dir_info["files"]:
                        # Process file path with placeholders
                        file_path_template = file_info["path"]
                        file_path = _replace_placeholders(file_path_template, context)
                        full_file_path = os.path.join(full_dir_path, file_path)
                        
                        content = file_info.get("content", "")
                        # Handle case where content is a list
                        if isinstance(content, list):
                            content = "\n".join(content)
                        
                        # Process content with placeholders
                        processed_content = _replace_placeholders(content, context)
                        
                        # Ensure parent directory exists (for nested files)
                        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                        
                        # Special handling for package.json to ensure valid JSON
                        if full_file_path.endswith("package.json") and "description" in processed_content:
                            try:
                                # Try to parse it as JSON
                                package_data = json.loads(processed_content)
                                # Write the file using json.dump directly
                                with open(full_file_path, "w", encoding="utf-8") as f:
                                    json.dump(package_data, f, indent=2, ensure_ascii=False)
                                continue  # Skip the normal file writing
                            except json.JSONDecodeError:
                                # If it fails to parse, continue with normal file writing
                                pass
                        
                        # Write file content normally
                        with open(full_file_path, "w", encoding="utf-8") as f:
                            f.write(processed_content)
        
        # Handle old format for backward compatibility
        if "directory_structure" in structure_suggestions:
            for dir_path_template in structure_suggestions["directory_structure"]:
                # Process directory path with placeholders
                dir_path = _replace_placeholders(dir_path_template, context)
                full_path = os.path.join(project_root, dir_path)
                os.makedirs(full_path, exist_ok=True)
        
        if "files_to_create" in structure_suggestions:
            for file_path_template, content in structure_suggestions["files_to_create"].items():
                # Process file path with placeholders
                file_path = _replace_placeholders(file_path_template, context)
                full_path = os.path.join(project_root, file_path)
                
                # Handle case where content is a list
                if isinstance(content, list):
                    content = "\n".join(content)
                
                # Process content with placeholders
                processed_content = _replace_placeholders(content, context)
                
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Special handling for package.json to ensure valid JSON
                if full_path.endswith("package.json") and "description" in processed_content:
                    try:
                        # Try to parse it as JSON
                        package_data = json.loads(processed_content)
                        # Write the file using json.dump directly
                        with open(full_path, "w", encoding="utf-8") as f:
                            json.dump(package_data, f, indent=2, ensure_ascii=False)
                        continue  # Skip the normal file writing
                    except json.JSONDecodeError:
                        # If it fails to parse, continue with normal file writing
                        pass
                
                # Write file content normally
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(processed_content)
            
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
        if shell._is_windows:
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
            if shell._is_windows:
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