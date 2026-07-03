# Dev Plan: Todo List

## File Structure
```
todo-list/
  index.html    -- Main HTML file (includes all markup)
  style.css     -- All styles (CSS custom properties, Tailwind-like utility via custom CSS, glassmorphism, animations)
  script.js     -- All JavaScript (ES6+, localStorage, event delegation, filtering)
```

## Implementation Contract

### `index.html`
- DOCTYPE html5, lang="en"
- Head: charset, viewport, title "memoriX - Todo", Google Fonts Inter (400,500,600,700), FontAwesome 6 CDN, link to style.css
- Body: `<div id="app">` container
  - `.todo-card`: centered glass card
    - `.todo-header`: title "memoriX" + "todo" subtitle, `.task-count` showing remaining count
    - `.todo-input-row`: `<input type="text" id="todo-input" placeholder="Add a new task..." aria-label="New task">` + `<button id="add-btn" aria-label="Add task"><i class="fas fa-plus"></i></button>`
    - `<ul id="todo-list" role="list"></ul>`
    - `.todo-footer`: filter buttons (All, Active, Completed) + `.clear-completed` button
- Script tag loading script.js (defer)

### `style.css`
- CSS reset, box-sizing border-box
- `:root` custom properties: --bg-gradient-start, --bg-gradient-end, --card-bg, --card-border, --text-primary, --text-secondary, --accent, --accent-hover, --danger, --completed-opacity
- Body: full viewport height, dark gradient background, font-family 'Inter', display flex, align center, justify center, padding
- `.todo-card`: glassmorphism (background: rgba(255,255,255,0.05), backdrop-filter: blur(16px), border: 1px solid rgba(255,255,255,0.1), border-radius: 24px, padding, max-width: 480px, width: 100%, box-shadow)
- `.todo-header`: flex, space-between, align-center; title: font-size 1.5rem, font-weight 700; task-count: font-size 0.85rem, color text-secondary
- `.todo-input-row`: flex, gap, input: flex 1, padding 14px 18px, border-radius 14px, border, background rgba(255,255,255,0.06), color white, font-size 1rem, outline; button: width 48px, height 48px, border-radius 50%, background accent, color white, border none, cursor pointer, transition transform 0.2s; hover: scale(1.05)
- Task items: `.todo-item` flex, align-center, padding 12px 16px, margin-bottom 8px, border-radius 16px, transition all 0.3s, hover: background rgba(255,255,255,0.05), transform translateX(4px)
  - `.todo-checkbox`: custom styled checkbox (hidden default, custom checkmark via pseudo-element)
  - `.todo-text`: flex 1, margin 0 12px, transition; `.completed .todo-text`: text-decoration line-through, opacity 0.5
  - `.delete-btn`: background none, border none, color danger, cursor pointer, opacity 0, transition; `.todo-item:hover .delete-btn`: opacity 1
- Filter bar: flex, gap 8px; `.filter-btn`: background none, border none, color text-secondary, padding 6px 14px, border-radius 20px, cursor pointer, transition; `.filter-btn.active`: background accent, color white
- `.clear-completed`: background none, border none, color danger, cursor pointer, font-size 0.85rem, display none; visible when completed exist
- Animations: `@keyframes slideIn` (translateY -10px to 0, opacity 0 to 1)
- Responsive: @media max-width 520px — adjust padding, font-size

### `script.js`
- `let tasks = []` (array of `{ id, text, completed, createdAt }`)
- `let currentFilter = 'all'`
- On DOMContentLoaded:
  - Load from localStorage (`JSON.parse(localStorage.getItem('memorix-todos')) || []`)
  - Render tasks
  - Event listeners
- `saveTasks()`: `localStorage.setItem('memorix-todos', JSON.stringify(tasks))`
- `renderTasks()`: filter tasks by currentFilter, generate `<li>` elements, append to `#todo-list`, update counter, show/hide clear-completed
- `addTask(text)`: trim, if empty return; create task object, push, save, render, scroll to bottom
- `toggleTask(id)`: find task, toggle completed, save, render
- `deleteTask(id)`: filter out, save, render
- `clearCompleted()`: filter out completed, save, render
- Event delegation on `#todo-list` for click on `.todo-checkbox` (toggle) and `.delete-btn` (delete)
- Event delegation on `.todo-footer` for click on `.filter-btn` (set currentFilter, render)
- Enter key on `#todo-input` triggers addTask

## Browser Test
- Open `todo-list/index.html` in a browser to verify.
