# Detailed Step-by-Step Implementation Plan: Password Generator (Python)

## Overview

This plan details the exact files, functions, and code structures to be created for the password generator.

---

## File 1: `password_generator.py` (Root of repository)

### Step 1: Module Header and Imports

**File**: `password_generator.py` (CREATE)
**Lines**: 1-10

```python
#!/usr/bin/env python3
"""
Secure Password Generator

A command-line tool to generate cryptographically secure random passwords
with configurable length, character sets, and options.
"""

import argparse
import secrets
import string
import sys
```

### Step 2: Constants

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 12-20

```python
# Character set constants
UPPERCASE = string.ascii_uppercase      # A-Z
LOWERCASE = string.ascii_lowercase      # a-z
DIGITS = string.digits                  # 0-9
SYMBOLS = string.punctuation            # !@#$%^&*()... etc
AMBIGUOUS = "Il1O0"                     # Characters that look similar
```

### Step 3: `build_char_pool(args)` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 22-45

```python
def build_char_pool(args):
    """
    Build the character pool based on command-line arguments.
    
    Args:
        args: Parsed argparse.Namespace with flags
        
    Returns:
        str: Combined character pool string
    """
    pool = ""
    
    if not args.no_upper:
        pool += UPPERCASE
    if not args.no_lower:
        pool += LOWERCASE
    if not args.no_digits:
        pool += DIGITS
    if not args.no_symbols:
        pool += SYMBOLS
    
    if args.ambiguous:
        pool = "".join(c for c in pool if c not in AMBIGUOUS)
    
    return pool
```

### Step 4: `validate_args(args, char_pool)` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 47-65

```python
def validate_args(args, char_pool):
    """
    Validate command-line arguments and character pool.
    
    Args:
        args: Parsed argparse.Namespace
        char_pool: Built character pool string
        
    Returns:
        None
        
    Raises:
        SystemExit: On validation failure
    """
    if len(char_pool) == 0:
        print("Error: No character sets available. Enable at least one character type.", file=sys.stderr)
        sys.exit(1)
    
    if args.length < 4:
        print(f"Error: Password length must be at least 4 (got {args.length}).", file=sys.stderr)
        sys.exit(1)
    
    if args.length > 256:
        print(f"Error: Password length cannot exceed 256 (got {args.length}).", file=sys.stderr)
        sys.exit(1)
    
    if args.count < 1:
        print(f"Error: Count must be at least 1 (got {args.count}).", file=sys.stderr)
        sys.exit(1)
```

### Step 5: `generate_password(length, char_pool)` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 67-82

```python
def generate_password(length, char_pool):
    """
    Generate a secure random password.
    
    Args:
        length: Desired password length
        char_pool: String of allowed characters
        
    Returns:
        str: Generated password
    """
    return "".join(secrets.choice(char_pool) for _ in range(length))
```

### Step 6: `copy_to_clipboard(text)` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 84-100

```python
def copy_to_clipboard(text):
    """
    Copy text to clipboard if pyperclip is available.
    
    Args:
        text: String to copy
        
    Returns:
        None
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        print("Password copied to clipboard.", file=sys.stderr)
    except ImportError:
        print("Note: pyperclip not installed. Copy the password manually.", file=sys.stderr)
    except Exception as e:
        print(f"Note: Could not copy to clipboard: {e}", file=sys.stderr)
```

### Step 7: `parse_args()` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 102-145

```python
def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate secure random passwords with configurable options.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python password_generator.py                    # Default 16-char password
  python password_generator.py --length 32        # 32-character password
  python password_generator.py --count 5          # Generate 5 passwords
  python password_generator.py --no-symbols       # No special characters
  python password_generator.py --ambiguous        # Exclude similar-looking chars
        """
    )
    
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=16,
        help="Password length (default: 16, min: 4, max: 256)"
    )
    
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=1,
        help="Number of passwords to generate (default: 1)"
    )
    
    parser.add_argument(
        "--no-upper",
        action="store_true",
        default=False,
        help="Exclude uppercase letters (A-Z)"
    )
    
    parser.add_argument(
        "--no-lower",
        action="store_true",
        default=False,
        help="Exclude lowercase letters (a-z)"
    )
    
    parser.add_argument(
        "--no-digits",
        action="store_true",
        default=False,
        help="Exclude digits (0-9)"
    )
    
    parser.add_argument(
        "--no-symbols",
        action="store_true",
        default=False,
        help="Exclude symbols (!@#$%%...)"
    )
    
    parser.add_argument(
        "--ambiguous",
        action="store_true",
        default=False,
        help="Exclude ambiguous characters (I, l, 1, O, 0)"
    )
    
    parser.add_argument(
        "--copy",
        action="store_true",
        default=False,
        help="Copy first password to clipboard (requires pyperclip)"
    )
    
    return parser.parse_args()
```

