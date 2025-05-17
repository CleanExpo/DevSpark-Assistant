"""
Tests for the dev_rules module
"""
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from devspark.utils.dev_rules import DevRules


class TestDevRules:
    @pytest.fixture
    def dev_rules(self):
        """Create a DevRules instance for testing"""
        # Mock the shell helper to avoid actual command execution
        with patch('devspark.utils.dev_rules.shell') as mock_shell:
            mock_shell._is_windows = False
            mock_shell._is_powershell = False
            mock_shell.execute_command.return_value = (0, "Success", "")
            yield DevRules()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def test_setup_dev_environment(self, dev_rules, temp_dir):
        """Test setting up a development environment"""
        # Patch exists to simulate venv not existing
        with patch('os.path.exists', return_value=False):
            success, message = dev_rules.setup_dev_environment(temp_dir)
            
            # Should succeed with our mocked shell
            assert success
            assert "successfully" in message

    def test_setup_dev_environment_existing(self, dev_rules, temp_dir):
        """Test setup when environment already exists"""
        # Patch exists to simulate venv existing
        with patch('os.path.exists', return_value=True):
            success, message = dev_rules.setup_dev_environment(temp_dir)
            
            # Should succeed but report already exists
            assert success
            assert "already exists" in message

    def test_run_dev_checks(self, dev_rules, temp_dir):
        """Test running development checks"""
        findings = dev_rules.run_dev_checks(temp_dir)
        
        # Should return a list of findings
        assert isinstance(findings, list)
        assert len(findings) > 0
        
        # Verify structure of findings
        for finding in findings:
            assert "type" in finding
            assert "message" in finding
            assert finding["type"] in ["info", "warning", "error"]

    @patch('devspark.utils.dev_rules.shell')
    def test_setup_git_hooks(self, mock_shell, temp_dir):
        """Test setting up Git hooks"""
        # Configure mock
        mock_shell._is_powershell = False
        mock_shell._is_windows = False
        mock_shell.execute_command.return_value = (0, "Success", "")
        
        dev_rules_instance = DevRules()
        success, message = dev_rules_instance.setup_git_hooks(temp_dir)
        
        # Should succeed with our mocked shell
        assert success
        assert mock_shell.execute_command.called

    def test_merge_config_files_json(self, dev_rules):
        """Test merging JSON config files"""
        existing = '{"key1": "value1", "key2": "value2"}'
        new = '{"key2": "new_value", "key3": "value3"}'
        
        merged = dev_rules._merge_config_files(existing, new, 'json')
        merged_dict = json.loads(merged)
        
        # Check merged content
        assert merged_dict["key1"] == "value1"
        assert merged_dict["key2"] == "new_value"  # New value should override
        assert merged_dict["key3"] == "value3"     # New key should be added

    def test_create_dev_config(self, dev_rules, temp_dir):
        """Test creating development config"""
        with patch('devspark.utils.dev_rules.DevRules._read_file_content', return_value=(False, "")):
            with patch('devspark.utils.dev_rules.shell.execute_command', return_value=(0, "", "")):
                config = {
                    "debug": True,
                    "environment": "development"
                }
                
                success, message = dev_rules.create_dev_config(temp_dir, config)
                
                # Should succeed with our mocked methods
                assert success

    def test_install_dev_dependencies(self, dev_rules, temp_dir):
        """Test installing development dependencies"""
        with patch('devspark.utils.dev_rules.shell.execute_command', return_value=(0, "", "")):
            success, message = dev_rules.install_dev_dependencies(temp_dir)
            
            # Should succeed with our mocked shell
            assert success

    def test_setup_dev_tools(self, dev_rules, temp_dir):
        """Test setting up development tools"""
        with patch('devspark.utils.dev_rules.shell.execute_command', return_value=(0, "", "")):
            with patch('devspark.utils.dev_rules.DevRules._read_file_content', return_value=(False, "")):
                success, message = dev_rules.setup_dev_tools(temp_dir)
                
                # Should succeed with our mocked methods
                assert success 