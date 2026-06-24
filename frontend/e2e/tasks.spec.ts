import { test, expect } from '@playwright/test'

const PROOF_DIR = '/workspace/proof'

// These tests run against the live Go backend (proxied through Vite's /api).
// They seed tasks via the UI, then verify the full CRUD flow end-to-end and
// capture screenshots of the task list with tasks visible.

test.beforeEach(async ({ request }) => {
  // Clean slate: delete any existing tasks so the run is deterministic.
  const res = await request.get('/api/tasks')
  const tasks = (await res.json()) as Array<{ id: number }>
  for (const t of tasks) {
    await request.delete(`/api/tasks/${t.id}`)
  }
})

test('loads the app and shows the heading', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Task Manager' })).toBeVisible()
  await expect(page.getByText('No tasks yet — add your first one below.')).toBeVisible()
  await page.screenshot({ path: `${PROOF_DIR}/01-empty-state.png`, fullPage: true })
})

test('adds tasks and shows them in the list', async ({ page }) => {
  await page.goto('/')

  const seed = [
    { title: 'Write project proposal', desc: 'Draft and share with the team' },
    { title: 'Review pull requests', desc: 'Backend + frontend changes' },
    { title: 'Plan sprint demo', desc: '' },
  ]

  for (const s of seed) {
    await page.getByLabel('Task title').fill(s.title)
    if (s.desc) await page.getByLabel('Task description').fill(s.desc)
    await page.getByRole('button', { name: 'Add Task' }).click()
    await expect(page.getByText(s.title)).toBeVisible()
  }

  const items = page.getByTestId('task-item')
  await expect(items).toHaveCount(3)

  // Screenshot of the task list with tasks visible (acceptance criterion).
  await page.screenshot({ path: `${PROOF_DIR}/02-task-list.png`, fullPage: true })
})

test('toggles a task done via checkbox', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Task title').fill('Finish documentation')
  await page.getByLabel('Task description').fill('Cover setup and usage')
  await page.getByRole('button', { name: 'Add Task' }).click()

  const item = page.getByTestId('task-item').first()
  const checkbox = item.getByRole('checkbox')

  await expect(checkbox).not.toBeChecked()
  await checkbox.check()
  await expect(checkbox).toBeChecked()
  // The done task gets a line-through style via the .task-done class.
  await expect(item).toHaveClass(/task-done/)

  await page.screenshot({ path: `${PROOF_DIR}/03-task-toggled.png`, fullPage: true })
})

test('deletes a task', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Task title').fill('Temporary task')
  await page.getByRole('button', { name: 'Add Task' }).click()
  await expect(page.getByTestId('task-item')).toHaveCount(1)

  await page.getByRole('button', { name: 'Delete "Temporary task"' }).click()
  await expect(page.getByTestId('task-item')).toHaveCount(0)
  await expect(page.getByText('Nothing here yet.')).toBeVisible()

  await page.screenshot({ path: `${PROOF_DIR}/04-after-delete.png`, fullPage: true })
})

test('persists tasks across reload (refresh after mutation)', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Task title').fill('Persistent task')
  await page.getByRole('button', { name: 'Add Task' }).click()
  await expect(page.getByText('Persistent task')).toBeVisible()

  await page.reload()
  await expect(page.getByText('Persistent task')).toBeVisible()
})
