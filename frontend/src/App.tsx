import { useCallback, useEffect, useState } from 'react'
import {
  type Task,
  createTask,
  deleteTask,
  listTasks,
  updateTask,
} from './api'

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // refresh re-fetches the full task list. Called after every mutation so the
  // UI always reflects server state.
  const refresh = useCallback(async () => {
    try {
      const data = await listTasks()
      setTasks(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = title.trim()
    if (!trimmed) return
    setSubmitting(true)
    try {
      await createTask({ title: trimmed, description: description.trim() })
      setTitle('')
      setDescription('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add task')
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggle = async (task: Task) => {
    try {
      await updateTask(task.id, { done: !task.done })
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task')
    }
  }

  const handleDelete = async (task: Task) => {
    try {
      await deleteTask(task.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task')
    }
  }

  const remaining = tasks.filter((t) => !t.done).length

  return (
    <main className="app">
      <header className="app-header">
        <h1>Task Manager</h1>
        <p className="subtitle">
          {tasks.length === 0
            ? 'No tasks yet — add your first one below.'
            : `${remaining} of ${tasks.length} remaining`}
        </p>
      </header>

      <form className="task-form" onSubmit={handleAdd}>
        <input
          className="input"
          type="text"
          placeholder="Task title (required)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-label="Task title"
        />
        <input
          className="input"
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          aria-label="Task description"
        />
        <button
          className="btn btn-primary"
          type="submit"
          disabled={submitting || title.trim() === ''}
        >
          {submitting ? 'Adding…' : 'Add Task'}
        </button>
      </form>

      {error && <div className="error" role="alert">{error}</div>}

      {loading ? (
        <p className="empty">Loading tasks…</p>
      ) : tasks.length === 0 ? (
        <p className="empty">Nothing here yet.</p>
      ) : (
        <ul className="task-list">
          {tasks.map((task) => (
            <li
              key={task.id}
              className={`task ${task.done ? 'task-done' : ''}`}
              data-testid="task-item"
            >
              <label className="task-main">
                <input
                  type="checkbox"
                  className="checkbox"
                  checked={task.done}
                  onChange={() => handleToggle(task)}
                  aria-label={`Mark "${task.title}" as ${task.done ? 'not done' : 'done'}`}
                />
                <span className="task-text">
                  <span className="task-title">{task.title}</span>
                  {task.description && (
                    <span className="task-desc">{task.description}</span>
                  )}
                </span>
              </label>
              <button
                className="btn btn-delete"
                type="button"
                onClick={() => handleDelete(task)}
                aria-label={`Delete "${task.title}"`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
