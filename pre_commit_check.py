#!/usr/bin/env python3
"""
Pre-commit validation script for BridgeAI Backend.
Runs all CI/CD checks locally before committing and pushing code.

Usage:
    python pre_commit_check.py
    python pre_commit_check.py --skip-tests  # Skip tests (faster)
    python pre_commit_check.py --fix         # Auto-fix formatting issues
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(message: str):
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def run_command(cmd: List[str], description: str, fix_mode: bool = False) -> Tuple[bool, str]:
    """
    Run a shell command and return success status and output.
    
    Args:
        cmd: Command and arguments as list
        description: Description of what the command does
        fix_mode: If True, run in fix mode (e.g., auto-format)
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    print(f"{Colors.BOLD}Running: {description}...{Colors.RESET}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Command succeeded (exit code 0)
        if result.returncode == 0:
            print_success(f"{description} passed")
            return True, result.stdout
        else:
            # Command failed
            print_error(f"{description} failed")
            if result.stdout:
                print(f"\n{Colors.YELLOW}STDOUT:{Colors.RESET}")
                print(result.stdout[:2000])  # Limit output
            if result.stderr:
                print(f"\n{Colors.YELLOW}STDERR:{Colors.RESET}")
                print(result.stderr[:2000])  # Limit output
            return False, result.stderr or result.stdout
            
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        print_warning(f"Please install: pip install {cmd[0]}")
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        print_error(f"Error running {description}: {str(e)}")
        return False, str(e)


def check_black(fix_mode: bool = False) -> bool:
    """Check code formatting with Black."""
    if fix_mode:
        # Auto-fix mode
        success, _ = run_command(
            ["python", "-m", "black", "app/", "tests/"],
            "Black (auto-formatting code)",
            fix_mode=True
        )
        return success
    else:
        # Check-only mode
        success, _ = run_command(
            ["python", "-m", "black", "--check", "--diff", "app/", "tests/"],
            "Black (code formatting check)"
        )
        if not success:
            print_warning("Run with --fix to auto-format, or run: python -m black app/ tests/")
        return success


def check_isort(fix_mode: bool = False) -> bool:
    """Check import sorting with isort."""
    if fix_mode:
        # Auto-fix mode
        success, _ = run_command(
            ["python", "-m", "isort", "app/", "tests/"],
            "isort (auto-sorting imports)",
            fix_mode=True
        )
        return success
    else:
        # Check-only mode
        success, _ = run_command(
            ["python", "-m", "isort", "--check-only", "--diff", "app/", "tests/"],
            "isort (import sorting check)"
        )
        if not success:
            print_warning("Run with --fix to auto-sort, or run: python -m isort app/ tests/")
        return success


def check_flake8() -> bool:
    """Run Flake8 linting checks."""
    # Critical errors only (syntax errors, undefined names)
    success1, _ = run_command(
        ["python", "-m", "flake8", "app/", "tests/", 
         "--count", "--select=E9,F63,F7,F82", "--show-source", "--statistics"],
        "Flake8 (critical syntax errors)"
    )
    
    # Important errors (unused imports, variables, etc.) - should fix but not block
    success2, _ = run_command(
        ["python", "-m", "flake8", "app/", "tests/",
         "--count", "--select=F401,F841,E402,E722,F541",
         "--show-source", "--statistics"],
        "Flake8 (code quality - should fix)"
    )
    
    # Minor warnings (informational only)
    run_command(
        ["python", "-m", "flake8", "app/", "tests/",
         "--count", "--select=W291,W293,F824",
         "--show-source", "--statistics"],
        "Flake8 (style warnings - optional)"
    )
    
    # Only fail on critical errors, warn on quality issues
    if not success1:
        return False
    if not success2:
        print_warning("⚠ Code quality issues found - please fix when possible")
        print_warning("   Most common: unused imports, f-strings without placeholders")
        print_warning("   Run: python quick_fix_flake8.py (to auto-fix some issues)")
    return success1  # Only block on critical syntax errors


def check_mypy() -> bool:
    """Run MyPy type checking (non-blocking)."""
    success, _ = run_command(
        ["python", "-m", "mypy", "app/", "--ignore-missing-imports", "--no-strict-optional"],
        "MyPy (type checking - informational)"
    )
    # Don't fail build on type errors
    return True


def check_bandit() -> bool:
    """Run Bandit security scanner."""
    success, _ = run_command(
        ["python", "-m", "bandit", "-r", "app/",
         "-ll", "--exclude", "tests/"],
        "Bandit (security scan)"
    )
    return success


def check_safety() -> bool:
    """Run Safety dependency vulnerability check."""
    success, _ = run_command(
        ["python", "-m", "safety", "check", "--json"],
        "Safety (dependency vulnerability check)"
    )
    # Safety might return non-zero even for low severity issues
    # Don't fail build, just warn
    if not success:
        print_warning("Safety found some issues. Review them but build will continue.")
    return True


def run_tests(skip_tests: bool = False) -> bool:
    """Run pytest test suite."""
    if skip_tests:
        print_warning("Tests skipped (--skip-tests flag)")
        return True
    
    print_warning("Running tests (this may take a while)...")
    print_warning("Ensure dependencies are installed: pip install -r requirements.txt")
    success, output = run_command(
        ["python", "-m", "pytest", "tests/",
         "-v", "--tb=short", "--maxfail=5"],
        "Pytest (test suite)"
    )
    
    if not success and "ModuleNotFoundError" in output:
        print_error("\nMissing dependencies detected!")
        print_warning("Run: pip install -r requirements.txt")
    
    return success


def check_git_status():
    """Check if there are uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print_warning("\nYou have uncommitted changes:")
            print(result.stdout[:500])  # Show first 500 chars
        else:
            print_success("No uncommitted changes")
            
    except subprocess.CalledProcessError:
        print_warning("Could not check git status")
    except FileNotFoundError:
        print_warning("Git not found in PATH")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Pre-commit validation for BridgeAI Backend"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (faster check)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix formatting and import sorting issues"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick check (formatting and linting only, no tests or security)"
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_header("BridgeAI Backend - Pre-Commit Validation")
    print(f"{Colors.BOLD}This script validates your code against CI/CD requirements{Colors.RESET}\n")
    
    # Track results
    results = {}
    
    # 1. Code Formatting
    print_header("1. Code Formatting")
    results["Black"] = check_black(fix_mode=args.fix)
    results["isort"] = check_isort(fix_mode=args.fix)
    
    # 2. Linting
    print_header("2. Code Linting")
    results["Flake8"] = check_flake8()
    results["MyPy"] = check_mypy()
    
    # 3. Security (skip in quick mode)
    if not args.quick:
        print_header("3. Security Scans")
        results["Bandit"] = check_bandit()
        results["Safety"] = check_safety()
    
    # 4. Tests (skip in quick mode or if --skip-tests)
    if not args.quick:
        print_header("4. Test Suite")
        results["Tests"] = run_tests(skip_tests=args.skip_tests)
    
    # 5. Git Status
    print_header("5. Git Status")
    check_git_status()
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for check, success in results.items():
        if success:
            print_success(f"{check:<20} PASSED")
        else:
            print_error(f"{check:<20} FAILED")
    
    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.RESET}\n")
    
    if failed == 0:
        print_success(f"{Colors.BOLD}✓ ALL CHECKS PASSED! You're ready to commit and push.{Colors.RESET}\n")
        return 0
    else:
        print_error(f"{Colors.BOLD}✗ Some checks failed. Please fix the issues before committing.{Colors.RESET}\n")
        
        # Provide helpful tips
        if not results.get("Tests", True):
            print_warning("→ Install dependencies: pip install -r requirements.txt")
        
        if not results.get("Flake8", True):
            print_warning("→ Fix code quality issues shown above")
            print_warning("→ Common: Remove unused imports, fix f-strings, specify exception types")
        
        if args.fix:
            print_warning("\n→ Auto-fix was applied for formatting. Re-run to verify.")
        else:
            print_warning("\n→ Tip: Run with --fix to auto-fix formatting issues")
            print_warning("→ Tip: Run with --quick for faster checks (no tests/security)")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
