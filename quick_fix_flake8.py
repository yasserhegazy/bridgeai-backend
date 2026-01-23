#!/usr/bin/env python3
"""
Quick fix script for common Flake8 code quality issues.
Automatically removes unused imports and variables.

Usage: python quick_fix_flake8.py
"""

import re
import subprocess
from pathlib import Path

def run_flake8_check():
    """Get list of flake8 issues."""
    result = subprocess.run(
        ["python", "-m", "flake8", "app/", "tests/", 
         "--select=F401,F841,F541", "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s"],
        capture_output=True,
        text=True
    )
    return result.stdout

def fix_unused_imports(file_path: str, line_num: int):
    """Remove unused import from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove the import line
    if 0 <= line_num - 1 < len(lines):
        print(f"  Removing line {line_num}: {lines[line_num - 1].strip()}")
        lines.pop(line_num - 1)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False

def fix_f_string_placeholders(file_path: str, line_num: int):
    """Convert f-strings without placeholders to regular strings."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if 0 <= line_num - 1 < len(lines):
        line = lines[line_num - 1]
        # Remove f prefix from string
        fixed_line = re.sub(r'f(["\'])', r'\1', line)
        if fixed_line != line:
            print(f"  Fixing line {line_num}: f-string → regular string")
            lines[line_num - 1] = fixed_line
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False

def main():
    print("🔧 Running Flake8 Quick Fix...")
    print("This will automatically fix common issues:\n")
    print("  - F401: Remove unused imports")
    print("  - F541: Convert f-strings without placeholders")
    print()
    
    issues = run_flake8_check()
    
    if not issues.strip():
        print("✓ No issues found!")
        return
    
    # Parse issues
    fixed_count = 0
    for line in issues.strip().split('\n'):
        match = re.match(r'(.+?):(\d+):\d+: ([A-Z]\d+) (.+)', line)
        if not match:
            continue
        
        file_path, line_num, code, description = match.groups()
        line_num = int(line_num)
        
        print(f"\n{file_path}:{line_num} - {code}")
        
        if code == 'F401':  # Unused import
            if 'imported but unused' in description:
                if fix_unused_imports(file_path, line_num):
                    fixed_count += 1
        
        elif code == 'F541':  # f-string without placeholders
            if fix_f_string_placeholders(file_path, line_num):
                fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} issues!")
    print("\n⚠ Note: Some issues require manual fixing:")
    print("  - F841: Unused variables (decide if needed)")
    print("  - E722: Bare except (specify exception type)")
    print("  - E402: Import not at top (move imports)")
    print("  - F824: Unused global (remove or assign)")
    print("\nRun 'python pre_commit_check.py' to verify.")

if __name__ == "__main__":
    main()
