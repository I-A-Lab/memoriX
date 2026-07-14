# Test Plan: Password Generator (Python)

## 1. Overview

Test the password generator CLI tool with unit tests and integration tests using Python's built-in `unittest` framework and subprocess calls.

## 2. Test Categories

### 2.1 Unit Tests

Test individual functions in isolation:

| Test | Description |
|------|-------------|
| `test_build_char_pool_default` | Default pool includes uppercase, lowercase, digits, symbols |
| `test_build_char_pool_no_upper` | Pool excludes uppercase when `--no-upper` is set |
| `test_build_char_pool_no_lower` | Pool excludes lowercase when `--no-lower` is set |
| `test_build_char_pool_no_digits` | Pool excludes digits when `--no-digits` is set |
| `test_build_char_pool_no_symbols` | Pool excludes symbols when `--no-symbols` is set |
| `test_build_char_pool_ambiguous` | Pool excludes ambiguous characters when flag is set |
| `test_generate_password_length` | Generated password matches requested length |
| `test_generate_password_characters` | Generated password contains only characters from the pool |
| `test_validate_args_minimum_length` | Validation fails when length < 4 |
| `test_validate_args_no_char_set` | Validation fails when all character sets are excluded |

### 2.2 Integration Tests

Test the CLI as a subprocess:

| Test | Command | Expected |
|------|---------|----------|
| `test_default_run` | `python password_generator.py` | Exit code 0, output length 16 |
| `test_custom_length` | `python password_generator.py --length 32` | Exit code 0, output length 32 |
| `test_multiple_count` | `python password_generator.py --count 5` | Exit code 0, 5 lines of output |
| `test_no_symbols_flag` | `python password_generator.py --no-symbols` | Exit code 0, no symbols in output |
| `test_ambiguous_flag` | `python password_generator.py --ambiguous` | Exit code 0, no ambiguous chars |
| `test_invalid_all_excluded` | `python password_generator.py --no-upper --no-lower --no-digits --no-symbols` | Exit code 1, error message |
| `test_short_length` | `python password_generator.py --length 3` | Exit code 1, error message |
| `test_copy_flag` | `python password_generator.py --copy` | Exit code 0, clipboard message or success |

### 2.3 Edge Cases

| Test | Description |
|------|-------------|
| `test_minimum_valid_length` | Length=4 works correctly |
| `test_maximum_length` | Length=256 works correctly |
| `test_single_char_set` | Only uppercase (all others excluded) produces valid password |
| `test_empty_output_on_error` | No output to stdout on validation failure |

## 3. Test File Structure

```
memoriX/
├── password_generator.py          # Source code
└── test_password_generator.py     # All tests
```

## 4. Test Execution

```bash
# Run all tests
python -m unittest test_password_generator -v

# Run specific test class
python -m unittest test_password_generator.TestUnit -v

# Run specific test
python -m unittest test_password_generator.TestIntegration.test_default_run -v
```

## 5. Assertions

- Use `assertRegex` for pattern matching on output.
- Use `assertEqual` for exact length checks.
- Use `assertIn` / `assertNotIn` for character presence checks.
- Use `assertGreaterEqual` for counting lines of output.
- Use `subprocess.run` with `capture_output=True` for CLI tests.

## 6. Coverage Goals

- 100% function coverage.
- All CLI argument paths tested.
- All error conditions tested.
