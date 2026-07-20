# Development Plan - Todo List Web App

## Architecture

Single-file SPA (`index.html`) with no build step. All logic lives in one file.

## Implementation Steps

### Step 1: HTML Skeleton
- Create `todo-app/index.html` with `<!DOCTYPE html>`, `<head>`, and `<body>`.
- Import Tailwind CSS CDN, Google Fonts (Inter), and Font Awesome 6 CDN.
- Set up the dark background (`bg-gray-950`) and centered layout.

### Step 2: UI Structure
- Build the main glassmorphism card container (`backdrop-blur`, `bg-white/5`, `rounded-2xl`, `shadow-2xl`).
- Header with app title and subtitle.
- Input area: text input + add button, styled with focus ring animations.
- Task list container (ul/div) for dynamic task items.
- Empty state message shown when no tasks exist.

### Step 3: Core JavaScript - Data Layer
- Define `loadTasks()` -- reads from `localStorage`, returns array.
- Define `saveTasks(tasks)` -- writes to `localStorage`.
- Define `generateId()` -- returns a unique ID (`Date.now().toString(36) + random`).
- Define initial in-memory `tasks` array loaded from storage on DOMContentLoaded.

### Step 4: Core JavaScript - Render
- Define `renderTasks()` -- clears the list container and re-renders all tasks.
- Each task item: checkbox, editable text span, delete button.
- Apply conditional classes for completed state (strikethrough, opacity).
- Show/hide empty state based on task count.
- Attach event listeners during render (or use event delegation).

### Step 5: Core JavaScript - Interactions
- **Add task**: Listen for Enter key and button click on the input. Validate non-empty, create task object, push to array, save, re-render.
- **Toggle complete**: Listen for change on checkbox. Toggle `completed` boolean, save, re-render.
- **Delete task**: Listen for click on delete button. Remove from array by ID, save, re-render with fade animation.
- **Inline edit**: Listen for dblclick on task text. Replace span with input, pre-fill value. On Enter/blur, update text (or discard if empty), save, re-render.

### Step 6: Animations & Polish
- CSS transitions on task items: `transition-all duration-200`.
- Hover effect on task row (subtle background brighten).
- Delete button appears on hover (`opacity-0` to `opacity-100` on group hover).
- Fade-in animation for newly added tasks.
- Input focus ring glow effect.

## Key Dependencies (CDN)

| Library | URL |
|---------|-----|
| Tailwind CSS | `https://cdn.tailwindcss.com` |
| Google Fonts (Inter) | `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap` |
| Font Awesome 6 | `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css` |
