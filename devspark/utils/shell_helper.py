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
        # Set Windows platform flag
        self._is_windows = self._system == 'windows'
        # Shell-specific flags
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
                # File Operations
                'create_dir': 'New-Item -ItemType Directory -Path',
                'remove_dir': 'Remove-Item -Recurse -Force',
                'copy': 'Copy-Item',
                'move': 'Move-Item',
                'rename': 'Rename-Item',
                'list_dir': 'Get-ChildItem',
                'read_file': 'Get-Content',
                'write_file': 'Set-Content',
                'append_file': 'Add-Content',
                'find_files': 'Get-ChildItem -Recurse -Filter',
                'file_exists': 'Test-Path',
                
                # Process Management
                'list_processes': 'Get-Process',
                'kill_process': 'Stop-Process -Id',
                'start_process': 'Start-Process',
                'background_job': 'Start-Job -ScriptBlock { }',
                
                # Environment and System
                'set_env': '$env:VARIABLE="value"',
                'get_env': '$env:VARIABLE',
                'current_dir': '$PWD',
                'change_dir': 'Set-Location',
                'system_info': 'Get-ComputerInfo',
                
                # Network
                'test_connection': 'Test-NetConnection',
                'get_ip': 'Get-NetIPAddress',
                'download_file': 'Invoke-WebRequest -Uri',
                
                # Redirections and Pipes
                'pipe': '|',
                'null_redirect': '$null',
                'error_redirect': '2>&1',
                'output_redirect': '>',
                'append_redirect': '>>',
                
                # Compression
                'compress': 'Compress-Archive -Path',
                'extract': 'Expand-Archive -Path',
                
                # String Operations
                'grep': 'Select-String -Pattern',
                'replace_text': '($content -replace "old", "new")',
                
                # Git Specific
                'git_init': 'git init',
                'git_clone': 'git clone',
                'git_add': 'git add',
                'git_commit': 'git commit -m'
            }
        elif self._is_cmd:
            return {
                # File Operations
                'create_dir': 'mkdir',
                'remove_dir': 'rmdir /s /q',
                'copy': 'copy',
                'move': 'move',
                'rename': 'ren',
                'list_dir': 'dir',
                'read_file': 'type',
                'write_file': 'echo content >',
                'append_file': 'echo content >>',
                'find_files': 'dir /s /b',
                'file_exists': 'if exist',
                
                # Process Management
                'list_processes': 'tasklist',
                'kill_process': 'taskkill /PID',
                'start_process': 'start',
                'background_job': 'start /b',
                
                # Environment and System
                'set_env': 'set VARIABLE=value',
                'get_env': 'echo %VARIABLE%',
                'current_dir': 'cd',
                'change_dir': 'cd',
                'system_info': 'systeminfo',
                
                # Network
                'test_connection': 'ping',
                'get_ip': 'ipconfig',
                'download_file': 'curl -O',
                
                # Redirections and Pipes
                'pipe': '|',
                'null_redirect': 'NUL',
                'error_redirect': '2>&1',
                'output_redirect': '>',
                'append_redirect': '>>',
                
                # Compression
                'compress': 'compact /c',
                'extract': 'expand',
                
                # String Operations
                'grep': 'findstr',
                'replace_text': 'for /f "tokens=*" %i in (file) do (echo %i | findstr /v "old" || echo %i | sed "s/old/new/")',
                
                # Git Specific
                'git_init': 'git init',
                'git_clone': 'git clone',
                'git_add': 'git add',
                'git_commit': 'git commit -m'
            }
        else:
            return {
                # File Operations
                'create_dir': 'mkdir -p',
                'remove_dir': 'rm -rf',
                'copy': 'cp',
                'move': 'mv',
                'rename': 'mv',
                'list_dir': 'ls',
                'read_file': 'cat',
                'write_file': 'echo content >',
                'append_file': 'echo content >>',
                'find_files': 'find . -name',
                'file_exists': 'test -f',
                
                # Process Management
                'list_processes': 'ps aux',
                'kill_process': 'kill',
                'start_process': 'nohup',
                'background_job': '&',
                
                # Environment and System
                'set_env': 'export VARIABLE=value',
                'get_env': 'echo $VARIABLE',
                'current_dir': 'pwd',
                'change_dir': 'cd',
                'system_info': 'uname -a',
                
                # Network
                'test_connection': 'ping -c 4',
                'get_ip': 'ip addr',
                'download_file': 'wget',
                
                # Redirections and Pipes
                'pipe': '|',
                'null_redirect': '/dev/null',
                'error_redirect': '2>&1',
                'output_redirect': '>',
                'append_redirect': '>>',
                
                # Compression
                'compress': 'tar -czf',
                'extract': 'tar -xzf',
                
                # String Operations
                'grep': 'grep',
                'replace_text': "sed 's/old/new/g'",
                
                # Git Specific
                'git_init': 'git init',
                'git_clone': 'git clone',
                'git_add': 'git add',
                'git_commit': 'git commit -m'
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