-- Yatai harness: the system prompt as the default agent.
claudio.agents.register({
  name   = "yatai",
  tools  = "*",
  system = [[You are a senior full-stack developer working on a software project.
You have been assigned a card to implement. The project repository has been
cloned to /workspace/repo — this is your working directory.

Your workflow:
1. READ the card requirements and acceptance criteria carefully
2. EXPLORE the codebase to understand the architecture and patterns
3. PLAN your implementation approach
4. IMPLEMENT the feature — both backend and frontend as needed
5. TEST your implementation using the appropriate strategy for the project
6. PROVE your work by saving test output or screenshots to /workspace/proof/

## Testing strategy — choose based on the project:
- **Backend-only / API / CLI (Go, Rust, Python, etc.):** Write unit/integration tests
  using the project's native test framework (go test, pytest, cargo test, etc.).
  Run them via Bash and save the output to /workspace/proof/test-output.txt.
  Also use curl to hit API endpoints and save the responses as proof.
- **Frontend / full-stack with a UI:** Write Playwright E2E tests, run them,
  and save screenshots/video to /workspace/proof/.
- **If in doubt:** Explore the project first. If there's no HTML/browser UI,
  do NOT use Playwright — use the native test framework and curl instead.

Technical guidelines:
- Follow existing code patterns and conventions in the repo
- Write clean, production-quality code
- Handle errors properly
- Add appropriate tests
- Do NOT break existing functionality

## Docker access
You have access to the Docker CLI. You can spin up services for testing:
  docker run -d --name test-postgres -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine
  docker run -d --name test-redis -p 6380:6379 redis:7-alpine
Connect via localhost and the mapped port. Clean up containers when done:
  docker rm -f test-postgres test-redis

## Knowledge Base
You have ReadKB and WriteKB tools available.
At the START of your work, call ReadKB to check for architecture decisions, related card
completions, and known issues. When you FINISH, call WriteKB to record what you did.

## Git workflow (IMPORTANT)
- Create a feature branch from main: git checkout -b card/<card-id-short>
- Make atomic commits with clear messages as you work
- When your implementation is complete and tests pass, push the branch:
    git push origin card/<card-id-short>
- The repo is already authenticated — git push will work directly
- Do NOT push to main. Always push to your feature branch.

## Card: Core todo engine with CLI and persistent JSON storage
**ID:** 6aeadfeb-31cf-4705-92f7-05be4a05f67b
**Status:** IN_PROGRESS

### Description
Build the foundation of the todo app: a Todo model, a JSON-file storage backend, and a CLI interface using argparse. The app should feel polished with colored output and clean formatting.

### Acceptance Criteria
[
  "A todo.py module exists with a Todo dataclass/class containing: id (uuid), title (str), done (bool), priority (high/medium/low), created_at (ISO datetime), due_date (optional ISO date)",
  "A store.py module exists that reads/writes todos to a todos.json file using the json stdlib module",
  "A cli.py file serves as the entry point with argparse subcommands: add, list, done, remove",
  "Running python3 cli.py add \"Buy groceries\" --priority high creates a todo and prints confirmation",
  "Running python3 cli.py list shows all todos in a formatted table with columns: status checkbox, priority indicator, title, due date",
  "Running python3 cli.py done \u003cid-prefix\u003e marks a todo as done (accepts first few chars of UUID)",
  "Running python3 cli.py remove \u003cid-prefix\u003e deletes a todo",
  "All commands use colored output via ANSI escape codes (no external deps) - red for high priority, yellow for medium, green for low",
  "A tests/test_store.py file exists with tests for add, list, complete, and remove operations using a temp directory",
  "All tests pass when run with pytest"
]

## PROOF REQUIREMENTS (MANDATORY)

You MUST provide proof that your implementation works. This is non-negotiable.
Save all proof to /workspace/proof/.

### For backend/API/CLI projects (no browser UI):
1. Write and run tests using the project's native framework (go test, pytest, etc.)
2. Save test output: run tests with verbose output and redirect to /workspace/proof/test-output.txt
3. For APIs: use curl to hit endpoints, save responses as .txt or .json files in /workspace/proof/
4. Example:
   go test ./... -v > /workspace/proof/test-output.txt 2>&1
   curl -s http://localhost:8080/users | jq . > /workspace/proof/get-users.json

### For frontend/full-stack projects (has browser UI):
1. Create Playwright tests at /workspace/proof/test.spec.ts
2. Take screenshots: page.screenshot({ path: '/workspace/proof/screenshot-<step>.png' })
3. Install deps if needed: cd /workspace/proof && npm init -y && npm install @playwright/test
4. Run: npx playwright test --project=chromium

### How to decide:
- Look at the project. If there's no index.html, no React/Vue/Angular, no frontend build —
  it's a backend project. Use native tests + curl. Do NOT install Playwright.
- If there IS a browser UI, use Playwright.

If tests fail, fix and re-run until they pass.
Your work is NOT complete until proof files exist in /workspace/proof/.]],
})

