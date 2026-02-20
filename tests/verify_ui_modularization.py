import re
import sys
import os

def verify_ui_modularization():
    file_path = "ecs/systems/ui_system.py"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return False

    with open(file_path, 'r') as f:
        content = f.read()

    # Methods to check
    methods_to_check = [
        "draw_header",
        "draw_sidebar",
        "_draw_sidebar_resource_bars",
        "_draw_sidebar_actions",
        "_draw_sidebar_equipment",
        "_draw_sidebar_combat_stats",
        "_draw_sidebar_needs",
        "_draw_section_title"
    ]

    errors = []
    
    # Check for LayoutCursor usage in draw_sidebar
    if "self.sidebar_cursor.reset()" not in content:
        errors.append("LayoutCursor.reset() not called in draw_sidebar")
    
    # Check for modular calls in draw_sidebar
    sidebar_calls = [
        "self._draw_sidebar_resource_bars",
        "self._draw_sidebar_actions",
        "self._draw_sidebar_equipment",
        "self._draw_sidebar_combat_stats",
        "self._draw_sidebar_needs"
    ]
    for call in sidebar_calls:
        if call not in content:
            errors.append(f"Missing call to {call} in draw_sidebar")

    # Check for magic numbers in the methods
    for method in methods_to_check:
        # Improved regex to find method body until next method or end of class
        pattern = r"def " + method + r"\(self, .*?\):((?:\n    (?:    |).*)+)"
        match = re.search(pattern, content)
        if match:
            body = match.group(1)
            
            # Find numeric literals
            # Match integers and floats not preceded by [a-zA-Z0-9_]
            numbers = re.findall(r'(?<![a-zA-Z0-9_])\d+(?![a-zA-Z0-9_\.])', body)
            
            # Allowed: 0, 1, 2, 3, 5, 255 (common color), and numbers that are clearly part of color tuples or common offsets
            # But the goal is to remove them.
            # 130, 80, 60, 25, 30, 95, 180, 150, 20, 100
            
            allowed = {'0', '1', '2', '3', '5', '255'}
            
            magic_numbers = [n for n in numbers if n not in allowed]
            
            if magic_numbers:
                for n in magic_numbers:
                    errors.append(f"Magic number '{n}' found in {method}")

    if errors:
        print("Verification failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("Verification passed! No magic numbers found.")
        return True

if __name__ == "__main__":
    if not verify_ui_modularization():
        sys.exit(1)
