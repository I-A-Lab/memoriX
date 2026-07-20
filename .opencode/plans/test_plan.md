# Test Plan - Todo List Web App

## Strategy

Since this is a single HTML file with vanilla JS (no build tool, no Node modules), testing will be done via lightweight inline JavaScript assertions that validate core business logic functions. The test file will be a standalone HTML file that can be opened in a browser.

## Test Scope

Only core utility/data functions are tested -- no DOM or UI tests (keeping it fast and lightweight).

## Test Cases (5 max)

### Test 1: generateId() returns unique values
- Call `generateId()` twice and assert the two values are not equal.

### Test 2: saveTasks() and loadTasks() round-trip
- Define a mock task array, call `saveTasks()`, then `loadTasks()`, assert deep equality.

### Test 3: loadTasks() returns empty array when localStorage is empty
- Clear localStorage, call `loadTasks()`, assert result is an empty array.

### Test 4: Task object shape validation
- Create a task using the app's creation logic, assert it has `id`, `text`, `completed`, and `createdAt` properties with correct types.

### Test 5: Toggle completed flips boolean
- Create a task with `completed: false`, apply toggle logic, assert `completed` is `true`.

## Test File

```
todo-app/test.html   -- Standalone HTML file with inline JS test runner
```

The test file will log results to the console and display pass/fail in the page body. No external test framework required.
