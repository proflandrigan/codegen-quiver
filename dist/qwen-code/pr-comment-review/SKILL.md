---
name: pr-comment-review
description: Fetches a pull request's review and discussion comments and resolves them — either by walking the user through each thread one fix at a time (interactive), or by triaging all comments, getting one plan approval, and dispatching subagents to implement the batch while the orchestrator QAs (orchestrated). Use when you have PR feedback to address.
---

# PR Comment Review: Fetch, Triage, Resolve

You help a developer work through the review feedback on a pull request. You
fetch the PR's inline review comments and general discussion comments, group
them into threads, and then resolve them in one of two modes the user picks up
front:

- **Interactive** — you and the user walk every thread together, and you gate
  each edit before applying it.
- **Orchestrated** — you triage all comments into a single fix plan, get one
  approval, then dispatch the implementation work to subagents while you stay in
  the loop as the QA gatekeeper.

This is a direct code-intervention workflow. While it runs you implement fixes
yourself (or via subagents) rather than handing off to other specialists. Keep
commentary concise throughout.

---

## Phase 0 — Pick the mode (ALWAYS first)

Your **first message** asks exactly one question:

> **"Should I walk you through the PR comments one at a time (interactive), or
> triage everything and orchestrate the fixes myself with your approval on the
> plan (orchestrated)?"**

Wait for the answer. If the invocation already states a mode (e.g. the user
said "orchestrate the PR fixes"), skip the question and proceed. Steps 0–2 are
identical for both modes; the modes diverge at Step 3.

---

## Step 0 — Repository verification

Confirm you are in a git repo:

```bash
git rev-parse --show-toplevel 2>&1
```

If it succeeds, note the root and continue. If it fails, discover candidate
repos:

```bash
find . -maxdepth 2 -name ".git" -type d | sort
```

For each repo found, show its current branch and let the user choose. All
subsequent commands run from the chosen directory.

---

## Step 1 — PR detection

This workflow requires the GitHub CLI (`gh`). Retrieve PR metadata for the
current branch:

```bash
gh pr view --json number,title,url,headRefName,baseRefName,reviewDecision,state
```

Display the PR number, title, branch info, and review status. If no PR exists
for the current branch, ask the user to specify the PR number (then use
`gh pr view <number> --json ...`). If `gh` is missing or unauthenticated,
report it plainly and stop — do not guess at comment content.

---

## Step 2 — Comment fetching

Resolve owner and repo:

```bash
gh repo view --json owner,name --jq '.owner.login + "/" + .name'
```

Fetch inline review comments (the ones attached to specific file lines):

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate
```

Fetch general PR discussion comments (not attached to code):

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments
```

Parse and group the inline comments into **threads** (a root comment plus its
replies, keyed by file + position / `in_reply_to_id`). Summarize what you found:
thread count, files touched, and how many general comments exist. Wait for the
user to confirm before proceeding.

**Cap:** if there are more than 100 threads, say so and offer to filter (by
file, by reviewer, or unresolved-only) before continuing.

Handle `gh` failures gracefully at every call — show the error and ask how to
proceed rather than fabricating results.

---

## Step 3 — INTERACTIVE mode (walk every thread)

Process threads in **file order**: alphabetical by filename, then ascending by
line number. For each thread:

1. **Present the thread.** Header with file path and line number, then the
   reviewer comment(s) in chronological order.
2. **Read the real code.** Open the file and show the cited line(s) with about
   ±15 lines of surrounding context. Always read the actual current code before
   proposing anything. If the line numbers no longer line up with the content
   the comment refers to, **warn that the line numbers may be stale** and locate
   the intended code by content.
3. **Propose a fix.** Categorize the thread as an **actionable change**, a
   **discussion point**, or **ambiguous**. For actionable changes, describe the
   specific edit you'd make.
4. **Gate and await approval.** Offer the choices:
   - `y` — apply the proposed fix
   - `n` — skip this thread
   - `edit` — apply a custom variant the user describes
   - `done` — stop the walkthrough

   Apply an edit **only after explicit approval**. After applying, read back the
   modified lines to confirm. **Gate every single edit — no exceptions.**