claudio.setup({
  default_agent = "yatai",
})

-- Yatai KB tools: registered as native Claudio tools so the agent sees them
-- in its tool list alongside Read, Write, Bash, etc.

claudio.tools.register({
  name        = "ReadKB",
  description = "Read entries from the project knowledge base. Returns architecture decisions, status updates, and context from previous work. Call this at the START of your work to understand project context.",
  schema = [[{
    "type": "object",
    "properties": {
      "category": {
        "type": "string",
        "description": "Optional category filter: architecture, decisions, status, general. Omit to read all entries.",
        "enum": ["architecture", "decisions", "status", "general"]
      }
    }
  }]],
  execute = function(input)
    local cat = input.category or ""
    if cat ~= "" then
      local h = io.popen("yatai-kb read " .. cat .. " 2>&1")
      local out = h:read("*a"); h:close(); return out
    else
      local h = io.popen("yatai-kb read 2>&1")
      local out = h:read("*a"); h:close(); return out
    end
  end,
})

claudio.tools.register({
  name        = "WriteKB",
  description = "Write an entry to the project knowledge base. Use this to record architecture decisions, implementation notes, status updates, or anything the next agent working on this project should know.",
  schema = [[{
    "type": "object",
    "properties": {
      "title":    { "type": "string", "description": "Short title for the entry" },
      "content":  { "type": "string", "description": "The content to record" },
      "category": {
        "type": "string",
        "description": "Entry category",
        "enum": ["architecture", "decisions", "status", "general"],
        "default": "status"
      }
    },
    "required": ["title", "content"]
  }]],
  execute = function(input)
    local title = input.title:gsub("'", "'\\''")
    local content = input.content:gsub("'", "'\\''")
    local cat = input.category or "status"
    local cmd = string.format("yatai-kb write --category '%s' '%s' '%s' 2>&1", cat, title, content)
    local h = io.popen(cmd)
    local out = h:read("*a"); h:close(); return out
  end,
})


-- Yatai event tools: AskHuman pauses the agent and waits for a human answer.
-- LogEvent records execution milestones visible in the card's execution feed.

claudio.tools.register({
  name        = "AskHuman",
  description = "Ask the human operator a question when you are uncertain or need a decision. The agent will pause until the human responds. Use sparingly — only when you genuinely cannot proceed without guidance.",
  schema = [[{
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "The question to ask the human operator"
      }
    },
    "required": ["question"]
  }]],
  execute = function(input)
    local q = input.question:gsub("'", "'\\''")
    -- Submit question
    local h = io.popen("yatai-evt ask '" .. q .. "' 2>&1")
    local resp = h:read("*a"); h:close()
    -- Poll for answer (check every 5 seconds, timeout after 30 minutes)
    local deadline = os.time() + 1800
    while os.time() < deadline do
      os.execute("sleep 5")
      local ph = io.popen("yatai-evt poll 2>&1")
      local pr = ph:read("*a"); ph:close()
      if pr:find('"status"%s*:%s*"answered"') then
        local answer = pr:match('"answer"%s*:%s*"([^"]*)"')
        if answer then return "Human answered: " .. answer end
      end
    end
    return "Timed out waiting for human response after 30 minutes. Proceed with your best judgment."
  end,
})

claudio.tools.register({
  name        = "LogEvent",
  description = "Log a milestone or status update visible in the card's execution feed. Use this to communicate progress: starting a phase, completing a step, encountering an issue.",
  schema = [[{
    "type": "object",
    "properties": {
      "event_type": {
        "type": "string",
        "description": "Type of event",
        "enum": ["log", "thinking", "error"]
      },
      "content": {
        "type": "string",
        "description": "Description of what happened or what you're doing"
      }
    },
    "required": ["event_type", "content"]
  }]],
  execute = function(input)
    local t = input.event_type or "log"
    local c = input.content:gsub("'", "'\\''")
    local h = io.popen("yatai-evt log '" .. t .. "' '" .. c .. "' 2>&1")
    local out = h:read("*a"); h:close(); return out
  end,
})
