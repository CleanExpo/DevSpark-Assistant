"""
Tests for the project_generator module
"""
import os
import tempfile
import shutil
import json
import pytest
from pathlib import Path

from devspark.core import project_generator


class TestProjectGenerator:
    @pytest.fixture
    def test_project_details(self):
        """Test project details fixture"""
        return {
            "name": "TestProject",
            "type": "web app",
            "language": "Python"
        }

    @pytest.fixture
    def test_structure_suggestions(self):
        """Test structure suggestions fixture"""
        return {
            "files": [
                {
                    "path": "README.md",
                    "content": "# TestProject\nA simple test project"
                },
                {
                    "path": "setup.py",
                    "content": "from setuptools import setup\nsetup(name='TestProject')"
                },
                {
                    "path": "requirements.txt",
                    "content": "pytest\nblack\nflake8"
                }
            ],
            "directories": [
                {
                    "path": "src",
                    "files": [
                        {
                            "path": "__init__.py",
                            "content": ""
                        },
                        {
                            "path": "main.py",
                            "content": "def main():\n    print('Hello world')\n\nif __name__ == '__main__':\n    main()"
                        }
                    ]
                },
                {
                    "path": "tests",
                    "files": [
                        {
                            "path": "__init__.py",
                            "content": ""
                        },
                        {
                            "path": "test_main.py",
                            "content": "def test_main():\n    assert True"
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def test_create_project_structure(self, temp_dir, test_project_details, test_structure_suggestions):
        """Test project structure creation"""
        # Arrange
        project_name = test_project_details["name"]
        
        # Act
        project_generator.create_project_structure(
            base_path=temp_dir,
            project_name=project_name,
            structure_suggestions=test_structure_suggestions
        )
        
        # Assert
        project_path = Path(temp_dir) / project_name
        assert project_path.exists(), f"Project directory {project_path} should exist"
        
        # Check README.md
        readme_path = project_path / "README.md"
        assert readme_path.exists(), "README.md should exist"
        assert "# TestProject" in readme_path.read_text(), "README.md should contain project name"
        
        # Check setup.py
        setup_path = project_path / "setup.py"
        assert setup_path.exists(), "setup.py should exist"
        
        # Check src/main.py
        main_path = project_path / "src" / "main.py"
        assert main_path.exists(), "src/main.py should exist"
        assert "def main():" in main_path.read_text(), "main.py should contain main function"
        
        # Check tests/test_main.py
        test_main_path = project_path / "tests" / "test_main.py"
        assert test_main_path.exists(), "tests/test_main.py should exist"

    def test_create_nested_directories(self, temp_dir):
        """Test creation of nested directories"""
        # Arrange
        structure = {
            "directories": [
                {
                    "path": "deep/nested/structure",
                    "files": [
                        {
                            "path": "test.txt",
                            "content": "Test content"
                        }
                    ]
                }
            ]
        }
        
        # Act
        project_generator.create_project_structure(
            base_path=temp_dir,
            project_name="NestedTest",
            structure_suggestions=structure
        )
        
        # Assert
        nested_file_path = Path(temp_dir) / "NestedTest" / "deep" / "nested" / "structure" / "test.txt"
        assert nested_file_path.exists(), "Nested file should exist"
        assert "Test content" in nested_file_path.read_text(), "File should contain correct content"

    def test_handle_empty_structure(self, temp_dir):
        """Test handling of empty structure suggestions"""
        # Arrange
        empty_structure = {
            "files": [],
            "directories": []
        }
        
        # Act
        project_generator.create_project_structure(
            base_path=temp_dir,
            project_name="EmptyProject",
            structure_suggestions=empty_structure
        )
        
        # Assert
        project_path = Path(temp_dir) / "EmptyProject"
        assert project_path.exists(), "Empty project directory should be created"
        
    def test_handle_invalid_structure(self, temp_dir):
        """Test handling of invalid structure suggestions"""
        # Arrange
        invalid_structure = "Not a dictionary"
        
        # Act/Assert
        with pytest.raises(Exception):
            project_generator.create_project_structure(
                base_path=temp_dir,
                project_name="InvalidProject",
                structure_suggestions=invalid_structure
            ) 