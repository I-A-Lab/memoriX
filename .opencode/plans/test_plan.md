# Test Plan
## Password Generator in Python

### Test Strategy
- Unit tests for all core functions
- Integration tests for CLI
- Edge case testing for security-critical paths

### Test Structure
```
tests/
├── __init__.py
├── test_generator.py      # Test password generation
├── test_strength.py       # Test strength estimation
├── test_utils.py          # Test utility functions
└── test_cli.py           # Test CLI interface
```

### Test Cases

#### Generator Tests (`test_generator.py`)
1. **Test basic generation**
   - Generate password with default settings
   - Verify length matches specification
   - Verify character types are present when enabled

2. **Test character type control**
   - Generate with only uppercase
   - Generate with only lowercase
   - Generate with only digits
   - Generate with only special characters
   - Verify each type is correctly included/excluded

3. **Test ambiguous character exclusion**
   - Generate with `exclude_ambiguous=True`
   - Verify none of the ambiguous characters appear
   - Test with mixed character types

4. **Test batch generation**
   - Generate multiple passwords
   - Verify all have correct length
   - Verify passwords are unique (statistically)

5. **Test edge cases**
   - Minimum length (8)
   - Maximum length (128)
   - Zero count should raise error
   - Negative length should raise error

#### Strength Tests (`test_strength.py`)
1. **Test strength levels**
   - Short password with few types → weak
   - Medium length with 2 types → medium
   - Long length with 3 types → strong
   - Long length with all types → very strong

2. **Test strength consistency**
   - Same input always produces same strength
   - Longer passwords generally have higher strength

#### Utility Tests (`test_utils.py`)
1. **Test clipboard copy**
   - Mock platform-specific functions
   - Verify correct function is called

2. **Test ambiguous character set**
   - Verify all expected characters are included
   - Verify set is non-empty

#### CLI Tests (`test_cli.py`)
1. **Test argument parsing**
   - Test default values
   - Test custom arguments
   - Test invalid combinations

2. **Test output format**
   - Verify password is printed
   - Verify strength is shown when requested

### Test Execution
- Run with: `python -m pytest tests/ -v`
- Minimum coverage: 90% for all modules
- Security-critical code must have 100% coverage