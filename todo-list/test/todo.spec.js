import { test, expect } from '@playwright/test';

test.describe('Todo List Application', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('TC-01: Page loads correctly', async ({ page }) => {
    // Page title
    await expect(page).toHaveTitle('memoriX - Todo');

    // Input field exists with correct placeholder
    const input = page.locator('#todo-input');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('placeholder', 'Add a new task...');

    // Add button exists
    const addBtn = page.locator('#add-btn');
    await expect(addBtn).toBeVisible();

    // Default task count shows 0 (uses plural "tasks" for 0)
    const taskCount = page.locator('#task-count');
    await expect(taskCount).toHaveText('0 tasks');

    // Filter buttons exist
    await expect(page.locator('.filter-btn[data-filter="all"]')).toBeVisible();
    await expect(page.locator('.filter-btn[data-filter="active"]')).toBeVisible();
    await expect(page.locator('.filter-btn[data-filter="completed"]')).toBeVisible();

    // Clear completed button exists (hidden when no completed tasks via CSS display:none)
    const clearBtn = page.locator('#clear-completed');
    await expect(clearBtn).toBeAttached();
    await expect(clearBtn).toBeHidden();
  });

  test('TC-02: Add a new task via Enter key', async ({ page }) => {
    const input = page.locator('#todo-input');

    await input.fill('Buy groceries');
    await input.press('Enter');

    // Task appears in list
    const task = page.locator('.todo-item');
    await expect(task).toHaveCount(1);
    await expect(task.locator('.todo-text')).toHaveText('Buy groceries');

    // Task count shows 1 (singular "task")
    await expect(page.locator('#task-count')).toHaveText('1 task');

    // Task is not marked completed
    await expect(task).not.toHaveClass(/completed/);
  });

  test('TC-03: Add multiple tasks', async ({ page }) => {
    const input = page.locator('#todo-input');
    const tasks = ['Task A', 'Task B', 'Task C'];

    for (const t of tasks) {
      await input.fill(t);
      await input.press('Enter');
    }

    // All three visible
    await expect(page.locator('.todo-item')).toHaveCount(3);

    // Count uses plural "tasks" for values other than 1
    await expect(page.locator('#task-count')).toHaveText('3 tasks');
  });

  test('TC-04: Reject empty input', async ({ page }) => {
    const input = page.locator('#todo-input');

    await input.press('Enter');

    await expect(page.locator('.todo-item')).toHaveCount(0);
    await expect(page.locator('#task-count')).toHaveText('0 tasks');
  });

  test('TC-05: Reject whitespace-only input', async ({ page }) => {
    const input = page.locator('#todo-input');

    await input.fill('   ');
    await input.press('Enter');

    await expect(page.locator('.todo-item')).toHaveCount(0);
    await expect(page.locator('#task-count')).toHaveText('0 tasks');
  });

  test('TC-06: Toggle task completion', async ({ page }) => {
    const input = page.locator('#todo-input');
    await input.fill('Toggle me');
    await input.press('Enter');

    const checkbox = page.locator('.todo-checkbox');
    const task = page.locator('.todo-item').first();

    // Click checkbox to mark completed
    await checkbox.check();
    await expect(task).toHaveClass(/completed/);
    await expect(checkbox).toBeChecked();

    // Click again to mark active
    await checkbox.uncheck();
    await expect(task).not.toHaveClass(/completed/);
    await expect(checkbox).not.toBeChecked();
  });

  test('TC-07: Delete a task', async ({ page }) => {
    const input = page.locator('#todo-input');
    await input.fill('Delete me');
    await input.press('Enter');

    await expect(page.locator('.todo-item')).toHaveCount(1);

    // Click delete button
    await page.locator('.delete-btn').click();

    await expect(page.locator('.todo-item')).toHaveCount(0);
    await expect(page.locator('#task-count')).toHaveText('0 tasks');
  });

  test('TC-08: Filter by All / Active / Completed', async ({ page }) => {
    const input = page.locator('#todo-input');
    for (const t of ['Task 1', 'Task 2', 'Task 3']) {
      await input.fill(t);
      await input.press('Enter');
    }

    // Complete the first task
    await page.locator('.todo-checkbox').first().check();

    // All filter — shows 3
    await page.locator('.filter-btn[data-filter="all"]').click();
    await expect(page.locator('.todo-item')).toHaveCount(3);

    // Active filter — shows 2
    await page.locator('.filter-btn[data-filter="active"]').click();
    await expect(page.locator('.todo-item')).toHaveCount(2);

    // Completed filter — shows 1
    await page.locator('.filter-btn[data-filter="completed"]').click();
    await expect(page.locator('.todo-item')).toHaveCount(1);

    // Active filter button gets highlighted class
    await page.locator('.filter-btn[data-filter="active"]').click();
    await expect(page.locator('.filter-btn[data-filter="active"]')).toHaveClass(/active/);
  });

  test('TC-09: Clear completed', async ({ page }) => {
    const input = page.locator('#todo-input');
    for (const t of ['Task 1', 'Task 2', 'Task 3']) {
      await input.fill(t);
      await input.press('Enter');
    }

    // Complete first two tasks
    const checkboxes = page.locator('.todo-checkbox');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    // Click clear completed
    await page.locator('#clear-completed').click();

    // Only the active task remains; count uses singular "task"
    await expect(page.locator('.todo-item')).toHaveCount(1);
    await expect(page.locator('#task-count')).toHaveText('1 task');
  });

  test('TC-10: Persistence (localStorage)', async ({ page }) => {
    const input = page.locator('#todo-input');
    await input.fill('Persist me');
    await input.press('Enter');

    await page.reload();

    // Tasks restored from localStorage
    await expect(page.locator('.todo-item')).toHaveCount(1);
    await expect(page.locator('.todo-text')).toHaveText('Persist me');
  });

  test('TC-11: Add button click', async ({ page }) => {
    const input = page.locator('#todo-input');
    await input.fill('Button add');

    // Click the add button (plus icon)
    await page.locator('#add-btn').click();

    await expect(page.locator('.todo-item')).toHaveCount(1);
    await expect(page.locator('.todo-text')).toHaveText('Button add');
  });

  test('TC-12: Task counter accuracy', async ({ page }) => {
    const input = page.locator('#todo-input');
    const taskCount = page.locator('#task-count');

    // Adding increases counter (singular "task" for 1)
    await input.fill('Task X');
    await input.press('Enter');
    await expect(taskCount).toHaveText('1 task');

    await input.fill('Task Y');
    await input.press('Enter');
    await expect(taskCount).toHaveText('2 tasks');

    // Completing a task decreases counter
    await page.locator('.todo-checkbox').first().check();
    await expect(taskCount).toHaveText('1 task');

    // Deleting an active task decreases counter to zero (plural "tasks")
    await page.locator('.todo-item .delete-btn').last().click();
    await expect(taskCount).toHaveText('0 tasks');

    // Clearing completed resets counter
    await input.fill('Temp');
    await input.press('Enter');
    await page.locator('.todo-checkbox').first().check();
    await page.locator('#clear-completed').click();
    await expect(taskCount).toHaveText('0 tasks');
  });

});
