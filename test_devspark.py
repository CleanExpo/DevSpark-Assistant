import os
import sys
import json
from devspark.core import llm_interface, project_generator, config_checker

def clean_json_response(text):
    """Clean the JSON response from code block markers."""
    if text.startswith("```json\n"):
        text = text[7:]
    if text.endswith("\n```"):
        text = text[:-4]
    return text.strip()

def test_llm_interface():
    print("\n=== Testing LLM Interface ===")
    project_details = {
        "name": "TestProject",
        "type": "web app",
        "language": "Python"
    }
    print("Testing scaffolding suggestions...")
    result = llm_interface.get_scaffolding_suggestions(project_details)
    
    if isinstance(result, dict) and "error" in result and "raw_response" in result:
        # Try to parse the raw response
        try:
            clean_response = clean_json_response(result["raw_response"])
            parsed_result = json.loads(clean_response)
            if "directory_structure" in parsed_result and "files_to_create" in parsed_result:
                print("✅ Successfully parsed LLM response")
                return True
        except json.JSONDecodeError:
            pass
        print(f"❌ Error: {result['error']}")
        return False
    
    if "directory_structure" in result and "files_to_create" in result:
        print("✅ Successfully got scaffolding suggestions")
        return True
    
    print("❌ Unexpected response format")
    return False

def test_project_generator():
    print("\n=== Testing Project Generator ===")
    test_structure = {
        "directory_structure": [
            "src",
            "tests",
            "docs"
        ],
        "files_to_create": {
            "README.md": "# Test Project\nThis is a test.",
            "src/main.py": "print('Hello World')",
            "tests/__init__.py": "",
        }
    }
    try:
        base_path = os.path.join(os.getcwd(), "test_output")
        os.makedirs(base_path, exist_ok=True)
        project_generator.create_project_structure(
            base_path=base_path,
            project_name="test_project",
            structure_suggestions=test_structure
        )
        print("✅ Successfully generated test project structure")
        return True
    except Exception as e:
        print(f"❌ Error generating project structure: {e}")
        return False

def test_config_checker():
    print("\n=== Testing Config Checker ===")
    test_config = """
    {
        "name": "test-app",
        "version": "1.0.0",
        "dependencies": {
            "flask": "^2.0.0"
        }
    }
    """
    result = llm_interface.review_config_file(test_config, file_type="json")
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    print("✅ Successfully performed config check")
    return True

def main():
    print("Starting DevSpark Assistant Tests...")
    
    # Check if API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables")
        sys.exit(1)
    print("✅ Found Google API Key")

    # Run tests
    tests = [
        test_llm_interface,
        test_project_generator,
        test_config_checker
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Print summary
    print("\n=== Test Summary ===")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 