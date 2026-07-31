# Product Requirements Document: Guess Game (Python CLI, Dark Theme)

## Project Overview
- **Project ID:** `guess-game-v2`
- **Type:** Python CLI Number Guessing Game
- **Style:** Dark Theme ANSI terminal UI
- **Complexity:** Very Simple (5-minute play session)

---

## 1. Functional Requirements

### FR-1: Game Initialization
- The game shall generate a random integer between 1 and 100 (inclusive).
- The game shall display a welcome banner and basic instructions.

### FR-2: Guess Input
- The game shall prompt the user to enter a numeric guess.
- The game shall validate that input is an integer within the range 1-100.
- The game shall re-prompt on invalid input with a clear error message.

### FR-3: Feedback
- After each valid guess, the game shall display one of:
  - "Too low! Try again."
  - "Too high! Try again."
  - "Congratulations! You guessed it!" (on correct guess)

### FR-4: Attempt Counter
- The game shall track and display the number of attempts after each guess.
- The game shall display total attempts upon successful guess.

### FR-5: Score Tracking
- The game shall maintain a high score file (`highscores.json`) in the current directory.
- The file shall store a list of the top 5 scores (lowest attempts = best).
- After a win, the game shall check if the current score qualifies and prompt for the player's name (3-letter initials).
- The game shall display the leaderboard after each game session.

### FR-6: Replay
- After each round, the game shall ask if the player wants to play again.
- On "yes", generate a new random number and reset the attempt counter.
- On "no", display a goodbye message and exit.

### FR-7: Session Persistence
- High scores persist across sessions via `highscores.json`.

---

## 2. UI/UX Design (Dark Theme ANSI)

### UD-1: Color Palette
- **Background:** Black terminal (default).
- **Header/Title:** Bright cyan (`\033[96m`).
- **Instructions:** Dim white (`\033[90m`).
- **Prompts:** Bright yellow (`\033[93m`).
- **Feedback (Too low/high):** Bright magenta (`\033[95m`).
- **Success:** Bright green (`\033[92m`).
- **Error:** Bright red (`\033[91m`).
- **Leaderboard Header:** Bright blue (`\033[94m`).
- **Leaderboard Entries:** White (`\033[97m`).

### UD-2: Layout
- Clear separation between sections using divider lines (e.g., `---` in cyan).
- Centered title using simple padding.
- Indented feedback messages.
- Leaderboard displayed in a formatted table with columns: Rank, Name, Attempts.

### UD-3: Responsiveness
- Works on any terminal width >= 60 characters.
- No fixed-width requirement beyond that.

---

## 3. Non-Functional Requirements

### NFR-1: Dependencies
- Python 3.8+ only. No external packages.
- Use only `random`, `json`, `os`, `sys`, `pathlib` from standard library.

### NFR-2: File Structure
```
guess_game/
    __init__.py
    game.py          # Main game logic
    score.py         # High score management
    ui.py            # ANSI color and display helpers
    __main__.py      # Entry point
tests/
    test_game.py
    test_score.py
```

### NFR-3: Error Handling
- Graceful handling of keyboard interrupt (Ctrl+C) with a clean exit.
- If `highscores.json` is corrupt, reset to empty leaderboard and continue.

### NFR-4: Testing
- Unit tests for game logic, score management, and input validation.
- Aim for >90% coverage on core modules.

---

## 4. Success Criteria
- Game runs with `python -m guess_game`.
- Dark theme ANSI output is visually clean and readable.
- High scores persist across sessions.
- All tests pass.
- Zero external dependencies.
