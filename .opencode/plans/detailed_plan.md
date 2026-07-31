# Detailed Implementation Plan: Guess Game (Python CLI)

## Overview
This plan breaks the implementation into atomic, sequential micro-tasks. Each task is designed to be executed independently while keeping the application functional.

---

## Step 1: Create Project Structure
- **File:** `guess_game/__init__.py`
- **Action:** Create empty file to make `guess_game` a Python package.
- **Dependencies:** None.
- **Verification:** Directory `guess_game/` exists with `__init__.py`.

---

## Step 2: Create UI Module
- **File:** `guess_game/ui.py`
- **Action:** Create file with ANSI color constants and display helper functions.
- **Contents:**
  - Color constants: `CYAN`, `YELLOW`, `GREEN`, `RED`, `MAGENTA`, `BLUE`, `WHITE`, `DIM`, `RESET`.
  - `print_header(title: str)` - prints centered title with cyan divider.
  - `print_instruction(text: str)` - prints dim white text.
  - `print_prompt(text: str)` - prints yellow prompt, returns `input()`.
  - `print_feedback(text: str, color: str)` - prints colored text.
  - `print_leaderboard(scores: list)` - prints formatted table.
  - `clear_line()` - clears current line.
- **Dependencies:** None.
- **Verification:** Module imports without error; functions callable.

---

## Step 3: Create Score Module
- **File:** `guess_game/score.py`
- **Action:** Create file with score management functions.
- **Contents:**
  - `load_scores(path="highscores.json") -> list` - loads JSON, returns sorted list or [].
  - `save_scores(scores: list, path="highscores.json") -> None` - writes top 5 to JSON.
  - `is_high_score(scores: list, attempts: int) -> bool` - checks if qualifies.
  - `add_score(scores: list, name: str, attempts: int) -> list` - inserts and returns top 5.
- **Dependencies:** None.
- **Verification:** Functions work with mocked file I/O.

---

## Step 4: Create Game Module
- **File:** `guess_game/game.py`
- **Action:** Create file with `GuessGame` class.
- **Contents:**
  - `class GuessGame`:
    - `__init__(self)` - loads scores, sets `self.target`, `self.attempts`.
    - `_generate_number() -> int` - returns `random.randint(1, 100)`.
    - `_get_guess() -> int` - prompts, validates, returns int.
    - `_play_round() -> int` - runs loop, returns attempts.
    - `_check_high_score(attempts: int) -> None` - checks score, prompts name, saves.
    - `run() -> None` - main game loop with replay.
- **Dependencies:** `ui.py`, `score.py`.
- **Verification:** Class instantiates; `_generate_number()` returns int in range.

---

## Step 5: Create Entry Point
- **File:** `guess_game/__main__.py`
- **Action:** Create file with `if __name__ == "__main__":` block.
- **Contents:**
  - Import `GuessGame` from `game.py`.
  - Instantiate and call `run()`.
- **Dependencies:** `game.py`.
- **Verification:** `python -m guess_game` starts the game.

---

## Step 6: Create Test Directory
- **File:** `tests/__init__.py`
- **Action:** Create empty file to make `tests` a package.
- **Dependencies:** None.
- **Verification:** Directory `tests/` exists with `__init__.py`.

---

## Step 7: Create Score Tests
- **File:** `tests/test_score.py`
- **Action:** Create file with unit tests for `score.py`.
- **Contents:**
  - 8 test cases covering load, save, is_high_score, add_score.
  - Use `unittest.mock` for file I/O and `tempfile` for real file tests.
- **Dependencies:** `score.py`.
- **Verification:** `python -m unittest tests.test_score` passes.

---

## Step 8: Create Game Tests
- **File:** `tests/test_game.py`
- **Action:** Create file with unit tests for `game.py`.
- **Contents:**
  - 8 test cases covering number generation, input validation, round logic.
  - Mock `random.randint` and `builtins.input`.
- **Dependencies:** `game.py`, `ui.py`.
- **Verification:** `python -m unittest tests.test_game` passes.

---

## Step 9: Run All Tests
- **Action:** Execute `python -m unittest discover -s tests -v`.
- **Verification:** All 16 tests pass with no failures or errors.

---

## Step 10: Smoke Test
- **Action:** Run `python -m guess_game` and play one round manually.
- **Verification:** Game starts, accepts guess, shows feedback, tracks attempts, asks replay.
