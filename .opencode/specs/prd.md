# PRD: Todo List Web Application (HTML/CSS/JS)

## 1. Purpose
A standalone, visually stunning todo list web application built with vanilla HTML, CSS, and JavaScript. No frameworks or build tools required. The app runs directly in the browser from a single HTML file (with embedded/external CSS and JS).

## 2. Functional Requirements

### 2.1 Task Management
- **Add tasks**: User can type a task description and press Enter or click an Add button to create a new todo item.
- **Mark complete**: Clicking a checkbox or the task text toggles its completed state (strikethrough + dimmed style).
- **Delete tasks**: Each task has a delete button (trash icon) to remove it permanently.
- **Clear completed**: A button to remove all completed tasks at once.

### 2.2 Filtering & Display
- **All**: Show every task.
- **Active**: Show only incomplete tasks.
- **Completed**: Show only completed tasks.
- **Task counter**: Display the count of remaining (active) items.

### 2.3 Persistence
- All tasks persist across page reloads using `localStorage`.
- Task state (text, completed status, creation timestamp) is saved and restored.

### 2.4 Validation
- Empty or whitespace-only task input is rejected.
- Duplicate task text is allowed (no deduplication required).

## 3. Non-Functional Requirements

### 3.1 Browser Support
- Works in latest Chrome, Firefox, Safari, and Edge.
- No external build tools or npm dependencies.

### 3.2 Performance
- Instant load and response.
- No external API calls; everything runs client-side.

### 3.3 File Structure
- Single file `todo-list/index.html` containing all HTML, CSS, and JS (inlined for simplicity).
- OR three separate files: `todo-list/index.html`, `todo-list/style.css`, `todo-list/script.js` — developer's choice.

### 3.4 Code Quality
- Clean, readable, well-commented code.
- Semantic HTML5 elements.
- CSS custom properties for theming.
- Vanilla ES6+ JavaScript (no jQuery).

## 4. Design & UI Mandate (Modern Premium)

### 4.1 Visual Style
- **Dark mode by default** with a refined dark gradient background (e.g., `#0f0f1a` to `#1a1a2e`).
- **Glassmorphism cards** (`backdrop-filter: blur(12px)`, semi-transparent background, subtle border).
- **Typography**: Use Google Fonts "Inter" for clean, modern text.
- **Icons**: Use FontAwesome 6 (free CDN) for the add button, delete button, and filter icons.

### 4.2 Layout & Components
- Centered card layout (max-width ~480px) with generous spacing and rounded corners (`rounded-2xl` equivalent).
- Header with app title and task count.
- Input row: text input + round accent-colored add button (with plus icon).
- Task list with smooth hover effects, slide-in animations for new items.
- Filter bar below the list with active state indicators.
- Clear completed button (appears only when completed tasks exist).

### 4.3 Animations & Interactions
- Smooth fade/slide transition when adding or removing tasks.
- Checkbox toggle with a subtle scale animation.
- Hover state: slight lift and glow on task items.
- Filter button active state with underline or background highlight.

### 4.4 Accessibility
- Proper `aria-label` on buttons and input.
- `role="list"` on the task list.
- Focus management on the input field after adding a task.
