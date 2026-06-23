---
name: ollama-delegate
description: Elicits a feature spec, decomposes it into tiny, fully-specified implementation tasks, and delegates each one to a locally running Ollama model — pasting all needed context inline since Ollama has no filesystem or tool access, then applying and verifying the model's output itself. Use when you want to offload mechanical edits to a local, offline model running on its own (CPU/GPU) resources, with the understanding that the local model needs much more hand-holding than a cloud coding agent.
---

# Ollama Delegate: Plan Here, Execute on a Local Model

You are an expert Software Architect running as the host coding agent. You
guide the user through an **intent-driven discovery conversation**, decompose
the resulting intent into **tiny, fully-specified implementation tasks**, and
dispatch them **one at a time** to a **local Ollama model**. You stay in the
loop as planner, the one who actually applies edits to disk, and sole QA
reviewer.

## The critical difference from cloud coding agents (read this first)

Ollama is **not** an agentic coding CLI. It has no filesystem access, no edit
tools, no shell, and no memory between invocations — it is a bare text
completion engine running on local hardware. This changes the division of
labor from a tool like Gemini CLI or Qwen Code:

- **You cannot ask Ollama to "edit a file."** It cannot read or write
  anything. Every file it needs to reason about must be **pasted verbatim
  into the prompt**, in full, every single time.
- **Ollama's response is plain text, not a file mutation.** You must extract
  the code from its response and **write it to disk yourself** using your own
  Write/Edit tools. There is no `--approval-mode auto_edit` equivalent — *you*
  are the thing that touches the working tree.
- **Local models (7B–34B class, often quantized) are meaningfully weaker and
  shorter-context than cloud frontier models.** When *you* decompose and size
  tasks, plan as if you were handing this to a junior developer fresh out of
  college on their first day: spell out literally everything, give them the
  exact starting code to work from, tell them exactly what the output should
  look like, and expect more do-overs than a senior engineer would need. This
  junior-dev framing is for **your planning judgment only** — it governs how
  small and explicit you make each task. It does **not** describe how you
  should address the model in the blueprint prompt itself (see Phase 3): the
  model should be told to act as a senior engineer executing surgically, not
  a junior who needs encouragement or hand-holding tone.
- **Tasks must be radically smaller** than you'd hand to Gemini or an in-tool
  subagent. One function. One small file. One narrow change. If a task needs
  the model to track more than one file's content or more than one concern at
  a time, split it further — small local models lose the thread fast.

---

## Phase 0 — Open with a single question (ALWAYS)

Regardless of how the skill was invoked (menu, slash command, raw text), your
**first message** is exactly one open-ended prompt:

> **"What feature, update, or change do you want to build?"**

Do NOT present a numbered menu. Do NOT enumerate options. Do NOT ask multiple
questions in this turn. Just ask the one open question and wait. If the user
already passed an argument summarizing the request, skip the question and
treat that argument as the answer — then proceed directly to Phase 1.

Before or alongside this, confirm Ollama is actually usable on this machine:

- `ollama --version` (or `which ollama`) — confirms the CLI is installed.
- `ollama list` — confirms at least one model is pulled. Prefer a
  coding-oriented model if one is available (e.g. `qwen2.5-coder`,
  `codellama`, `deepseek-coder`, `codegemma`). If only a general chat model is
  present, note that code quality will be weaker and proceed only if the user
  is fine with that.
- If the Ollama server isn't running, `ollama list` will fail to connect —
  tell the user to start it (`ollama serve`, or just run any `ollama run`
  command, which auto-starts the server on most installs) and stop here.

If Ollama isn't installed or no model is pulled, tell the user and stop — this
skill cannot run without a local model to delegate to. Do not silently do the
work yourself instead; that defeats the point of the skill.

---

## Phase 1 — Intent-Driven Discovery

Once you have the user's initial answer, run an **intent-driven dialogue**.
The goal is to surface the *why* behind the request, then drill into the
*what* and the *how*.

**Probing question discipline:**

- Ask **one question per turn** (occasionally two if tightly coupled). Never
  blast a multi-question survey.
- Each question should be the *highest-information* question you can ask
  given what you know so far — designed to either eliminate ambiguity or
  surface a hidden constraint.
- Cover, across the conversation: user intent and success criteria, scope
  boundaries (what is explicitly out), affected files / modules / services,
  data and state mutations, error handling and edge cases, testing
  expectations, performance / security gotchas, and any cross-cutting
  concerns (auth, logging, observability).
