# Contributing

Skills are authored once in canonical form and built into provider-specific
artifacts. This document defines the canonical format and the build workflow.

## Canonical skill format

Every skill is a directory under `skills/` containing a `SKILL.md` file:

```
skills/
  my-skill/
    SKILL.md          # required
    scripts/          # optional — helper scripts, copied through verbatim
    references/       # optional — extra docs loaded on demand
    assets/           # optional — templates, binaries
```

`SKILL.md` has YAML-style frontmatter between `---` fences, followed by a
markdown body of instructions:

```markdown
---
name: my-skill
description: What the skill does and when it should trigger. Be specific — agents use this to decide when to invoke it.
---

# My Skill

Step-by-step instructions for the agent...
```

### Frontmatter rules

The builder is **stdlib-only (no PyYAML)**, so frontmatter is restricted to flat
`key: value` scalar pairs — no nested maps, lists, or multi-line values.

| Key | Required | Notes |
|-----|----------|-------|
| `name` | yes | Must equal the skill's folder name. Lowercase letters, digits, hyphens. |
| `description` | yes | Non-empty. Describes *what* and *when*. |
| `manual` | no | `true` to only activate on explicit invocation. |
| `when_to_use` | no | Extra trigger guidance. |

If you genuinely need richer frontmatter, that's the trigger to add a YAML
dependency to the builder — don't smuggle structured data through the flat parser.

## Building

```bash
python build/build.py          # regenerate dist/ from skills/
python build/build.py --check  # verify dist/ matches skills/ (CI / pre-push)
```

The build emits one artifact per provider into `dist/`:

- **claude-code**, **qwen-code**, **codex** — the skill directory copied verbatim
  (all three consume the `SKILL.md` standard; they differ only by install path).
- **gemini-cli** — a generated `.toml` custom command with `description` and a
  `prompt` containing the markdown body. Gemini commands are prompt-centric, so
  any `scripts/`/`references/`/`assets/` are copied alongside the command rather
  than embedded.

## Release workflow

1. Add or edit a skill under `skills/`.
2. Run `python build/build.py`.
3. Commit **both** the source change and the regenerated `dist/` together.
4. `python build/build.py --check` must pass — it fails if `dist/` is stale,
   which keeps generated output honest in review and CI.
