// --- State ---
let tasks = [];
let currentFilter = 'all';

// --- DOM References ---
const todoInput = document.getElementById('todo-input');
const todoList = document.getElementById('todo-list');
const taskCount = document.getElementById('task-count');
const clearCompletedBtn = document.getElementById('clear-completed');
const footerEl = document.querySelector('.todo-footer');
const addBtn = document.getElementById('add-btn');

// --- Persistence ---
function saveTasks() {
  localStorage.setItem('memorix-todos', JSON.stringify(tasks));
}

function loadTasks() {
  try {
    const stored = localStorage.getItem('memorix-todos');
    tasks = stored ? JSON.parse(stored) : [];
  } catch {
    tasks = [];
  }
}

// --- Render ---
function renderTasks() {
  // Filter tasks based on current filter
  const filtered = tasks.filter((task) => {
    if (currentFilter === 'active') return !task.completed;
    if (currentFilter === 'completed') return task.completed;
    return true; // 'all'
  });

  // Build list HTML
  todoList.innerHTML = filtered
    .map(
      (task) => `
    <li class="todo-item${task.completed ? ' completed' : ''}" data-id="${task.id}">
      <input type="checkbox" class="todo-checkbox" ${task.completed ? 'checked' : ''} aria-label="Mark task as ${task.completed ? 'incomplete' : 'complete'}">
      <span class="todo-text">${escapeHtml(task.text)}</span>
      <button class="delete-btn" aria-label="Delete task"><i class="fas fa-times"></i></button>
    </li>
  `
    )
    .join('');

  // Update task count
  const remaining = tasks.filter((t) => !t.completed).length;
  taskCount.textContent = `${remaining} task${remaining !== 1 ? 's' : ''}`;

  // Show/hide clear-completed button
  const hasCompleted = tasks.some((t) => t.completed);
  clearCompletedBtn.classList.toggle('visible', hasCompleted);

  // Update active filter button styling
  document.querySelectorAll('.filter-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.filter === currentFilter);
  });
}

// --- Helpers ---
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// --- Actions ---
function addTask(text) {
  const trimmed = text.trim();
  if (!trimmed) return;

  const task = {
    id: Date.now(),
    text: trimmed,
    completed: false,
    createdAt: new Date().toISOString(),
  };

  tasks.push(task);
  saveTasks();
  renderTasks();
  todoInput.value = '';
  todoInput.focus();
}

function toggleTask(id) {
  const task = tasks.find((t) => t.id === id);
  if (!task) return;
  task.completed = !task.completed;
  saveTasks();
  renderTasks();
}

function deleteTask(id) {
  tasks = tasks.filter((t) => t.id !== id);
  saveTasks();
  renderTasks();
}

function clearCompleted() {
  tasks = tasks.filter((t) => !t.completed);
  saveTasks();
  renderTasks();
}

// --- Event Binding ---
function initEvents() {
  // Add task on button click
  addBtn.addEventListener('click', () => addTask(todoInput.value));

  // Add task on Enter key
  todoInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      addTask(todoInput.value);
    }
  });

  // Event delegation: checkbox toggle and delete
  todoList.addEventListener('click', (e) => {
    const li = e.target.closest('.todo-item');
    if (!li) return;
    const id = Number(li.dataset.id);

    if (e.target.closest('.todo-checkbox')) {
      toggleTask(id);
    } else if (e.target.closest('.delete-btn')) {
      deleteTask(id);
    }
  });

  // Event delegation: filter buttons
  footerEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    currentFilter = btn.dataset.filter;
    renderTasks();
  });

  // Clear completed
  clearCompletedBtn.addEventListener('click', clearCompleted);
}

// --- Bootstrap ---
document.addEventListener('DOMContentLoaded', () => {
  loadTasks();
  renderTasks();
  initEvents();
});
