# Test Plan: Guess Game (Python CLI)

## Objective
Validate correctness of game logic, score management, and UI formatting with lightweight unit tests.

---

## Test Strategy
- **Framework:** `unittest` (standard library).
- **Mocking:** Use `unittest.mock` to patch `random.randint`, `builtins.input`, and file I/O.
- **Coverage Target:** >90% on `score.py` and `game.py` core logic.

---

## Test Cases

### Module: `tests/test_score.py`

| ID | Test Name | Description |
|----|-----------|-------------|
| S1 | `test_load_scores_missing_file` | `load_scores()` returns `[]` when file does not exist. |
| S2 | `test_load_scores_corrupt_file` | `load_scores()` returns `[]` when JSON is invalid. |
| S3 | `test_load_scores_valid_file` | `load_scores()` returns sorted list from valid JSON. |
| S4 | `test_save_scores_creates_file` | `save_scores()` writes correct JSON to disk. |
| S5 | `test_save_scores_limits_top_5` | `save_scores()` keeps only top 5 entries. |
| S6 | `test_is_high_score_qualifies` | Returns `True` when attempts < 5th score. |
| S7 | `test_is_high_score_not_qualifies` | Returns `False` when attempts >= 5th score. |
| S8 | `test_add_score_inserts_correctly` | Inserts score in correct position and trims to 5. |

### Module: `tests/test_game.py`

| ID | Test Name | Description |
|----|-----------|-------------|
| G1 | `test_generate_number_in_range` | `_generate_number()` returns int in [1, 100]. |
| G2 | `test_get_guess_valid_input` | `_get_guess()` returns parsed int on valid input. |
| G3 | `test_get_guess_retries_on_invalid` | `_get_guess()` re-prompts on non-numeric input. |
| G4 | `test_get_guess_retries_on_out_of_range` | `_get_guess()` re-prompts on number outside 1-100. |
| G5 | `test_play_round_correct_guess` | `_play_round()` returns 1 attempt on first correct guess. |
| G6 | `test_play_round_multiple_guesses` | `_play_round()` returns correct count after multiple guesses. |
| G7 | `test_play_round_hint_too_low` | Displays "Too low!" when guess < target. |
| G8 | `test_play_round_hint_too_high` | Displays "Too high!" when guess > target. |

---

## Execution
- Run: `python -m pytest tests/ -v` or `python -m unittest discover -s tests -v`.
- All tests must pass before proceeding to Step 5 validation gate.

---

## Out of Scope
- UI/visual tests (manual smoke test only).
- Performance/load tests.
- Integration tests with actual file system (mocked in unit tests).