### Step 8: `main()` Function

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 147-170

```python
def main():
    """Main entry point for the password generator."""
    args = parse_args()
    
    char_pool = build_char_pool(args)
    validate_args(args, char_pool)
    
    passwords = []
    for _ in range(args.count):
        password = generate_password(args.length, char_pool)
        passwords.append(password)
        print(password)
    
    if args.copy and passwords:
        copy_to_clipboard(passwords[0])
```

### Step 9: Entry Point Guard

**File**: `password_generator.py` (MODIFY - append)
**Lines**: 172-174

```python
if __name__ == "__main__":
    main()
```

---

## File 2: `test_password_generator.py` (Root of repository)

### Step 1: Test Module Header and Imports

**File**: `test_password_generator.py` (CREATE)
**Lines**: 1-20

```python
"""
Tests for the Password Generator CLI tool.
"""

import unittest
import subprocess
import sys
import os

# Import functions from the main module
from password_generator import (
    build_char_pool,
    validate_args,
    generate_password,
    UPPERCASE,
    LOWERCASE,
    DIGITS,
    SYMBOLS,
    AMBIGUOUS,
)
```

### Step 2: Mock Args Helper

**File**: `test_password_generator.py` (MODIFY - append)
**Lines**: 22-40

```python
class MockArgs:
    """Mock argparse.Namespace for testing."""
    
    def __init__(self, **kwargs):
        self.length = kwargs.get("length", 16)
        self.count = kwargs.get("count", 1)
        self.no_upper = kwargs.get("no_upper", False)
        self.no_lower = kwargs.get("no_lower", False)
        self.no_digits = kwargs.get("no_digits", False)
        self.no_symbols = kwargs.get("no_symbols", False)
        self.ambiguous = kwargs.get("ambiguous", False)
        self.copy = kwargs.get("copy", False)
```

### Step 3: Unit Test Class

**File**: `test_password_generator.py` (MODIFY - append)
**Lines**: 42-120

```python
class TestUnit(unittest.TestCase):
    """Unit tests for individual functions."""
    
    def test_build_char_pool_default(self):
        """Default pool includes all character sets."""
        args = MockArgs()
        pool = build_char_pool(args)
        self.assertIn("A", pool)  # uppercase
        self.assertIn("a", pool)  # lowercase
        self.assertIn("0", pool)  # digits
        self.assertIn("@", pool)  # symbols
    
    def test_build_char_pool_no_upper(self):
        """Pool excludes uppercase when flag is set."""
        args = MockArgs(no_upper=True)
        pool = build_char_pool(args)
        for c in UPPERCASE:
            self.assertNotIn(c, pool)
    
    def test_build_char_pool_no_lower(self):
        """Pool excludes lowercase when flag is set."""
        args = MockArgs(no_lower=True)
        pool = build_char_pool(args)
        for c in LOWERCASE:
            self.assertNotIn(c, pool)
    
    def test_build_char_pool_no_digits(self):
        """Pool excludes digits when flag is set."""
        args = MockArgs(no_digits=True)
        pool = build_char_pool(args)
        for c in DIGITS:
            self.assertNotIn(c, pool)
    
    def test_build_char_pool_no_symbols(self):
        """Pool excludes symbols when flag is set."""
        args = MockArgs(no_symbols=True)
        pool = build_char_pool(args)
        for c in SYMBOLS:
            self.assertNotIn(c, pool)
    
    def test_build_char_pool_ambiguous(self):
        """Pool excludes ambiguous characters when flag is set."""
        args = MockArgs(ambiguous=True)
        pool = build_char_pool(args)
        for c in AMBIGUOUS:
            self.assertNotIn(c, pool)
    
    def test_generate_password_length(self):
        """Generated password matches requested length."""
        args = MockArgs(length=20)
        pool = build_char_pool(args)
        password = generate_password(20, pool)
        self.assertEqual(len(password), 20)
    
    def test_generate_password_characters(self):
        """Generated password contains only characters from the pool."""
        args = MockArgs()
        pool = build_char_pool(args)
        password = generate_password(100, pool)
        for c in password:
            self.assertIn(c, pool)
    
    def test_validate_args_all_excluded(self):
        """Validation fails when all character sets are excluded."""
        args = MockArgs(no_upper=True, no_lower=True, no_digits=True, no_symbols=True)
        pool = build_char_pool(args)
        with self.assertRaises(SystemExit):
            validate_args(args, pool)
    
    def test_validate_args_short_length(self):
        """Validation fails when length < 4."""
        args = MockArgs(length=3)
        pool = build_char_pool(args)
        with self.assertRaises(SystemExit):
            validate_args(args, pool)
```

