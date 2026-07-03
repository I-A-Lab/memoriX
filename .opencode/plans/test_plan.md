# Test Plan: Todo List

## Testing Approach
Since this is a vanilla HTML/CSS/JS app with no Node.js test framework, tests will be:
1. **Automated Playwright tests** (if Playwright is available) OR
2. **Manual test checklist** below

Given the environment constraints, we will create a **Playwright test script** at `todo-list/test/todo.spec.js` that runs against a local file server.

## Test File Structure
```
todo-list/
  test/
    todo.spec.js   -- Playwright test spec
```

## Test Cases

### TC-01: Page loads correctly
- Title is "memoriX - Todo"
- Input field exists with correct placeholder
- Add button exists
- Default task count is 0
- Filter buttons (All, Active, Completed) exist

### TC-02: Add a new task
- Type "Buy groceries" and press Enter
- Task appears in the list
- Task count shows 1
- Task text is "Buy groceries"
- Task is not marked completed

### TC-03: Add multiple tasks
- Add "Task A", "Task B", "Task C"
- All three appear in the list
- Count shows 3

### TC-04: Reject empty input
- Press Enter with empty input
- No new task added
- Count remains unchanged

### TC-05: Reject whitespace-only input
- Type spaces and press Enter
- No new task added

### TC-06: Toggle task completion
- Add a task
- Click checkbox → task becomes completed (strikethrough style)
- Click checkbox again → task becomes active again

### TC-07: Delete a task
- Add a task
- Click delete button → task is removed
- Count decreases

### TC-08: Filter by All / Active / Completed
- Add 3 tasks, mark 1 as completed
- Filter "All" shows all 3
- Filter "Active" shows 2
- Filter "Completed" shows 1
- Active filter button is highlighted
- Completed filter button is highlighted when selected

### TC-09: Clear completed
- Add 3 tasks, mark 2 as completed
- Click "Clear completed"
- Only the active task remains
- Completed count is 0

### TC-10: Persistence (localStorage)
- Add several tasks
- Reload the page
- All tasks are restored
- Completed state is preserved

### TC-11: Add button click
- Type text and click the add button (with plus icon)
- Task is added

### TC-12: Task counter accuracy
- Counter shows number of active (incomplete) tasks
- Adding a task increases counter
- Completing a task decreases counter
- Deleting an active task decreases counter
- Deleting a completed task does not change counter
- Clearing completed resets counter (since completed are removed)

## Execution Status

All 12 Playwright tests pass successfully:
- `todo-list/playwright.config.js` -- Playwright config (chromium, headless)
- `todo-list/test/todo.spec.js` -- 12 test cases implemented and passing

## How to Run Tests
```bash
cd todo-list
npx playwright test
```
