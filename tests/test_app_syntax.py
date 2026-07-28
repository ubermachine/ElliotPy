import ast
import os

def test_app_py_syntax():
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    assert os.path.exists(app_path), "app.py does not exist"
    
    with open(app_path, "r", encoding="utf-8") as f:
        source = f.read()
        
    tree = ast.parse(source)
    assert tree is not None, "Failed to parse app.py AST"

def test_no_selected_count_name_in_app():
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        source = f.read()
    assert "selected_count_name" not in source, "Found deprecated variable 'selected_count_name' in app.py"
