// API client for the Go task backend. All requests go through /api, which the
// Vite dev server proxies to http://localhost:8080.

export interface Task {
  id: number
  title: string
  description: string
  done: boolean
  created_at: string
}

const BASE = '/api/tasks'

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `request failed with status ${res.status}`
    try {
      const body = await res.json()
      if (body && typeof body.error === 'string') message = body.error
    } catch {
      // ignore JSON parse errors; use the default message
    }
    throw new Error(message)
  }
  // 204 No Content has no body to parse.
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export async function listTasks(): Promise<Task[]> {
  return handle<Task[]>(await fetch(BASE))
}

export async function createTask(input: {
  title: string
  description?: string
}): Promise<Task> {
  return handle<Task>(
    await fetch(BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}

export async function updateTask(
  id: number,
  patch: Partial<Pick<Task, 'title' | 'description' | 'done'>>,
): Promise<Task> {
  return handle<Task>(
    await fetch(`${BASE}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  )
}

export async function deleteTask(id: number): Promise<void> {
  return handle<void>(
    await fetch(`${BASE}/${id}`, { method: 'DELETE' }),
  )
}
