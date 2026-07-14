# Development Plan: Password Generator (Python)

## 1. Overview

Create a single-file Python CLI tool (`password_generator.py`) that generates secure random passwords with configurable options.

## 2. Architecture

- **Single file**: All code lives in `password_generator.py` at repository root.
- **No external dependencies**: Uses only Python standard library.
- **Modular internal structure**: Separate functions for generation, argument parsing, validation, and output.

## 3. Implementation Steps

### Step 1: Project Setup
- Create `password_generator.py` with shebang and module docstring.
- Import required modules: `secrets`, `string`, `argparse`, `sys`.

### Step 2: Character Set Definitions
- Define constants for each character category:
  - `UPPERCASE = string.ascii_uppercase`
  - `LOWERCASE = string.ascii_lowercase`
  - `DIGITS = string.digits`
  - `SYMBOLS = string.punctuation`
  - `AMBIGUOUS = "Il1O0"` (characters to exclude when `--ambiguous` is set)

### Step 3: Argument Parser
- Create `argparse.ArgumentParser` with description.
- Add arguments: `--length`, `--count`, `--no-upper`, `--no-lower`, `--no-digits`, `--no-symbols`, `--ambiguous`, `--copy`.
- Set defaults and help text for each argument.

### Step 4: Validation Function
- `validate_args(args)`:
  - Ensure at least one character set remains after exclusions.
  - Ensure `length >= 4`.
  - Print error and exit with code 1 on failure.

### Step 5: Password Generation
- `generate_password(length, char_pool)`:
  - Use `secrets.choice(char_pool)` in a loop to build password.
  - Return the password string.
- `build_char_pool(args)`:
  - Start with empty set.
  - Add character sets based on flags.
  - Remove ambiguous characters if `args.ambiguous` is True.
  - Convert to string and return.

### Step 6: Clipboard Support
- `copy_to_clipboard(text)`:
  - Try to import `pyperclip`.
  - If available, copy text and print confirmation.
  - If not available, print a message that clipboard copy is unavailable.

### Step 7: Main Function
- `main()`:
  - Parse arguments.
  - Validate.
  - Build character pool.
  - Generate `count` passwords.
  - Print each password to stdout.
  - If `--copy` flag is set, copy the first password to clipboard.

### Step 8: Entry Point
- Add `if __name__ == "__main__": main()` block.

## 4. File Structure

```
memoriX/
└── password_generator.py   # Single file with all code
```

## 5. Testing Strategy

See `test_plan.md` for details.

## 6. Dependencies

- Python 3.9+
- Optional: `pyperclip` for clipboard support
