# DevSpark Assistant

DevSpark Assistant is a powerful CLI tool designed to streamline project initialization and maintain consistent development environments across teams. It leverages AI capabilities to generate project structures and provides robust cross-platform development environment management.

## Features

### 🚀 Project Scaffolding
- AI-powered project structure generation
- Language-specific boilerplate code
- Intelligent dependency management
- Cross-platform compatibility

### 🔧 Consistent Development Environment
- Automated environment setup and configuration
- Cross-platform shell command handling
- Virtual environment management
- Development tool configuration
- Git hooks setup and management

### 🛠️ Development Tools Integration
- Automated setup of common development tools:
  - Code formatting (Black)
  - Linting (Flake8)
  - Type checking (MyPy)
  - Import sorting (isort)
  - Testing (pytest)
  - Code coverage tracking
  - Pre-commit hooks

### 🔄 Configuration Management
- Smart configuration handling
- Environment-specific settings
- Merge capability for existing configurations
- Cross-platform compatibility

## Installation

```bash
pip install devspark-assistant
```

## Quick Start

1. Initialize a new project:
```bash
devspark init
```

2. Set up development environment:
```python
from devspark.utils.dev_rules import dev_rules

# Setup development environment
dev_rules.setup_dev_environment("/path/to/project")

# Install development dependencies
dev_rules.install_dev_dependencies("/path/to/project")

# Setup development tools
dev_rules.setup_dev_tools("/path/to/project")
```

## Development Environment Features

### Virtual Environment Management
```python
# Create or recreate virtual environment
dev_rules.setup_dev_environment(
    project_path="/path/to/project",
    force_recreate=True  # Optional: recreate if exists
)
```

### Development Tools Configuration
```python
# Setup development tools with existing config merge
dev_rules.setup_dev_tools(
    project_path="/path/to/project",
    merge_existing=True  # Preserves existing configurations
)
```

### Git Hooks Setup
```python
# Setup Git hooks for consistent code quality
dev_rules.setup_git_hooks("/path/to/project")
```

### Development Configuration
```python
# Create or update development configuration
config = {
    "development_mode": True,
    "debug_level": "DEBUG",
    "custom_setting": "value"
}
dev_rules.create_dev_config(
    project_path="/path/to/project",
    config=config,
    merge_existing=True  # Merges with existing config
)
```

## Cross-Platform Shell Support

DevSpark Assistant provides consistent command execution across different shells:

- PowerShell
- CMD
- Bash
- Other Unix shells

Example of cross-platform command execution:
```python
from devspark.utils.shell_helper import shell

# Execute commands consistently across platforms
shell.execute_command("your_command")

# Join multiple commands
commands = ["cd /path", "git init", "git add ."]
shell.join_commands(commands)
```

## Development Tools Included

- **Code Quality**
  - Black (code formatting)
  - Flake8 (linting)
  - MyPy (type checking)
  - isort (import sorting)

- **Testing**
  - pytest
  - pytest-cov (coverage reporting)

- **Git Integration**
  - pre-commit hooks
  - Automated testing before commits
  - Code quality checks before pushing

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Requirements

- Python 3.8+
- pip
- Git

## Support

For issues and feature requests, please use the GitHub issue tracker. 