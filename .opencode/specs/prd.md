# Product Requirements Document (PRD)
## Password Generator in Python

### Overview
A command-line password generator application written in Python that generates secure, customizable passwords based on user-defined criteria.

### User Stories
1. As a user, I want to generate passwords of specific lengths
2. As a user, I want to include/exclude uppercase letters, lowercase letters, numbers, and special characters
3. As a user, I want to exclude ambiguous characters (like 0/O, l/1/I) for better readability
4. As a user, I want to generate multiple passwords at once
5. As a user, I want to copy generated passwords to clipboard easily
6. As a user, I want to see password strength estimation

### Functional Requirements
1. Password generation with configurable length (8-128 characters)
2. Character type selection: uppercase, lowercase, digits, special characters
3. Ambiguous character exclusion option
4. Batch generation of multiple passwords
5. Clipboard copy functionality
6. Password strength indicator (weak/medium/strong/very strong)
7. Command-line interface with argparse
8. Error handling and input validation

### Non-Functional Requirements
1. Cross-platform compatibility (Windows, macOS, Linux)
2. Secure random number generation using Python's `secrets` module
3. Clean, readable code following PEP 8
4. Comprehensive error handling
5. No external dependencies beyond standard library

### Technical Stack
- Language: Python 3.6+
- Standard library modules: `secrets`, `string`, `argparse`, `random`

### Acceptance Criteria
1. Generates passwords of specified length
2. Properly includes/excludes selected character types
3. Excludes ambiguous characters when requested
4. Generates multiple passwords without duplication
5. Provides strength estimation
6. Handles invalid input gracefully
7. Works on all major operating systems