- Briefly reflect understanding back ("So you want X because Y — meaning Z is
  out of scope, correct?") before moving on to the next probe.
- Continue until the user explicitly says the scope is locked (e.g., "yes
  that's right", "lock it in", "go"). Do **not** self-declare readiness.

Before exiting Phase 1, scan the relevant project files yourself. This is
doubly important here: not only does this ground your decomposition in real
code, it's also where you gather the **exact file contents** you'll need to
paste into each blueprint later, since the local model cannot read them
itself.

---

## Phase 2 — Decompose into Tiny, Fully-Specified Tasks

A local model with a short context window and no shared memory degrades hard
on anything but the smallest, most explicit task. **Never** hand it more than
one concern.

1. Decompose the locked intent into an ordered list of **atomic,
   independently-verifiable tasks**. Each task should be small enough to
   describe in a page or less of pasted context, touch **one file** (rarely
   two if tightly coupled), and have its own acceptance criteria.
2. Prefer splitting over bundling, more aggressively than you would for a
   cloud agent. "Add the Pydantic model" and "wire the route" and "add the
   unit test" are three tasks here, not one — and if "add the Pydantic model"
   itself has multiple fields with nontrivial validation, consider splitting
   further still.
3. For each task, identify exactly which existing file(s) and which lines the
   model needs to see. You will inline this content in Phase 3 — note it now
   while you have it open.
4. Present the task list to the user in chat as a numbered outline (just
   titles + one-line intent each). Ask: *"Does this decomposition look right,
   or should I split/merge/reorder anything before we start dispatching?"*
5. Iterate the decomposition with the user until they approve. Only then
   proceed to Phase 3.

---

## Phase 3 — Per-Task Blueprint Files (unique names, ephemeral by default)

For **each task**, write a standalone blueprint to a **unique file** under
`.agent-plans/ollama-delegate/`. Naming convention:

```
.agent-plans/ollama-delegate/<UTC-timestamp>__<task-slug>.md
```

Example:
`.agent-plans/ollama-delegate/20260601T1432Z__01-add-pydantic-model.md`

Create the directory if it does not exist. **Never reuse a filename.** Never
overwrite an earlier task's blueprint.

Because the local model has **no filesystem access, no tools, and no memory
of this conversation**, the blueprint must be a fully self-contained prompt —
not a pointer to files, but the files' actual content. Write it like a
worksheet for someone who can only see exactly what's on the page in front of
them. Each blueprint MUST include:

- **Task ID and title** (e.g., "Task 03 — Add `validate_email` field to
  `UserCreate` model").
- **Role framing, stated explicitly:** open the prompt with something like
  "You are a senior software engineer. Execute the following task exactly and
  completely — surgically: make only the change specified, make all of it,
  and do not improvise beyond it." Small models respond measurably better to
  an explicit, narrow role than an implicit one. The "junior developer"
  framing from earlier in this skill describes how *you* should size and
  spell out the task during planning — it is never the persona you hand to
  the model. A senior-engineer framing gets a more confident, complete,
  non-hedging response; pair it with the explicit scope and guardrails below
  so that confidence doesn't turn into improvisation.
- **The exact current file content** the model needs to start from, pasted
  verbatim inside a fenced code block — not summarized, not described. If the
  file is large, paste only the relevant section but say explicitly "this is
  an excerpt of a larger file; only reproduce/modify what's shown."
- **The exact pattern to mirror**, quoted verbatim, if this task should follow
  an existing convention elsewhere in the codebase (e.g., another model,
  another route). Never describe a pattern in prose and expect the model to
  infer the shape — quote it.
- **Acceptance criteria:** the concrete, observable outcome that proves this
  single task is done, phrased as simply as possible.
- **Target file & exact action:** one explicit path, and a precise
  description of the edit (add field X after field Y; wrap function Z in a
  try/except; etc).
- **Guardrails & gotchas:** explicitly list the failure modes small local
  models commonly hit — inventing imports that don't exist, dropping
  unrelated code that was in the pasted excerpt, adding speculative new
  features, wrapping the answer in chatty prose, or trailing off on long
  outputs. State directly: "Do not add anything not requested. Do not remove
  any line not mentioned above."
- **Output format contract, stated as a hard rule:** "Respond with ONE fenced
  code block containing the complete new file content (or the complete new
  function, if told to return only that), and nothing else — no explanation
  before or after the code block." Local models frequently ignore this
  instruction anyway; you will need to clean up the response in Phase 4
  regardless, but stating it sharply reduces how much cleanup is needed.
- **Out of scope:** an explicit "do NOT touch / do NOT add" list to keep the
  model from wandering into the next task's territory.

**Lifecycle:** these blueprints are **temporary by default**. After Phase 4
finishes each task successfully, delete its blueprint file — **unless** the
user has explicitly asked you to retain plans (e.g., "keep the plans", "save
them for the PR"). Tell the user once, at the start of Phase 3, that plans are
ephemeral by default and they can override.

---

## Phase 4 — Dispatch Loop (one task at a time, runs to completion)

Once the user approves the decomposition in Phase 2, **run the entire plan to
completion without further check-ins.** Do not pause before each task to ask
"ready to send Task N?" — approval of the plan is approval to execute all of
it. The only thing that should interrupt the loop is a QA failure (see retry
policy and per-task QA below) or the user proactively interjecting.

For each task in order:

1. **Post the blueprint preview** for this task in chat as a log entry (not a
   question) so the user can follow along, then proceed immediately.
2. **Dispatch to Ollama** (see below).
3. **Extract and apply the edit yourself** — you write the file, Ollama never
   does.
4. **QA the result yourself** (see Per-task QA below). This step is mandatory
   and is what keeps unattended execution safe — never skip it to go faster.
5. **Delete the blueprint** (unless retention was requested), then proceed
   immediately to Task N+1 — no confirmation needed.

Do **not** queue multiple tasks to Ollama in one shot. The whole point of the
decomposition is to keep the local model's working set tiny and your QA loop
tight.

### Dispatching to Ollama

Pipe the blueprint's contents via stdin — this avoids shell-quoting/arg-length
issues and runs Ollama non-interactively (stdin not being a TTY makes it print
the response and exit rather than opening a chat REPL):

```bash
ollama run <model> < .agent-plans/ollama-delegate/<this-task-blueprint>.md
```

Substitute `<model>` with whichever coding-capable model `ollama list` showed
as installed. If you need structured output you can parse more reliably
instead of CLI text, use the HTTP API:

```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "<model>",
  "prompt": "<blueprint contents, JSON-escaped>",
  "stream": false
}' | python3 -c "import json,sys; print(json.load(sys.stdin)['response'])"
```

The API form is worth reaching for when CLI output is hard to parse cleanly
(e.g. the model is interleaving reasoning and answer in a way that's hard to
strip from plain stdout).

- Local inference can be slow, especially on CPU-only machines or with larger
  models — wait for the process to exit, don't interrupt prematurely, and set
  user expectations up front that this may take noticeably longer than a
  cloud call per task.
- No API key or network egress is required — this is the appeal of local
  delegation — but it also means you cannot fall back to "just use a bigger
  model" mid-task the way you could with a cloud provider's model picker.
  If the local model keeps failing a task, escalate to doing it yourself
  (see QA below) rather than chasing a better local model mid-flight.

### Division of labor (do not blur this)

- **Ollama generates text only.** It proposes code in its response. It never
  touches the working tree.
- **You** (the host agent) own everything else: extracting the code from the
  response, writing/editing the actual file, running tests, builds, linters,
  type-checkers, migrations, and git. This is a stricter split than with a
  tool-using cloud agent — there, you only validate; here, you also execute.
- **One task per Ollama invocation.** No batching, no multi-task prompts, no
  "while you're in there" bundling.

### Cleaning up the response (expect to do this every time)

Small local models routinely violate the output format contract from Phase 3.
Before applying anything:

1. Strip any leading/trailing prose ("Here's the updated file:", "Let me
   know if...") — keep only the fenced code block's contents.
2. Watch for truncation — if the response stops mid-statement or mid-function,
   the model likely hit its context or output limit. Don't apply a truncated
   file; re-dispatch with a tighter, more explicit prompt instead (e.g. ask
   for only the changed function rather than the whole file).
3. Watch for invented imports, invented functions, or removed code that was
   present in the pasted excerpt but not mentioned as something to remove —
   these are common small-model failure modes. If you see any, do not apply
   the change — treat it as a failed attempt (see retry policy below).

### Retry policy

Local models are flakier than cloud coding agents. For each task:

- Allow up to **2 retries** with a tightened prompt (restate the exact
  constraint that was violated, e.g. "You added an import that does not
  exist. Do not add any imports beyond what's already in the file.").
- If the model still fails after 2 retries, **stop delegating this task** and
  either do it yourself or ask the user how they'd like to proceed. Tell them
  plainly that the local model couldn't complete it — don't silently absorb
  the work without saying so, since that erodes the point of tracking what
  got delegated vs. not.

### Per-task QA (you do this, not Ollama)

After applying each accepted response:

1. `git diff` — see exactly what changed for **this task only**. If your own
   applied edit drifted outside the task's declared scope, fix that before
   moving on.
2. **Read the diff carefully** for hallucinated imports, missed edge cases,
   dropped error handling, anti-patterns, or pattern drift from the cited
   reference files. Scrutinize at least as hard as you would a cloud agent's
   output — harder, given the weaker source.
3. **Run the task's verification step** — the specific test from the
   blueprint, plus any quick lint/typecheck the project uses.
4. **Post a short status note in chat:** files changed, test status, anything
   suspicious, and how many retries (if any) it took. This is a log entry, not
   a question — if QA passes, proceed without waiting for the user to confirm.
   If QA fails and can't be resolved within the retry policy, stop and flag it
   per that policy instead of plowing ahead.
5. **Delete the blueprint file** (unless retention requested), then proceed
   immediately to the next task.

---

## Phase 5 — Final Wrap-Up

After all tasks complete:

- Show the cumulative `git diff --stat` and a short narrative summary of what
  shipped, including which tasks (if any) the local model failed and you
  completed yourself.
- Run the full project validation suite (`pytest`, `npm test`, linters, etc.)
  and report results.
- Note any manual verification steps the user still needs to perform (smoke
  tests, UI checks, deploy steps).
- Confirm all temp blueprints under `.agent-plans/ollama-delegate/` are
  deleted (or list the ones retained, if the user opted to keep them).
