"""
Shell Helper Utilities for Cross-Platform Command Execution
"""
import os
import platform
import subprocess
from typing import List, Optional

class ShellHelper:
    def __init__(self):
        self._system = platform.system().lower()
        self._shell = os.environ.get('SHELL', '')
        if self._system == 'windows':
            self._shell = os.environ.get('COMSPEC', 'cmd.exe')
        self._is_powershell = 'powershell' in self._shell.lower()
        self._is_cmd = 'cmd' in self._shell.lower()
        self._is_bash = 'bash' in self._shell.lower() or 'sh' in self._shell.lower()

    @property
    def command_separator(self) -> str:
        """Get the appropriate command separator for the current shell."""
        if self._is_powershell:
            return '; '  # PowerShell uses semicolon
        elif self._is_cmd:
            return '& '  # CMD uses &
        else:
            return ' && '  # Bash and others use &&

    @property
    def line_continuation(self) -> str:
        """Get the appropriate line continuation character for the current shell."""
        if self._is_powershell:
            return '`'  # PowerShell uses backtick
        elif self._is_cmd:
            return '^'  # CMD uses caret
        else:
            return '\\'  # Bash and others use backslash

    def join_commands(self, commands: List[str]) -> str:
        """Join multiple commands using the appropriate separator."""
        return self.command_separator.join(cmd.strip() for cmd in commands if cmd.strip())

    def wrap_command(self, command: str) -> str:
        """Wrap a command appropriately for the current shell."""
        if self._is_powershell:
            # For PowerShell, we might need to handle certain commands differently
            if 'git' in command:
                return command  # Git commands work as-is
            if '|' in command:
                # PowerShell uses different pipeline syntax
                return command.replace('|', ' | ')
            return command
        return command

    def execute_command(self, command: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
        """Execute a command in the appropriate shell and return exit code, stdout, and stderr."""
        try:
            if self._is_powershell:
                shell_cmd = ['powershell', '-Command', command]
            elif self._is_cmd:
                shell_cmd = ['cmd', '/c', command]
            else:
                shell_cmd = ['/bin/bash', '-c', command]

            process = subprocess.Popen(
                shell_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True
            )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        except Exception as e:
            return 1, '', str(e)

    def get_example_commands(self) -> dict[str, str]:
        """Get example commands for the current shell."""
        if self._is_powershell:
            return {
                'create_dir': 'New-Item -ItemType Directory -Path',
                'remove_dir': 'Remove-Item -Recurse -Force',
                'copy': 'Copy-Item',
                'move': 'Move-Item',
                'set_env': '$env:VARIABLE="value"',
                'pipe': '|',
                'null_redirect': '$null',
            }
        elif self._is_cmd:
            return {
                'create_dir': 'mkdir',
                'remove_dir': 'rmdir /s /q',
                'copy': 'copy',
                'move': 'move',
                'set_env': 'set VARIABLE=value',
                'pipe': '|',
                'null_redirect': 'NUL',
            }
        else:
            return {
                'create_dir': 'mkdir -p',
                'remove_dir': 'rm -rf',
                'copy': 'cp',
                'move': 'mv',
                'set_env': 'export VARIABLE=value',
                'pipe': '|',
                'null_redirect': '/dev/null',
            }

# Create a global instance for easy access
shell = ShellHelper()

# Example usage:
if __name__ == '__main__':
    # Test the shell helper
    print(f"Current shell: {shell._shell}")
    print(f"Command separator: '{shell.command_separator}'")
    print(f"Line continuation: '{shell.line_continuation}'")
    
    # Test command joining
    commands = [
        "cd /path/to/dir",
        "git init",
        "git add .",
    ]
    print("\nJoined commands:")
    print(shell.join_commands(commands))
    
    # Test command execution
    print("\nExecuting 'pwd' command:")
    exit_code, stdout, stderr = shell.execute_command("pwd" if not shell._is_powershell else "pwd | Select-Object")
    print(f"Exit code: {exit_code}")
    print(f"Stdout: {stdout}")
    print(f"Stderr: {stderr}")
    
    # Show shell-specific commands
    print("\nShell-specific commands:")
    for cmd, example in shell.get_example_commands().items():
        print(f"{cmd}: {example}") 