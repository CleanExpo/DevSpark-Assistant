"""
Development Rules and Utilities for DevSpark Assistant
This module provides development-specific rules and utilities that leverage the shell helper
for consistent development environment setup and maintenance.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import os
import json
from .shell_helper import shell

class DevRules:
    def __init__(self):
        self.shell = shell
        
    def _read_file_content(self, file_path: str) -> Tuple[bool, str]:
        """Helper method to read file content."""
        try:
            if shell._is_powershell:
                cmd = f'Get-Content -Path "{file_path}" -Raw'
            else:
                cmd = f'cat "{file_path}"'
            
            exit_code, stdout, stderr = shell.execute_command(cmd)
            if exit_code != 0:
                return False, stderr
            return True, stdout
        except Exception as e:
            return False, str(e)

    def _merge_config_files(self, existing_content: str, new_content: str, file_type: str) -> str:
        """
        Merges existing configuration with new configuration based on file type.
        """
        if file_type == 'json':
            try:
                existing = json.loads(existing_content)
                new = json.loads(new_content)
                merged = {**existing, **new}
                return json.dumps(merged, indent=4)
            except:
                return new_content
        elif file_type == 'ini':
            # Simple section-based merge for ini files
            existing_sections = {}
            current_section = ''
            for line in existing_content.splitlines():
                if line.strip().startswith('['):
                    current_section = line
                    existing_sections[current_section] = []
                elif current_section:
                    existing_sections[current_section].append(line)

            merged_content = []
            current_section = ''
            for line in new_content.splitlines():
                if line.strip().startswith('['):
                    current_section = line
                    if current_section not in existing_sections:
                        merged_content.append(line)
                elif current_section and current_section not in existing_sections:
                    merged_content.append(line)

            return '\n'.join(merged_content + ['\n'.join(lines) for section, lines in existing_sections.items()])
        else:
            # For other file types, append new content if not already present
            new_lines = set(new_content.splitlines())
            existing_lines = set(existing_content.splitlines())
            return '\n'.join(list(existing_lines) + list(new_lines - existing_lines))

    def setup_dev_environment(self, project_path: str, force_recreate: bool = False) -> Tuple[bool, str]:
        """
        Sets up a development environment with standard configurations.
        
        Args:
            project_path: Path to the project directory
            force_recreate: If True, recreates virtual environment even if it exists
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            venv_path = os.path.join(project_path, "venv")
            
            if os.path.exists(venv_path):
                if not force_recreate:
                    return True, "Virtual environment already exists. Use force_recreate=True to recreate."
                # Remove existing venv if force_recreate
                if shell._is_windows:
                    remove_cmd = f'Remove-Item -Recurse -Force "{venv_path}"' if shell._is_powershell else f'rmdir /s /q "{venv_path}"'
                else:
                    remove_cmd = f'rm -rf "{venv_path}"'
                shell.execute_command(remove_cmd)

            # Create virtual environment
            venv_cmd = (
                'python -m venv venv' if not shell._is_powershell
                else 'python -m venv ./venv'
            )
            
            # Activate virtual environment
            activate_cmd = (
                '. venv/bin/activate' if not shell._is_windows
                else '.\\venv\\Scripts\\Activate.ps1' if shell._is_powershell
                else '.\\venv\\Scripts\\activate.bat'
            )
            
            # Chain commands
            commands = [
                f"cd {project_path}",
                venv_cmd,
                activate_cmd,
                "python -m pip install --upgrade pip",
                "pip install -r requirements.txt"
            ]
            
            cmd = shell.join_commands(commands)
            exit_code, stdout, stderr = shell.execute_command(cmd)
            
            if exit_code != 0:
                return False, f"Environment setup failed: {stderr}"
                
            return True, "Development environment setup successfully"
            
        except Exception as e:
            return False, f"Failed to setup development environment: {str(e)}"

    def run_dev_checks(self, project_path: str) -> List[Dict[str, str]]:
        """
        Runs development environment checks and returns findings.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            List of findings with type and message
        """
        findings = []
        
        # Check Python version
        cmd = "python --version"
        exit_code, stdout, stderr = shell.execute_command(cmd)
        if exit_code == 0:
            findings.append({
                "type": "info",
                "message": f"Python version: {stdout.strip()}"
            })
        else:
            findings.append({
                "type": "error",
                "message": "Could not determine Python version"
            })

        # Check virtual environment
        venv_path = os.path.join(project_path, "venv")
        if not os.path.exists(venv_path):
            findings.append({
                "type": "warning",
                "message": "Virtual environment not found. Run setup_dev_environment()"
            })

        # Check git configuration
        git_cmd = "git config --list"
        exit_code, stdout, stderr = shell.execute_command(git_cmd)
        if exit_code != 0:
            findings.append({
                "type": "warning",
                "message": "Git configuration not found or incomplete"
            })

        # Check requirements.txt
        req_path = os.path.join(project_path, "requirements.txt")
        if not os.path.exists(req_path):
            findings.append({
                "type": "error",
                "message": "requirements.txt not found"
            })

        return findings

    def setup_git_hooks(self, project_path: str) -> Tuple[bool, str]:
        """
        Sets up Git hooks for development workflow.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            hooks_dir = os.path.join(project_path, ".git", "hooks")
            
            # Create pre-commit hook
            pre_commit_content = """#!/bin/sh