Then continue to Step 4.

---

## Step 3' — ORCHESTRATED mode (triage, approve once, dispatch)

The orchestrator (you) plans and verifies; cheaper subagents do the mechanical
editing. This mirrors the discipline of the [[tiered-delegate]] skill applied to
PR feedback.

### 3'a — Triage into a fix plan

Read the real code behind each thread first (don't plan from the comment text
alone). Then sort every thread into one of:

- **actionable-clear** — unambiguous fix; you know exactly what to change.
- **needs-judgment** — actionable but with a real decision; state the options
  and the call you intend to make.
- **discussion-only** — a question or remark with no code change implied.
- **skip-with-reason** — won't address; give the reason (out of scope, stale,
  disagree, etc.).

### 3'b — Present the plan and get ONE approval

Show the full categorized plan as a numbered list: each item names the
file/lines, the reviewer's point, and your intended action. This single
approval is the gate for the whole batch. Let the user amend the plan
(reclassify, drop, or adjust any item) before you start. Only proceed once they
approve.

### 3'c — Dispatch each actionable item

For each actionable item, in order:

1. **Write a tight per-fix blueprint** — the minimum the executor needs:
   - the reviewer's point and the intended outcome,
   - exact target file and line range, with the surrounding pattern to mirror
     (quote it),
   - acceptance criteria (what proves this one fix is done),
   - guardrails / gotchas (hallucinated imports, dropped error handling, pattern
     drift),
   - an explicit out-of-scope list so the executor doesn't reach into other
     items.
2. **Dispatch to a cheaper subagent tier** to do the edit only:
   - **Claude Code (reference):** use the **Task tool** with an explicit `model`
     step-down (Opus → Sonnet, Sonnet → Haiku) and a general-purpose subagent;
     pass the blueprint as the prompt. Drop a further tier for purely mechanical
     edits; keep it at your own tier (or do it yourself) for subtle or
     security-sensitive ones.
   - **Other tools (generic fallback):** use your tool's subagent / task
     mechanism on a lighter tier than your own. If there is no model-tiered
     subagent, apply the blueprint yourself but treat it as one isolated,
     scoped unit of work.
3. **The subagent edits files only.** You own all validation.

### 3'd — QA every dispatched fix (you, not the subagent)

After each dispatch:

- `git diff` the changed files; confirm the edit stayed inside the item's
  declared scope (revert and re-issue if it didn't).
- Read the diff for hallucinated imports, missed edge cases, dropped error
  handling, or drift from the cited pattern.
- Run the relevant test / lint / type-check yourself — **never delegate
  validation** to the subagent.
- Report per item: files changed, check status, anything suspicious. On failure,
  re-dispatch a corrective mini-blueprint or fix it yourself if that's faster.

Then continue to Step 4.

---

## Step 4 — General comments

If non-inline (general discussion) comments exist, offer to walk through them.
These are **discussion-only** unless the user explicitly asks you to turn one
into a code change.

---

## Step 5 — Wrap-up

Show a completion summary:

- count of fixes applied,
- count skipped (with reasons in orchestrated mode),
- list of files modified,
- `git diff --stat` for the whole session.

Then **offer** to commit the addressed changes (and optionally push). This is
gated — never auto-commit. If the user accepts, write a concise commit message
referencing the PR feedback addressed.

---

## Behavioral rules

- Pick the mode in Phase 0 before anything else.
- Always read the actual current code before proposing a fix.
- **Interactive mode:** gate every single edit — no exceptions.
- **Orchestrated mode:** the one plan approval (3'b) is the batch gate; the
  final commit (Step 5) is separately gated. Subagents edit; you always QA.
- Warn when comment line numbers look stale.
- Cap at 100 threads; offer filtering for larger PRs.
- Require `gh`; handle its failures gracefully — never fabricate comments.
- Keep commentary concise.
