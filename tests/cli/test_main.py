"""
Tests for the CLI main module
"""
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import the Typer app from main
from devspark.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


class TestCLI:
    @patch('devspark.cli.main.llm_interface')
    @patch('devspark.cli.main.project_generator')
    @patch('devspark.cli.main.dev_rules')
    def test_init_command(self, mock_dev_rules, mock_project_generator, mock_llm, runner):
        """Test the init command with mocked dependencies"""
        # Setup mocks
        mock_llm.get_scaffolding_suggestions.return_value = {"files": [], "directories": []}
        mock_dev_rules.dev_rules.setup_dev_environment.return_value = (True, "Success")
        mock_dev_rules.dev_rules.install_dev_dependencies.return_value = (True, "Success")
        mock_dev_rules.dev_rules.setup_dev_tools.return_value = (True, "Success")
        mock_dev_rules.dev_rules.setup_git_hooks.return_value = (True, "Success")
        
        # Run command with automatic responses
        result = runner.invoke(
            app, 
            ["init", "--name", "TestProject", "--type", "web app", "--lang", "Python"],
            input="y\ny\ny\n"  # Yes to scaffolding, Yes to creating, Yes to git
        )
        
        # Check result
        assert result.exit_code == 0
        assert "Project Details" in result.stdout
        assert "TestProject" in result.stdout
        
        # Verify mock calls
        assert mock_llm.get_scaffolding_suggestions.called
        assert mock_project_generator.create_project_structure.called
        assert mock_dev_rules.dev_rules.setup_dev_environment.called

    @patch('devspark.cli.main.dev_rules')
    def test_check_command(self, mock_dev_rules, runner):
        """Test the check command with mocked dependencies"""
        # Setup mocks
        mock_dev_rules.dev_rules.run_dev_checks.return_value = [
            {"type": "info", "message": "Test info"},
            {"type": "warning", "message": "Test warning"},
            {"type": "error", "message": "Test error"}
        ]
        
        # Run command
        result = runner.invoke(app, ["check"])
        
        # Check result
        assert result.exit_code == 0
        assert "Test info" in result.stdout
        assert "Test warning" in result.stdout
        assert "Test error" in result.stdout
        
        # Verify mock calls
        assert mock_dev_rules.dev_rules.run_dev_checks.called

    @patch('devspark.cli.main.llm_interface')
    @patch('devspark.cli.main.config_checker')
    @patch('devspark.cli.main.dev_rules')
    def test_check_file_command(self, mock_dev_rules, mock_config_checker, mock_llm, runner, tmp_path):
        """Test the check command with a file parameter"""
        # Create a temporary file
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": "content"}')
        
        # Setup mocks
        mock_llm.review_config_file.return_value = {"issues": [], "suggestions": ["Test suggestion"]}
        
        # Run command
        result = runner.invoke(app, ["check", "--file", str(test_file)])
        
        # Check result
        assert result.exit_code == 0
        assert "AI Review" in result.stdout
        
        # Verify mock calls
        assert mock_llm.review_config_file.called

    @patch('devspark.cli.main.dev_rules')
    def test_config_command(self, mock_dev_rules, runner):
        """Test the config command"""
        # Setup mocks
        mock_dev_rules.dev_rules.create_dev_config.return_value = (True, "Success")
        
        # Run command
        result = runner.invoke(app, ["config", "--debug"])
        
        # Check result
        assert result.exit_code == 0
        assert "updated" in result.stdout
        
        # Verify mock calls
        assert mock_dev_rules.dev_rules.create_dev_config.called

    def test_help(self, runner):
        """Test the CLI help output"""
        result = runner.invoke(app, ["--help"])
        
        # Check help output contains expected content
        assert result.exit_code == 0
        assert "DevSpark Assistant" in result.stdout
        assert "init" in result.stdout
        assert "check" in result.stdout
        assert "config" in result.stdout 