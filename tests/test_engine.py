import sys
import os
# This line tells Python to look in the root folder for our engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_engine.pruner import get_file_imports

def test_import_extraction():
    # 1. Create a temporary dummy file
    temp_file = "test_dummy.py"
    with open(temp_file, "w") as f:
        f.write("import math\nfrom os import path")
    
    # 2. Run our engine on it
    found = get_file_imports(temp_file)
    
    # 3. Check if it found the right things
    assert "math" in found
    assert "os" in found
    
    # 4. Cleanup
    os.remove(temp_file)
    print("✅ Unit Test Passed: Import extraction is accurate!")

if __name__ == "__main__":
    test_import_extraction()