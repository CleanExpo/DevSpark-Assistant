# DevSpark Assistant

DevSpark Assistant is an AI-powered development environment manager and project scaffolding tool.

## Features

- **AI-Guided Project Scaffolding**: Generate project structures based on your specifications using AI
- **Cross-Platform Shell Command Execution**: Run commands consistently across Windows, macOS, and Linux
- **Development Environment Management**: Set up and configure development environments with best practices
- **Configuration File Handling**: Create and manage configuration files for your projects
- **Git Hooks Integration**: Automate quality checks with pre-commit and pre-push hooks

## Installation

```bash
# Clone the repository
git clone https://github.com/CleanExpo/DevSpark-Assistant.git
cd DevSpark-Assistant

# Create a virtual environment
python -m venv .venv
# Activate the virtual environment
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the package in development mode
pip install -e .
```

## Usage

### Initialize a New Project

```bash
# Interactive project initialization
devspark init

# Non-interactive project initialization
devspark init --name MyProject --type "web app" --lang Python
```

### Check Development Environment

```bash
# Check the current directory
devspark check

# Check a specific configuration file
devspark check --file docker-compose.yml
```

### Configure Development Settings

```bash
# Configure development environment settings
devspark config --debug --env development
```

## Project Structure

```
devspark/
├── __init__.py          # Package initialization
├── cli/                 # Command-line interface
│   ├── __init__.py
│   ├── __main__.py      # Entry point for python -m devspark.cli
│   └── main.py          # CLI implementation with Typer
├── core/                # Core functionality
│   ├── __init__.py
│   ├── config_checker.py
│   ├── llm_interface.py
│   └── project_generator.py
└── utils/               # Utility modules
    ├── __init__.py
    ├── dev_rules.py     # Development environment management
    └── shell_helper.py  # Cross-platform shell command execution
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Building the Package

```bash
# Install build dependencies
pip install build

# Build the package
python -m build
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 