# CI/CD Agent 🤖

An autonomous agent that watches your GitHub Actions pipelines, diagnoses failures, traces the responsible commit, proposes a targeted fix, and posts a structured report — all without human intervention.

## Demo

> Agent detects a syntax error, traces the blame to commit `823e971`, proposes a fix with 95% confidence, and posts the report to GitHub.

![CI/CD Agent Report](docs/demo.png)

**Live example:** [View a real agent report on GitHub →](https://github.com/kv-1505/cicd-agent/commit/f43a87189f68b564af86665ea5b9dcb474e4aaf9)

---

## How It Works

When a GitHub Actions workflow fails, the agent runs a 6-step pipeline:

```
GitHub Actions fails
        │
        ▼
┌───────────────┐
│  Log Analyser │  Parses CI logs → extracts error, file, line number
└──────┬────────┘
       │
       ▼
┌───────────────┐
│ Blame Tracer  │  Finds the commit + author responsible via GitHub API
└──────┬────────┘
       │
       ▼
┌────────────────┐
│ Code Retriever │  RAG lookup — fetches relevant code context from FAISS index
└──────┬─────────┘
       │
       ▼
┌───────────────┐
│ Fix Proposer  │  Claude proposes a targeted fix (snippet-level, not full file)
└──────┬────────┘
       │
       ▼
┌───────────────┐     fails (max 2 retries)
│   Validator   │ ──────────────────────────► Fix Proposer
└──────┬────────┘
       │ passes
       ▼
┌───────────────┐
│  PR Reporter  │  Posts structured Markdown report to GitHub PR or commit
└───────────────┘
```

### Report Posted to GitHub

```markdown
## 🤖 CI/CD Agent Report

### ❌ Build Failure Analysis
**Error:** NameError: name 'this' is not defined
**File:** `calculator.py` (line 6)
**Root Cause:** syntax

### 🔍 Blame Trace
**Commit:** 823e971 by kv-1505
**Message:** test: reindex v2

### 💡 Proposed Fix
**Confidence:** 🟢 0.95

 ```diff
- this is broken
+ 
 ```

### ✅ Validation
✅ Fix passed validation
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub                               │
│  push event ──────────────────────────────────────────┐ │
│  workflow_run failure ──────────────────────────────┐  │ │
└────────────────────────────────────────────────────────┘ │
                                                    │   │
                        ┌───────────────────────────┘   │
                        │  FastAPI Webhook Server        │
                        │  POST /webhook                 │
                        └──────────┬────────────────┘   │
                                   │                     │
              ┌────────────────────┴──────────────┐      │
              │                                   │      │
              ▼                                   ▼      │
    ┌──────────────────┐               ┌─────────────────┴──┐
    │  Re-index Repo   │               │   LangGraph Agent   │
    │  (on every push) │               │   6-node pipeline   │
    └──────────────────┘               └────────────────────┘
              │                                   │
              ▼                                   ▼
    ┌──────────────────┐               ┌──────────────────┐
    │   FAISS Index    │◄──────────────│  Code Retriever  │
    │ (sentence-trans) │               │  (RAG lookup)    │
    └──────────────────┘               └──────────────────┘
                                                │
                                                ▼
                                    ┌──────────────────────┐
                                    │   Claude Sonnet 4    │
                                    │  Log Analyser        │
                                    │  Fix Proposer        │
                                    └──────────────────────┘
```

**Key design decisions:**
- **Push-based re-indexing** — index is rebuilt on every push, so the agent always queries fresh code
- **Thread-safe locking** — if re-indexing and a failure arrive simultaneously, the agent waits for indexing to finish before querying
- **Snippet-level diffs** — fix proposals show only the changed line, not the whole file
- **Retry loop** — validator rejects low-confidence or syntactically invalid fixes and loops back to Fix Proposer (max 2 retries)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Webhook server | FastAPI + Uvicorn |
| Agent orchestration | LangGraph |
| LLM | Claude Sonnet 4 (Anthropic) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS (IndexFlatL2) |
| Code chunking | Python AST parser |
| GitHub API | PyGithub |
| Signature verification | HMAC-SHA256 |

---

## Project Structure

```
cicd-agent/
├── main.py                  # FastAPI server, webhook handler, reindex lock
├── config.py                # Environment variable loader
├── agent/
│   ├── graph.py             # LangGraph pipeline definition + retry logic
│   ├── state.py             # AgentState TypedDict
│   └── nodes/
│       ├── log_analyser.py  # Parse CI logs → structured error JSON
│       ├── blame_tracer.py  # Find responsible commit via GitHub API
│       ├── code_retriever.py# RAG query with reindex-lock awareness
│       ├── fix_proposer.py  # Claude proposes targeted fix
│       ├── validator.py     # Syntax check + confidence + placeholder check
│       └── pr_reporter.py   # Post Markdown report to GitHub
├── rag/
│   ├── indexer.py           # Clone repo, AST-chunk Python files, build FAISS index
│   └── retriever.py         # Query index, return formatted code context
└── gh_client/
    ├── client.py            # Fetch + decode workflow logs (ZIP format)
    └── webhook.py           # Verify GitHub webhook HMAC signature
```

---

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/kv-1505/cicd-agent.git
cd cicd-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=your_secret_here
```

### 3. Start the server

```bash
uvicorn main:app --port 8000
```

### 4. Expose locally with ngrok (for testing)

```bash
ngrok http 8000
```

### 5. Add GitHub webhook

In your repo → **Settings → Webhooks → Add webhook**:
- **Payload URL:** `https://<your-ngrok-url>/webhook`
- **Content type:** `application/json`
- **Secret:** same as `GITHUB_WEBHOOK_SECRET`
- **Events:** `push` + `workflow_run`

Now push a broken commit and watch the agent post a report.

---

## Roadmap

- [x] Weekend 1 — FastAPI webhook + Log Analyser + Blame Tracer
- [x] Weekend 2 — RAG indexer + Fix Proposer + Validator + PR Reporter + push-based reindex
- [ ] Weekend 3 — MCP server + Docker + deploy to Railway
