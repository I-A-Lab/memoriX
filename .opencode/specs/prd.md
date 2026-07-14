# Product Requirements Document: Password Generator (Python)

## 1. Overview

Build a **command-line Python password generator** that produces secure, random passwords with configurable length, complexity, and character set options. The tool runs locally in a terminal and outputs a single password per invocation, with optional clipboard copying.

## 2. Goals

| Goal | Description |
|------|-------------|
| Security | Use Python's `secrets` module for cryptographically strong randomness |
| Usability | Single-command invocation with sensible defaults |
| Configurability | Let users control length, character types, and exclusion rules |
| Portability | Pure Python, no external dependencies beyond the standard library |

## 3. User Stories

1. As a user, I want to run `python password_generator.py` and instantly get a secure 16-character password so I can use it immediately.
2. As a user, I want to specify the password length via `--length N` so I can meet different site requirements.
3. As a user, I want to include/exclude uppercase, lowercase, digits, and symbols via flags so I can satisfy specific password policies.
4. As a user, I want to exclude ambiguous characters (e.g., `l`, `1`, `O`, `0`) so passwords are easy to read aloud.
5. As a user, I want to generate multiple passwords at once via `--count N` so I can compare or batch-assign.
6. As a user, I want a `--copy` flag that copies the result to my clipboard so I can paste it directly.

## 4. Features

### 4.1 Core

- Generate a single random password using `secrets.choice()`.
- Default length: 16 characters.
- Default character set: uppercase + lowercase + digits + symbols.

### 4.2 CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--length` / `-l` | int | 16 | Password length (min 4, max 256) |
| `--count` / `-c` | int | 1 | Number of passwords to generate |
| `--no-upper` | flag | false | Exclude uppercase letters |
| `--no-lower` | flag | false | Exclude lowercase letters |
| `--no-digits` | flag | false | Exclude digits |
| `--no-symbols` | flag | false | Exclude symbols |
| `--ambiguous` | flag | false | Exclude ambiguous characters (I, l, 1, O, 0) |
| `--copy` | flag | false | Copy first password to clipboard (uses `pyperclip` if available, else prints a message) |

### 4.3 Validation

- Ensure at least one character set remains selected after exclusions.
- Print a clear error message and exit with code 1 on invalid input.
- Enforce minimum length of 4 characters.

### 4.4 Output

- Print one password per line to stdout.
- When `--count > 1`, print all passwords, each on its own line.

## 5. Non-Goals

- No GUI or web interface.
- No password storage or vault functionality.
- No external dependencies (optional clipboard support via `pyperclip` if installed).
- No password strength scoring or entropy display in v1.

## 6. Technical Constraints

- **Language**: Python 3.9+
- **Dependencies**: Standard library only (`secrets`, `string`, `argparse`, `sys`). Clipboard is optional (`pyperclip`).
- **File**: Single file `password_generator.py` at repository root.

## 7. Success Criteria

- Running `python password_generator.py` produces a 16-character password with all character types.
- Running with `--length 32 --count 5` produces five 32-character passwords.
- Running with `--no-symbols --ambiguous` produces a password with only lowercase, uppercase, and digits (excluding ambiguous chars).
- Invalid combinations (e.g., `--no-upper --no-lower --no-digits --no-symbols`) produce a clear error.

## 8. Out of Scope for v1

- Entropy calculation.
- Password strength meter.
- Batch file output.
- Integration with password managers.
