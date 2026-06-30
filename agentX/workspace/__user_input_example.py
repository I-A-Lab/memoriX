from typing import Dict, Optional
import sys

def get_password_length_and_character_types(user_input: str) -> Optional[Dict[str, bool]]:
    length = None
    include_uppercase = False
    include_lowercase = False
    include_digits = False

    if user_input.isdigit():
        length = int(user_input)
    elif user_input.isnumeric() and len(user_input) > 1:
        try:
            length = int(user_input[:len(user_input) - 1])
        except ValueError:
            sys.stderr.write('Invalid input for length. Please provide a valid integer.
')

    if 'u' in user_input.lower():
        include_uppercase = True
    if 'l' in user_input.lower():
        include_lowercase = True
    if 'd' in user_input.lower():
        include_digits = True

    # Ensure at least one type of character is included.
    valid_types = {'u', 'l', 'd'}
    required_types: Dict[str, bool] = {
        'upper': include_uppercase,
        'lower': include_lowercase,
        'digit': include_digits,
    }

    if not (required_types and any(valid_type in required_types for valid_type in valid_types)):
        raise ValueError('Password must contain at least one of the following: uppercase letters, lowercase letters, or digits.')

    return required_types