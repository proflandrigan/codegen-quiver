# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A build pipeline for **installable coding-agent skills**. Each skill is authored
once as a canonical `SKILL.md` (YAML-ish frontmatter + markdown body) and
compiled into provider-specific artifacts for Claude Code, Qwen Code, Codex, and
Gemini CLI. There is no application runtime here — the "product" is the generated
`dist/` tree that users copy into their agent's skills directory.

## Commands

```bash
python build/build.py          # regenerate dist/ from skills/ (stdlib only, no venv needed)
python build/build.py --check  # verify dist/ matches skills/; non-zero exit if stale (CI/pre-push gate)
```

There is no test suite, linter, or dependency manifest — the builder is pure
Python stdlib and runs with any `python3`.

## Architecture

The core invariant: **`skills/` is the single source of truth; `dist/` is
generated and committed.** `build/build.py` is the only thing that writes
`dist/`, and it wipes `dist/` entirely on each run (`build_all` → `rmtree`).

Compilation differs by provider target:

- **claude-code, qwen-code, codex** (`SKILL_MD_PROVIDERS` in `build.py`) consume
  the `SKILL.md` standard directly, so each skill directory is copied *verbatim*
  into `dist/<provider>/<name>/`. They differ only in install path, not content.
- **gemini-cli** is the exception: Gemini commands are prompt-centric, so the
  builder generates a `.toml` custom command (`description` + the markdown body
  as `prompt`). Any `scripts/`/`references/`/`assets/` are copied *alongside* the
  command rather than embedded, so they aren't silently lost.

When adding a new provider, decide which of these two shapes it fits and extend
`build_all` accordingly.

## Frontmatter constraint (important)

The builder deliberately has **no PyYAML dependency**. `parse_frontmatter` is a
hand-rolled parser that only understands flat `key: value` scalar pairs between
`---` fences — no nested maps, lists, or multi-line values. If a skill needs
richer frontmatter, that is the signal to add a real YAML dependency to the
builder, *not* to smuggle structured data through the flat parser.

Validation enforced by `load_skill`:
- `name` frontmatter must exactly equal the skill's folder name.
- `description` must be present and non-empty.

A malformed skill raises `SkillError` and fails the build with exit code 2.

## Release workflow

Source and generated output are committed **together**. After editing anything
under `skills/`, run `python build/build.py` and commit both the source change
and the regenerated `dist/` in the same commit. CI runs `--check`, which fails if
`dist/` is stale — so never hand-edit files under `dist/`.
