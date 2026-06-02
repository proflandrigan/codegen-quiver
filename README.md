# codegen-quiver

A collection of **installable skills for coding agents** — authored once, shipped to every major coding tool.

Most coding agents have converged on the [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) standard: a `SKILL.md` file (YAML frontmatter + markdown instructions) in a skill directory. This repo treats `SKILL.md` as the **canonical source** and builds provider-specific artifacts from it, so the same skill works in Claude Code, Qwen Code, Codex, and Gemini CLI.

## Layout

```
skills/                  # canonical source of truth — author skills here
  <skill-name>/
    SKILL.md             # frontmatter (name, description) + instructions
build/
  build.py               # stdlib-only builder: skills/ -> dist/
dist/                    # generated + committed — install from here
  claude-code/<name>/SKILL.md
  qwen-code/<name>/SKILL.md
  codex/<name>/SKILL.md
  gemini-cli/commands/<name>.toml
```

You never need to run the build to *use* a skill — `dist/` is committed. The build is only for authors regenerating outputs after editing a source skill.

## Supported providers

| Provider | Artifact | Install location |
|----------|----------|------------------|
| Claude Code | `SKILL.md` directory | `.claude/skills/<name>/` (project) or `~/.claude/skills/<name>/` (global) |
| Qwen Code | `SKILL.md` directory | `.qwen/skills/<name>/` or `~/.qwen/skills/<name>/` |
| Codex | `SKILL.md` directory | `.agents/skills/<name>/` (project, scanned cwd→repo root) or `~/.codex/skills/<name>/` (global) |
| Gemini CLI | `.toml` custom command | `.gemini/commands/<name>.toml` or `~/.gemini/commands/<name>.toml` |

## Installing a skill

Copy the artifact for your tool into the matching location. For example, to install `conventional-commit` into Claude Code globally:

```bash
cp -r dist/claude-code/conventional-commit ~/.claude/skills/
```

For Gemini CLI:

```bash
cp dist/gemini-cli/commands/conventional-commit.toml ~/.gemini/commands/
```

Then invoke it in your agent (e.g. `/conventional-commit`, or let the agent trigger it by description).

## Authoring a skill

Add `skills/<name>/SKILL.md`, then rebuild:

```bash
python build/build.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the canonical format and the build/release workflow.
