# Development Plan: Guess Game (Python CLI)

## Objective
Implement a Python CLI number guessing game with dark theme ANSI UI and high score persistence.

---

## Architecture Overview
- **Entry Point:** `guess_game/__main__.py` - runs the game loop.
- **Game Logic:** `guess_game/game.py` - contains the `GuessGame` class.
- **Score Management:** `guess_game/score.py` - handles `highscores.json` CRUD.
- **UI Helpers:** `guess_game/ui.py` - ANSI color codes and display formatting.
- **Tests:** `tests/test_game.py`, `tests/test_score.py`.

---

## Module Responsibilities

### 1. `guess_game/ui.py`
- Constants for ANSI color codes (CYAN, YELLOW, GREEN, RED, MAGENTA, BLUE, WHITE, DIM, RESET).
- `print_header(title: str)` - prints centered, colored title with divider.
- `print_instruction(text: str)` - prints dim white text.
- `print_prompt(text: str)` - prints yellow prompt and returns user input.
- `print_feedback(text: str, color: str)` - prints colored feedback.
- `print_leaderboard(scores: list[dict])` - prints formatted leaderboard table.
- `clear_line()` - utility to clear current terminal line.

### 2. `guess_game/score.py`
- `load_scores(path: str = "highscores.json") -> list[dict]`
  - Returns list of `{"name": str, "attempts": int}` sorted ascending by attempts.
  - Returns empty list if file missing or corrupt.
- `save_scores(scores: list[dict], path: str = "highscores.json") -> None`
  - Writes top 5 scores to JSON file.
- `is_high_score(scores: list[dict], attempts: int) -> bool`
  - Returns True if `attempts` qualifies for top 5.
- `add_score(scores: list[dict], name: str, attempts: int) -> list[dict]`
  - Inserts new score, sorts, returns top 5.

### 3. `guess_game/game.py`
- `class GuessGame`
  - `__init__(self)` - initializes random seed, loads scores.
  - `_generate_number() -> int` - returns random int 1-100.
  - `_get_guess() -> int` - prompts user, validates, returns int.
  - `_play_round() -> int` - runs one round, returns attempts.
  - `_check_high_score(attempts: int) -> None` - handles score check and name prompt.
  - `run() -> None` - main loop: play round, check score, ask replay.

### 4. `guess_game/__main__.py`
  - `if __name__ == "__main__":` instantiates `GuessGame` and calls `run()`.

---

## Implementation Steps (Micro-Tasks)

1. Create `guess_game/__init__.py` (empty).
2. Create `guess_game/ui.py` with color constants and display functions.
3. Create `guess_game/score.py` with load/save/check/add functions.
4. Create `guess_game/game.py` with `GuessGame` class.
5. Create `guess_game/__main__.py` entry point.
6. Create `tests/test_score.py` with unit tests for score module.
7. Create `tests/test_game.py` with unit tests for game logic.
8. Verify all tests pass.
9. Manual smoke test: run `python -m guess_game` and play one round.

---

## Dependencies
- Python 3.8+ standard library only: `random`, `json`, `os`, `sys`, `pathlib`.

---

## File Tree
```
guess_game/
    __init__.py
    ui.py
    score.py
    game.py
    __main__.py
tests/
    __init__.py
    test_game.py
    test_score.py
```
