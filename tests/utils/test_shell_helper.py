"""
Tests for the shell_helper module
"""
import os
import platform
import pytest
from unittest.mock import patch, MagicMock

from devspark.utils.shell_helper import ShellHelper, shell


class TestShellHelper:
    def test_shell_instance_created(self):
        """Test that the global shell instance is created"""
        assert shell is not None
        assert isinstance(shell, ShellHelper)

    def test_detect_system(self):
        """Test system detection"""
        helper = ShellHelper()
        system = platform.system().lower()
        assert helper._system == system

    def test_command_separator(self):
        """Test command separator property"""
        helper = ShellHelper()
        if helper._is_powershell:
            assert helper.command_separator == '; '
        elif helper._is_cmd:
            assert helper.command_separator == '& '
        else:
            assert helper.command_separator == ' && '

    def test_line_continuation(self):
        """Test line continuation property"""
        helper = ShellHelper()
        if helper._is_powershell:
            assert helper.line_continuation == '`'
        elif helper._is_cmd:
            assert helper.line_continuation == '^'
        else:
            assert helper.line_continuation == '\\'

    def test_join_commands(self):
        """Test joining commands"""
        helper = ShellHelper()
        commands = ['command1', 'command2', 'command3']
        joined = helper.join_commands(commands)
        
        # The commands should be joined with the appropriate separator
        assert len(joined.split(helper.command_separator)) == 3
        assert 'command1' in joined
        assert 'command2' in joined
        assert 'command3' in joined

    def test_join_commands_handles_empty(self):
        """Test joining commands with empty items"""
        helper = ShellHelper()
        commands = ['command1', '', 'command2', '  ', 'command3']
        joined = helper.join_commands(commands)
        
        # Empty commands should be filtered out
        assert len(joined.split(helper.command_separator)) == 3

    @patch('subprocess.Popen')
    def test_execute_command(self, mock_popen):
        """Test command execution"""
        # Setup mock
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('stdout', 'stderr')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        helper = ShellHelper()
        code, stdout, stderr = helper.execute_command('test command')
        
        # Assertions
        assert code == 0
        assert stdout == 'stdout'
        assert stderr == 'stderr'
        assert mock_popen.called

    @patch('subprocess.Popen')
    def test_execute_command_error(self, mock_popen):
        """Test command execution with error"""
        # Setup mock for failure
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('', 'command not found')
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        helper = ShellHelper()
        code, stdout, stderr = helper.execute_command('invalid command')
        
        # Assertions
        assert code == 1
        assert stdout == ''
        assert stderr == 'command not found'

    def test_get_example_commands(self):
        """Test getting example commands"""
        helper = ShellHelper()
        examples = helper.get_example_commands()
        
        # Should return a dictionary of example commands
        assert isinstance(examples, dict)
        assert len(examples) > 0
        
        # Check for common commands across all shells
        assert 'create_dir' in examples
        assert 'list_dir' in examples
        assert 'git_init' in examples

    def test_wrap_command(self):
        """Test command wrapping"""
        helper = ShellHelper()
        
        # Git commands should pass through unchanged
        assert helper.wrap_command('git status') == 'git status'
        
        # PowerShell pipeline handling
        if helper._is_powershell:
            assert '|' not in helper.wrap_command('Get-Process | Select-Object Name')
            assert ' | ' in helper.wrap_command('Get-Process | Select-Object Name') 