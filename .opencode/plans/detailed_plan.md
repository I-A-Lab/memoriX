# Detailed Step-by-Step Implementation Plan

## Files to Create

| File | Purpose |
|------|---------|
| `todo-app/index.html` | Single-file SPA -- all HTML, CSS (Tailwind), and JS |
| `todo-app/test.html` | Standalone test runner with 5 unit tests |

---

## Step 1: Create `todo-app/index.html` -- Document Head

- `<!DOCTYPE html>` with `lang="en"`.
- `<meta charset>`, `<meta viewport>` for responsive.
- `<title>`: "Todo List".
- **CDN imports** (in `<head>`):
  - `<script src="https://cdn.tailwindcss.com"></script>`
  - `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">`
  - `<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />`
- Tailwind config block: `<script>tailwind.config = { theme: { extend: { fontFamily: { sans: ['Inter', 'sans-serif'] } } } }</script>`

## Step 2: Create `todo-app/index.html` -- Body HTML

Structure (inside `<body class="bg-gray-950 min-h-screen flex items-center justify-center p-4 font-sans">`):

- **Outer card** `div`: `max-w-lg w-full mx-auto bg-white/5 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8`
  - **Header**: `<h1>` "Todo List" (text-2xl font-bold text-white) + `<p>` subtitle (text-gray-400 text-sm).
  - **Input row** `div`: flex row with:
    - `<input id="taskInput">` -- `flex-1 bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition`
    - `<button id="addBtn">` -- `<i class="fas fa-plus">` + " Add", `bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-6 py-3 font-medium transition`
  - **Task list** `<ul id="taskList">` -- container for dynamic items.
  - **Empty state** `<div id="emptyState">` -- `<i class="fas fa-clipboard-list">` + "No tasks yet. Add one above!", `text-gray-500 text-center py-8`.

## Step 3: Create `todo-app/index.html` -- JavaScript (Data Layer)

Inside `<script>` at bottom of body:

- **Constants**: `const STORAGE_KEY = 'todo-app-tasks'`
- **`loadTasks()`**: Returns `JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')`.
- **`saveTasks(tasks)`**: `localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))`.
- **`generateId()`**: Returns `Date.now().toString(36) + Math.random().toString(36).slice(2)`.
- **`createTask(text)`**: Returns `{ id: generateId(), text, completed: false, createdAt: Date.now() }`.

## Step 4: Create `todo-app/index.html` -- JavaScript (Render)

- **`renderTasks(tasks, listEl, emptyEl)`**:
  - Clear `listEl.innerHTML`.
  - If `tasks.length === 0`, show `emptyEl`, return. Else hide `emptyEl`.
  - For each task, create `<li>` with classes `group flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-all duration-200`.
  - Inside each `<li>`:
    - `<input type="checkbox">` -- checked if `task.completed`, classes `w-5 h-5 rounded accent-indigo-500 cursor-pointer`.
    - `<span class="flex-1 text-white cursor-pointer transition-all duration-200">` -- text content, conditional classes: `line-through text-gray-500` if completed.
    - `<button class="delete-btn opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all duration-200">` -- `<i class="fas fa-trash-alt">`.

## Step 5: Create `todo-app/index.html` -- JavaScript (Interactions)

- **DOMContentLoaded** handler: Load tasks, get DOM refs (`#taskInput`, `#addBtn`, `#taskList`, `#emptyState`), call `renderTasks()`.
- **addTask()** helper: Read input, trim, if empty return; `tasks.push(createTask(text))`, clear input, `saveTasks(tasks)`, `renderTasks()`.
- **Event: Enter key** on `#taskInput` -> `addTask()`.
- **Event: Click** on `#addBtn` -> `addTask()`.
- **Event delegation** on `#taskList`:
  - `change` on checkbox -> find task by ID, toggle `.completed`, save, render.
  - `click` on delete button -> find task by ID, filter out, save, render.
  - `dblclick` on span -> replace with `<input>` (inline edit), on Enter/blur -> update task text (or remove if empty), save, render.

## Step 6: Create `todo-app/test.html` -- Test Runner

- Standalone HTML with inline `<script>` that defines the same `generateId`, `saveTasks`, `loadTasks`, `createTask` functions.
- 5 test functions:
  - `test_generateId_returns_unique` -- assert two calls return different values.
  - `test_saveLoad_roundtrip` -- save mock data, load, assert deep equality.
  - `test_loadTasks_empty_returns_array` -- clear storage, load, assert `Array.isArray(result) && result.length === 0`.
  - `test_createTask_shape` -- assert `id` is string, `text` is string, `completed` is boolean, `createdAt` is number.
  - `test_toggleCompleted` -- create task, flip `completed`, assert `true`.
- Each test: try/catch, `console.log` pass/fail, append result `<div>` to `#results`.
- Page displays "All 5 tests passed" or failure details.

---

## Summary

| Step | File | What |
|------|------|------|
| 1-5 | `todo-app/index.html` | Full SPA with HTML + Tailwind + JS |
| 6 | `todo-app/test.html` | 5 unit tests for data functions |