### Step 4: Integration Test Class

**File**: `test_password_generator.py` (MODIFY - append)
**Lines**: 122-200

```python
class TestIntegration(unittest.TestCase):
    """Integration tests for CLI execution."""
    
    SCRIPT = "password_generator.py"
    
    def _run(self, *args):
        """Run the password generator with given arguments."""
        cmd = [sys.executable, self.SCRIPT] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def test_default_run(self):
        """Default run produces a 16-character password."""
        result = self._run()
        self.assertEqual(result.returncode, 0)
        password = result.stdout.strip()
        self.assertEqual(len(password), 16)
    
    def test_custom_length(self):
        """Custom length produces correct length."""
        result = self._run("--length", "32")
        self.assertEqual(result.returncode, 0)
        password = result.stdout.strip()
        self.assertEqual(len(password), 32)
    
    def test_multiple_count(self):
        """Count flag produces multiple passwords."""
        result = self._run("--count", "5")
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().split("\n")
        self.assertEqual(len(lines), 5)
        for line in lines:
            self.assertEqual(len(line), 16)
    
    def test_no_symbols_flag(self):
        """No-symbols flag excludes symbols from output."""
        result = self._run("--no-symbols", "--length", "100")
        self.assertEqual(result.returncode, 0)
        password = result.stdout.strip()
        for c in password:
            self.assertNotIn(c, SYMBOLS)
    
    def test_ambiguous_flag(self):
        """Ambiguous flag excludes similar-looking characters."""
        result = self._run("--ambiguous", "--length", "200")
        self.assertEqual(result.returncode, 0)
        password = result.stdout.strip()
        for c in password:
            self.assertNotIn(c, AMBIGUOUS)
    
    def test_invalid_all_excluded(self):
        """Exitting all character sets produces error."""
        result = self._run("--no-upper", "--no-lower", "--no-digits", "--no-symbols")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error", result.stderr)
    
    def test_short_length(self):
        """Length < 4 produces error."""
        result = self._run("--length", "3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error", result.stderr)
    
    def test_copy_flag(self):
        """Copy flag runs without error."""
        result = self._run("--copy")
        # May succeed or show pyperclip note, but should not crash
        self.assertIn(result.returncode, [0])
```

### Step 5: Entry Point

**File**: `test_password_generator.py` (MODIFY - append)
**Lines**: 202-204

```python
if __name__ == "__main__":
    unittest.main()
```

---

## Summary

| Step | File | Action | Functions/Components |
|------|------|--------|---------------------|
| 1 | `password_generator.py` | CREATE | Module header, imports |
| 2 | `password_generator.py` | MODIFY | Constants: UPPERCASE, LOWERCASE, DIGITS, SYMBOLS, AMBIGUOUS |
| 3 | `password_generator.py` | MODIFY | `build_char_pool(args)` |
| 4 | `password_generator.py` | MODIFY | `validate_args(args, char_pool)` |
| 5 | `password_generator.py` | MODIFY | `generate_password(length, char_pool)` |
| 6 | `password_generator.py` | MODIFY | `copy_to_clipboard(text)` |
| 7 | `password_generator.py` | MODIFY | `parse_args()` |
| 8 | `password_generator.py` | MODIFY | `main()` |
| 9 | `password_generator.py` | MODIFY | Entry point guard |
| 10 | `test_password_generator.py` | CREATE | Test header, imports, MockArgs |
| 11 | `test_password_generator.py` | MODIFY | `TestUnit` class (10 tests) |
| 12 | `test_password_generator.py` | MODIFY | `TestIntegration` class (8 tests) |
| 13 | `test_password_generator.py` | MODIFY | Entry point guard |