# Run tests before commit
python -m pytest
if [ $? -ne 0 ]; then
    echo "Tests must pass before commit!"
    exit 1
fi

# Run linting
flake8 .
if [ $? -ne 0 ]; then
    echo "Code must pass linting before commit!"
    exit 1
fi
"""
            
            # Create pre-push hook
            pre_push_content = """#!/bin/sh
# Run full test suite before push
python -m pytest --cov=devspark
if [ $? -ne 0 ]; then
    echo "Full test suite must pass before push!"
    exit 1
fi
"""
            
            # Write hooks using shell commands
            if shell._is_powershell:
                write_cmd = f"""
                Set-Content -Path "{os.path.join(hooks_dir, 'pre-commit')}" -Value @"
                {pre_commit_content}
                "@
                
                Set-Content -Path "{os.path.join(hooks_dir, 'pre-push')}" -Value @"
                {pre_push_content}
                "@
                """
            else:
                write_cmd = f"""
                echo '{pre_commit_content}' > "{os.path.join(hooks_dir, 'pre-commit')}"
                echo '{pre_push_content}' > "{os.path.join(hooks_dir, 'pre-push')}"
                """
            
            exit_code, stdout, stderr = shell.execute_command(write_cmd)
            
            if exit_code != 0:
                return False, f"Failed to create Git hooks: {stderr}"
            
            # Make hooks executable (Unix-like systems only)
            if not shell._is_windows:
                chmod_cmd = f"""
                chmod +x "{os.path.join(hooks_dir, 'pre-commit')}"
                chmod +x "{os.path.join(hooks_dir, 'pre-push')}"
                """
                shell.execute_command(chmod_cmd)
            
            return True, "Git hooks setup successfully"
            
        except Exception as e:
            return False, f"Failed to setup Git hooks: {str(e)}"

    def create_dev_config(self, project_path: str, config: Dict, merge_existing: bool = True) -> Tuple[bool, str]:
        """
        Creates or updates development configuration file.
        
        Args:
            project_path: Path to the project directory
            config: Dictionary containing configuration
            merge_existing: If True, merges with existing config instead of overwriting
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            config_path = os.path.join(project_path, "dev_config.json")
            
            if os.path.exists(config_path) and merge_existing:
                success, content = self._read_file_content(config_path)
                if success:
                    try:
                        existing_config = json.loads(content)
                        dev_config = {**existing_config, **config}  # Merge existing with new
                    except json.JSONDecodeError:
                        return False, "Failed to parse existing config file"
                else:
                    return False, f"Failed to read existing config: {content}"
            else:
                dev_config = {
                    "development_mode": True,
                    "debug_level": "DEBUG",
                    "auto_reload": True,
                    "test_database": "sqlite:///test.db",
                    "mock_services": True,
                    **config
                }
            
            # Write config using shell commands
            if shell._is_powershell:
                write_cmd = f"""
                $config = '{json.dumps(dev_config, indent=4)}'
                Set-Content -Path "{config_path}" -Value $config
                """
            else:
                write_cmd = f"""
                echo '{json.dumps(dev_config, indent=4)}' > "{config_path}"
                """
            
            exit_code, stdout, stderr = shell.execute_command(write_cmd)
            
            if exit_code != 0:
                return False, f"Failed to create development config: {stderr}"
                
            return True, "Development configuration updated successfully"
            
        except Exception as e:
            return False, f"Failed to create/update development config: {str(e)}"

    def install_dev_dependencies(self, project_path: str, update_existing: bool = True) -> Tuple[bool, str]:
        """
        Installs or updates development dependencies.
        
        Args:
            project_path: Path to the project directory
            update_existing: If True, updates existing packages
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            dev_packages = [
                "pytest",
                "pytest-cov",
                "flake8",
                "black",
                "mypy",
                "isort",
                "pre-commit"
            ]
            
            # Check existing packages
            if update_existing:
                cmd = "pip list --format=json"
                exit_code, stdout, stderr = shell.execute_command(cmd)
                if exit_code == 0:
                    try:
                        installed = {pkg['name'].lower(): pkg['version'] for pkg in json.loads(stdout)}
                        to_update = [pkg for pkg in dev_packages if pkg.lower() in installed]
                        to_install = [pkg for pkg in dev_packages if pkg.lower() not in installed]
                        
                        if to_update:
                            update_cmd = f"pip install --upgrade {' '.join(to_update)}"
                            commands = [
                                f"cd {project_path}",
                                update_cmd
                            ]
                            cmd = shell.join_commands(commands)
                            shell.execute_command(cmd)
                        
                        if to_install:
                            install_cmd = f"pip install {' '.join(to_install)}"
                            commands = [
                                f"cd {project_path}",
                                install_cmd
                            ]
                            cmd = shell.join_commands(commands)
                            shell.execute_command(cmd)
                    except json.JSONDecodeError:
                        # Fall back to regular install if pip list fails
                        install_cmd = f"pip install {'--upgrade ' if update_existing else ''}{' '.join(dev_packages)}"
                        commands = [
                            f"cd {project_path}",
                            install_cmd
                        ]
                        cmd = shell.join_commands(commands)
                        shell.execute_command(cmd)
            else:
                # Regular install without updating
                install_cmd = f"pip install {' '.join(dev_packages)}"
                commands = [
                    f"cd {project_path}",
                    install_cmd
                ]
                cmd = shell.join_commands(commands)
                shell.execute_command(cmd)
            
            # Update dev-requirements.txt
            commands = [
                f"cd {project_path}",
                "pip freeze > dev-requirements.txt"
            ]
            cmd = shell.join_commands(commands)
            exit_code, stdout, stderr = shell.execute_command(cmd)
            
            if exit_code != 0:
                return False, f"Failed to update dev-requirements.txt: {stderr}"
                
            return True, "Development dependencies installed/updated successfully"
            
        except Exception as e:
            return False, f"Failed to install/update development dependencies: {str(e)}"

    def setup_dev_tools(self, project_path: str, merge_existing: bool = True) -> Tuple[bool, str]:
        """
        Sets up development tools and configurations.
        
        Args:
            project_path: Path to the project directory
            merge_existing: If True, merges with existing configs instead of overwriting
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            configs = {
                ".flake8": ("ini", """[flake8]
max-line-length = 88
extend-ignore = E203
exclude = .git,__pycache__,build,dist
"""),
                "pyproject.toml": ("toml", """[tool.black]
line-length = 88
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
"""),
                "mypy.ini": ("ini", """[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
""")
            }
            
            for filename, (file_type, content) in configs.items():
                file_path = os.path.join(project_path, filename)
                
                if os.path.exists(file_path) and merge_existing:
                    success, existing_content = self._read_file_content(file_path)
                    if success:
                        content = self._merge_config_files(existing_content, content, file_type)
                
                if shell._is_powershell:
                    write_cmd = f"""
                    Set-Content -Path "{file_path}" -Value @"
                    {content}
                    "@
                    """
                else:
                    write_cmd = f"""
                    echo '{content}' > "{file_path}"
                    """
                
                exit_code, stdout, stderr = shell.execute_command(write_cmd)
                
                if exit_code != 0:
                    return False, f"Failed to create/update {filename}: {stderr}"
            
            return True, "Development tools configured successfully"
            
        except Exception as e:
            return False, f"Failed to setup development tools: {str(e)}"

# Create a global instance for easy access
dev_rules = DevRules() 