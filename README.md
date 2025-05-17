# DevSpark Assistant

DevSpark Assistant is an AI-powered development environment manager and project scaffolding tool.

## Features

- **AI-Guided Project Scaffolding**: Generate project structures based on your specifications using AI
- **Pre-defined Templates**: Quickly create projects using battle-tested templates 
- **AI-Enhanced Templates**: Customize templates with AI suggestions for your specific needs
- **Cross-Platform Shell Command Execution**: Run commands consistently across Windows, macOS, and Linux
- **Development Environment Management**: Set up and configure development environments with best practices
- **Database Integration**: Generate projects with SQLAlchemy (Flask) or MongoDB (Express) integration
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
# Interactive project initialization (will offer template options or AI generation)
devspark init

# Use a template directly (no AI customization)
devspark init --name MyExpressAPI --template nodejs_express_api --no-ai

# Use a template with AI customization
devspark init --name MyExpressAPI --template nodejs_express_api --ai --desc "A RESTful API with authentication and role-based access control"

# Use AI from scratch (no template)
devspark init --name MyProject --type "web app" --lang Python --ai
```

### Available Templates

The following templates are available for use with `devspark init --template <template_name>`:

| Template Name | Description | Language | 
|---------------|-------------|----------|
| nodejs_express_api | A Node.js REST API using Express framework | JavaScript |
| python_flask_api | A Python REST API using Flask framework | Python |

### Database Integration

DevSpark Assistant supports generating projects with database integration:

```bash
# Flask with SQLAlchemy
devspark init --name MyFlaskApp --template python_flask_api --ai --desc "Add SQLAlchemy with a User model having username, email, and password fields. Include migrations." --resource "user"

# Node.js with MongoDB
devspark init --name MyNodeApp --template nodejs_express_api --ai --desc "Add MongoDB with a Product model having name, price, and description fields." --main-resource "product"
```

For detailed information about database integration features, see [DATABASE_INTEGRATION.md](DATABASE_INTEGRATION.md).

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
├── templates/           # Pre-defined project templates
│   └── nodejs_express_api.json  # Node.js Express API template
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

# Run all tests
python run_tests.py

# Or run individual tests directly
python test_template_fixes.py
python test_template_edge_cases.py
python test_template_customization.py
python test_ai_scaffolding.py
```

The test runner provides options to:
1. Run all tests
2. Run basic tests only (no LLM API calls)
3. Run a specific test file

### Adding a New Template

To add a new project template:

1. Create a JSON file in the `devspark/templates/` directory (e.g., `my_template.json`)
2. Follow the template format structure:
   ```json
   {
     "name": "template_name",
     "description": "Template description",
     "structure": {
       "files": [
         {
           "path": "file.txt",
           "content": "File content with {{project_name}} placeholders"
         }
       ],
       "directories": [
         {
           "path": "src",
           "files": [
             {
               "path": "main.js",
               "content": "// Main file for {{project_name}}"
             }
           ]
         }
       ]
     }
   }
   ```
3. Use `{{project_name}}` and `{{project_description}}` placeholders in content that should be replaced with actual values.

### Building the Package

```bash
# Install build dependencies
pip install build

# Build the package
python -m build
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 