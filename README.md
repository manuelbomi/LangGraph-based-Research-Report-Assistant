# LangGraph-based Research & Report Assistant

A production-shaped, end-to-end example of a **cyclic, human-in-the-loop agentic
workflow** built with [LangGraph](https://github.com/langchain-ai/langgraph): it
plans sub-questions for a research question, researches them with a web search
tool and an embedded vector-store knowledge base, drafts a cited markdown
report, critiques and revises itself in a bounded loop, pauses for a **human**
decision, and finalizes the report -- durably, resumably, and observably.

This repo exists to demonstrate, concretely and honestly, what LangGraph is
*for* -- not just to show LangGraph syntax. See
["Why LangGraph (and when NOT to use it)"](#why-langgraph-and-when-not-to-use-it) below.

## What it does

**Backend:** Python 3.11 / FastAPI / LangGraph `StateGraph`, checkpointed to
Postgres (`langgraph-checkpoint-postgres`), streaming node-by-node progress to
the frontend over Server-Sent Events.

**Frontend:** React 18 / TypeScript / Vite / Tailwind, with a live
[React Flow](https://reactflow.dev/) diagram of the running graph, a human
review panel, and a run-history / example-analyses view.

### The graph

```mermaid
flowchart TD
    START([START]) --> plan[1. plan\nLLM: 2-4 sub-questions]
    plan --> research[2. research\nweb search + Milvus Lite KB tool]
    research --> draft[3. draft\nLLM: cited markdown report]
    draft --> critique[4. critique\nLLM: approve or revise]
    critique -- "revise\n(bounded, max 2 loops)" --> research
    critique -- approve --> human_review[5. human_review\ninterrupt(): pauses for a human]
    human_review -- "revise\n(bounded, max 2 loops)" --> research
    human_review -- "approve / reject" --> finalize[6. finalize\nassemble final report + sources]
    finalize --> END([END])

    classDef loop stroke:#f59e0b,stroke-width:2px;
    class critique,human_review loop;
```

Two cycles matter here:

1. **`critique -> research`** -- an *automated* revision loop. If the critique
   node decides the draft doesn't fully answer the question, the graph loops
   back to `research` with the critique feedback folded in, bounded to
   `MAX_REVISION_LOOPS` (default 2) before it force-approves.
2. **`human_review -> research`** -- a *human-directed* revision loop. A
   reviewer can request changes in free text; the graph loops back to
   `research` with that feedback, bounded to `MAX_HUMAN_REVISION_LOOPS`
   (default 2) before it force-finalizes.

Both loops are the entire point of this repo: a linear pipeline (a LangChain
LCEL chain, a LlamaIndex query engine, a Haystack `Pipeline`) runs forward
once and cannot natively express "go back and redo step 2 based on what step 4
found," but a `StateGraph` conditional edge can.

### The knowledge-base tool (and a deliberate simplification)

The `research` node picks its tool(s) per sub-question with a real, inspectable
heuristic (`should_consult_kb` in `backend/app/graph/nodes.py`): if the
sub-question's keywords plausibly fall inside the fixed demo knowledge-base
topic (**the history and fundamentals of renewable energy**, 12 short
hand-written reference documents), it queries the knowledge base; it always
also falls back to web search when the KB heuristic doesn't fire or comes back
empty. This means a renewable-energy question exercises both tools and merges
their findings; most other questions exercise the web-search path only -- try
both from the New Run page to see the difference in the trace panel.

The knowledge base is an **embedded Milvus Lite** vector store
(`pymilvus[milvus_lite]`) -- a local file, no server, no Docker container
required for the vector DB itself. This is a deliberate simplification for a
tutorial: Milvus Lite ships Linux/macOS binaries only, so on native Windows
Python you'll need to run the backend via Docker or WSL (see
[Setup & run](#setup--run) below); the backend's own Docker image is Linux, so
`docker compose up` works everywhere. For a larger-scale or multi-process
production deployment, swap `pymilvus[milvus_lite]`'s embedded client for a
real **Milvus server** (`pymilvus.MilvusClient(uri="http://milvus:19530")`)
running as its own `docker-compose` service -- the KB tool's interface
(`app/tools/knowledge_base.py`) doesn't change, only the connection string
does.

### The UI

- **New Research Run** -- ask a question; watch the graph diagram highlight
  the currently-executing node live as SSE events arrive, with a side panel
  streaming in each node's output (sub-questions, findings with source
  citations, the draft, critique feedback).
- **Human Review** -- when the run reaches `human_review`, the draft report
  and critique feedback are shown with **Approve**, **Request Changes** (free
  text), and **Reject** actions that call `POST /runs/{id}/resume`.
- **Run History / Example Analyses** -- every run (including two seeded,
  realistic example runs -- one that exercises the KB+web merge on a
  renewable-energy question, one web-search-only on a software-architecture
  question) with status, and a detail view rendering the final markdown
  report plus the full step-by-step trace of what each node produced.

## Setup & run

### Required environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | -- | Required (this repo is tested against OpenAI) |
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4o-mini` | Cheap, fast; used for plan/research/draft/critique |
| `ANTHROPIC_API_KEY` | -- | Only needed if `LLM_PROVIDER=anthropic` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Used to embed the KB corpus + queries |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/research_assistant` | Prompts, runs, and LangGraph checkpoints |
| `MILVUS_LITE_PATH` | `./data/milvus_kb.db` | Embedded vector-store file |

See `.env.example` for the full list (revision-loop caps, CORS, etc).

### Option A: docker-compose (recommended, works on Windows/macOS/Linux)

```bash
cp .env.example .env   # then edit OPENAI_API_KEY
docker compose up --build
```

This starts `postgres` (healthchecked), `backend` (runs Alembic migrations,
seeds the v1 prompts, seeds the Milvus Lite KB, seeds two example runs, then
serves the API on `:8000` -- see `backend/docker-entrypoint.sh`), and
`frontend` (built + served via nginx on `:8080`). Open
**http://localhost:8080**.

Port collisions are common on a dev box; override any of them without
touching the compose file:

```bash
BACKEND_PORT=8091 POSTGRES_PORT=5544 FRONTEND_PORT=8092 docker compose up --build
```

### Option B: local dev (backend + frontend separately)

Backend (Python 3.11+; **Linux or macOS for the KB tool** -- see the Milvus
Lite note above; on Windows, run the backend in Docker or WSL instead):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start Postgres however you like, e.g.:
docker run -d --name rra-postgres -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=research_assistant postgres:16-alpine

export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/research_assistant
export OPENAI_API_KEY=sk-...

alembic upgrade head
python -m app.prompts.seed_prompts
python -m app.tools.seed_kb          # Linux/macOS only (or run inside Docker)
python -m scripts.seed_examples
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm run dev   # http://localhost:5173
```

### Running the tests

```bash
# Backend: fully mocked (no API key, no real DB needed) -- 33 tests
cd backend && pytest

# Backend: REAL end-to-end smoke test (needs a real OPENAI_API_KEY + reachable
# Postgres) -- proves the interrupt/resume cycle survives a checkpointer
# restart, using real LLM calls
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/research_assistant \
  pytest -m live tests/live/test_live_smoke.py -v -s

# Frontend
cd frontend
npm run typecheck && npm run build && npm run test
```

## Why LangGraph (and when NOT to use it)

This is the honest engineering case for the tool choice, not marketing copy.

**Native cycles / conditional loops.** The critique-to-research and
human-review-to-research loops in this repo are ordinary conditional edges in
a `StateGraph` -- `add_conditional_edges("critique", route_after_critique,
{...})`. A LangChain LCEL chain, a LlamaIndex query engine, and a Haystack
`Pipeline` are all fundamentally **DAGs that execute forward once**; looping
back to an earlier step based on a later step's output isn't something they
express natively -- you'd hand-roll a `while` loop around the whole pipeline
outside the framework, at which point you've lost the framework's visibility
into where you are in that loop. LangGraph's graph *is* the state machine, so
the loop, its bound, and its exit condition are all visible in one place
(`app/graph/graph.py`).

**Durable execution via checkpointing.** `AsyncPostgresSaver` persists the
*entire* graph state after every node, keyed by `thread_id`. That's what makes
`human_review` able to pause for seconds or for weeks: the process can exit
completely, and a brand new process opening a fresh `AsyncPostgresSaver`
against the same Postgres database can resume the exact same run. This repo
proves that concretely in `backend/tests/live/test_live_smoke.py`: it runs
until the interrupt, closes the checkpointer entirely, opens a **new**
checkpointer + a **newly-compiled graph**, confirms the paused state is really
there (not held in memory), and resumes it to completion.

**First-class human-in-the-loop.** `interrupt()` is not a callback bolted onto
a response object -- it raises inside the node, LangGraph persists state up to
that point, and `graph.astream(Command(resume=...), config)` continues
*exactly* from there, re-running only that node's body. Building the
equivalent by hand on top of a plain chain means inventing your own pause/
resume protocol and your own state persistence.

**Explicit, inspectable control flow.** You can look at `graph.py` and see
every node and exactly which one runs next, versus LangChain's
`AgentExecutor` implicit ReAct loop (the model decides what happens next, and
you observe it after the fact via callbacks) or a single retrieval pipeline
with no branching at all. For a workflow with more than one path through it,
that explicitness is worth a lot in code review and in debugging a production
incident at 2am.

**When NOT to use LangGraph:**

- **Simple, single-shot RAG Q&A with no iteration.** If there's no loop, no
  pause, and no multi-step control flow, LlamaIndex's query engines are more
  purpose-built and require far less boilerplate for pure indexing/retrieval.
  You'd be paying for state-machine machinery you never touch.
- **Fast linear prototyping with the broadest integration catalog.** If you
  just need to chain "retrieve -> prompt -> parse" once, a LangChain LCEL
  chain gets there in fewer lines and still has the widest catalog of
  prebuilt loaders/integrations to lean on.
- **Production search/NLP pipelines (retrieval + ranking + extraction) with
  strong evaluation tooling**, as opposed to agentic reasoning. Haystack's
  `Pipeline`/component ecosystem and evaluation story are more purpose-built
  for that than bending a graph of LLM nodes to do it.
- **A team unfamiliar with graph/state-machine modeling, on a tight
  deadline.** Simpler frameworks ship a simple case faster; a `StateGraph`
  has a real learning curve (state reducers, checkpointers, interrupts) that
  isn't worth paying for a workflow that will never branch or loop.
- **No need for persistence, resumability, or human-in-the-loop at all.** If
  your workflow runs start-to-finish in one request/response with nothing to
  pause for, the checkpointing and graph-compilation machinery here is pure
  overhead versus a plain function call.

The rule of thumb this repo tries to embody: reach for LangGraph when the
workflow has **cycles, needs to survive being paused, or needs a human in the
loop** -- and reach for something lighter when it doesn't.

## Repo structure

```
backend/
  app/
    graph/          # StateGraph state schema (state.py), nodes (nodes.py), wiring (graph.py)
    tools/          # web_search.py (ddgs), knowledge_base.py + kb_documents.py (Milvus Lite)
    prompts/        # registry.py (Postgres-backed prompt versions), seed_prompts.py
    db/             # SQLAlchemy models, Alembic migrations, session, checkpointer wiring
    api/             # FastAPI routers (runs.py: create/stream/resume/list/detail), schemas.py
    llm.py           # provider-agnostic chat model + embeddings factory
    main.py          # FastAPI app + lifespan (opens the one AsyncPostgresSaver)
  scripts/
    seed_examples.py # seeds 2 realistic example runs for the History page
  tests/             # pytest, fully mocked (LLM, tools, DB)
    live/            # tests/live/test_live_smoke.py -- REAL OpenAI + Postgres, excluded by default
  Dockerfile, docker-entrypoint.sh, requirements.txt, pyproject.toml
frontend/
  src/
    api/             # types.ts (hand-written mirror of backend schemas), client.ts
    hooks/           # useRunStream.ts (SSE -> React state)
    components/      # GraphView (React Flow), NodePanel, HumanReview, RunHistory, MarkdownReport
    pages/           # NewRunPage, HistoryPage, RunDetailPage
    test/            # Vitest + React Testing Library component tests
  Dockerfile, nginx.conf
docker-compose.yml
.github/workflows/ci.yml
```

## The prompt registry

Prompts aren't hardcoded strings in the node functions -- they're rows in a
Postgres `prompts` table (`name`, `version`, `template`, `is_active`,
`created_at`), loaded through `app/prompts/registry.py::get_prompt(name)`
(with a small process-local cache) and formatted with `render_prompt(name,
**kwargs)`. `backend/app/prompts/seed_prompts.py` seeds real v1 templates for
`plan`, `research_summarize`, `draft`, and `critique`.

**To add a new prompt version:**

```python
from app.prompts.registry import add_prompt_version

add_prompt_version(
    "critique",
    "...your improved template, with the same {question}/{draft}/... placeholders...",
    activate=True,  # flips is_active on this version, off on the previous one
)
```

Run that from a one-off script, a Python shell, or wire it behind an
admin-only API route -- `add_prompt_version` handles version numbering and
activation atomically. Because `get_prompt` caches per-process, restart the
backend (or call `registry.invalidate_cache()`) to pick up the change
immediately in a running process.

## License

MIT -- see [LICENSE](./LICENSE).

**Author:** Emmanuel Oyekanlu
