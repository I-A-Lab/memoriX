# Product Requirements Document (PRD) - Todo List Web App

## 1. Overview

A modern, single-page Todo List web application built with vanilla HTML, JavaScript, and Tailwind CSS. The app delivers a visually stunning dark-themed UI with glassmorphism and smooth animations, persisted entirely in the browser via LocalStorage.

## 2. Goals

- Provide a fast, beautiful, and intuitive task management experience.
- Zero backend dependency -- all data lives in the browser.
- Demonstrate modern UI/UX patterns with minimal dependencies (Tailwind CSS via CDN).

## 3. Target Users

- Individuals who need a quick, local task tracker in the browser.
- No account or login required.

## 4. Features

### 4.1 Add Task
- User can type a task description in an input field and press Enter or click an "Add" button.
- Empty submissions are rejected with subtle inline feedback.

### 4.2 Mark Complete / Incomplete
- Each task has a checkbox. Clicking it toggles the completed state.
- Completed tasks display a strikethrough style and reduced opacity.

### 4.3 Edit Task
- Double-clicking a task text enters inline edit mode.
- Pressing Enter or clicking away saves the edit.
- Empty edits discard the change.

### 4.4 Delete Task
- Each task has a delete button (icon) visible on hover.
- Clicking it removes the task with a fade-out animation.

### 4.5 Persistence
- All tasks are stored in `localStorage` under a single key.
- Tasks load automatically on page open.
- Data shape: `{ id: string, text: string, completed: boolean, createdAt: number }[]`

### 4.6 Visual Design
- Dark background with a centered glassmorphism card container.
- Tailwind CSS via CDN for styling.
- Google Fonts (Inter) for clean typography.
- Lucide or Font Awesome icons for add, delete, and empty-state visuals.
- Smooth CSS transitions for hover states, task completion, and deletion.
- Responsive layout that works on mobile and desktop.

## 5. Non-Goals

- User authentication or cloud sync.
- Collaborative or shared lists.
- Categories, tags, priorities, or due dates (out of scope for v1).
- Server-side logic or database.

## 6. Success Metrics

- App loads and renders in under 100ms.
- All CRUD operations are instant with no perceivable lag.
- Data survives browser refresh (LocalStorage persistence works).

## 7. Tech Stack

| Layer | Technology |
|-------|-----------|
| Markup | HTML5 |
| Styling | Tailwind CSS (CDN) |
| Logic | Vanilla JavaScript (ES6+) |
| Icons | Font Awesome 6 (CDN) |
| Fonts | Google Fonts - Inter |
| Storage | localStorage |

## 8. File Structure

```
todo-app/
  index.html    -- Single file containing all HTML, CSS (Tailwind), and JS
```

A single `index.html` file is sufficient for this scope. No build step required.
