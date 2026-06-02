#!/usr/bin/env python3
"""Build provider-specific skill artifacts from canonical SKILL.md sources.

Canonical skills live in ``skills/<name>/SKILL.md``. This script emits one
artifact per supported coding-agent provider into ``dist/<provider>/``. Most
providers share the SKILL.md standard, so their output is a verbatim copy of the
source directory; Gemini CLI is the exception and gets a generated TOML command.

Stdlib only — no third-party dependencies. To keep frontmatter parsing trivial
without PyYAML, SKILL.md frontmatter is restricted to flat ``key: value`` scalar
pairs (see CONTRIBUTING.md).

Usage:
    python build/build.py            # rebuild dist/ in place
    python build/build.py --check    # verify dist/ is in sync; non-zero if stale
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DIST_DIR = REPO_ROOT / "dist"

# Providers that consume the SKILL.md standard verbatim. The value is the
# subdirectory under dist/ where each skill directory is copied.
SKILL_MD_PROVIDERS = ("claude-code", "qwen-code", "codex")


class SkillError(Exception):
    """Raised when a canonical skill is malformed."""


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a SKILL.md into (frontmatter dict, markdown body).

    Frontmatter is the block between the leading ``---`` fences. Only flat
    ``key: value`` scalar pairs are supported.
    """
    if not text.startswith("---"):
        raise SkillError("missing leading '---' frontmatter fence")

    lines = text.splitlines()
    # lines[0] is the opening fence; find the closing fence.
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise SkillError("missing closing '---' frontmatter fence")

    frontmatter: dict[str, str] = {}
    for raw in lines[1:close]:
        if not raw.strip():
            continue
        if ":" not in raw:
            raise SkillError(f"frontmatter line is not 'key: value': {raw!r}")
        key, value = raw.split(":", 1)
        frontmatter[key.strip()] = value.strip()

    body = "\n".join(lines[close + 1:]).strip() + "\n"
    return frontmatter, body


def load_skill(skill_dir: Path) -> tuple[dict[str, str], str]:
    """Read and validate a skill's SKILL.md."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SkillError(f"{skill_dir.name}: no SKILL.md")

    frontmatter, body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))

    name = frontmatter.get("name", "")
    if name != skill_dir.name:
        raise SkillError(
            f"{skill_dir.name}: frontmatter name {name!r} must equal folder name"
        )
    if not frontmatter.get("description"):
        raise SkillError(f"{skill_dir.name}: frontmatter 'description' is required")

    return frontmatter, body


def toml_basic_string(value: str) -> str:
    """Quote a value as a TOML basic (single-line) string."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def toml_multiline_string(value: str) -> str:
    """Quote a value as a TOML multi-line basic string."""
    escaped = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{escaped}"""'


def build_skill_md_provider(skill_dir: Path, provider: str, out_root: Path) -> None:
    """Copy a skill directory verbatim for a SKILL.md-native provider."""
    dest = out_root / provider / skill_dir.name
    shutil.copytree(skill_dir, dest)


def build_gemini(skill_dir: Path, frontmatter: dict[str, str], body: str,
                 out_root: Path) -> None:
    """Emit a Gemini CLI TOML custom command from a canonical skill."""
    commands_dir = out_root / "gemini-cli" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"description = {toml_basic_string(frontmatter['description'])}",
        f"prompt = {toml_multiline_string(body)}",
    ]
    out_file = commands_dir / f"{skill_dir.name}.toml"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Gemini commands are prompt-centric; bundled scripts/references are not
    # part of the command file. Copy them alongside so nothing is silently lost.
    for extra in ("scripts", "references", "assets"):
        src = skill_dir / extra
        if src.is_dir():
            shutil.copytree(src, commands_dir / skill_dir.name / extra)


def build_all(out_root: Path) -> list[str]:
    """Build every skill into out_root. Returns the list of skill names built."""
    if not SKILLS_DIR.is_dir():
        raise SkillError(f"no skills/ directory at {SKILLS_DIR}")

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )
    if not skill_dirs:
        raise SkillError("no skills found under skills/")

    if out_root.exists():
        shutil.rmtree(out_root)

    built: list[str] = []
    for skill_dir in skill_dirs:
        frontmatter, body = load_skill(skill_dir)
        for provider in SKILL_MD_PROVIDERS:
            build_skill_md_provider(skill_dir, provider, out_root)
        build_gemini(skill_dir, frontmatter, body, out_root)
        built.append(skill_dir.name)

    return built


def dirs_equal(a: Path, b: Path) -> bool:
    """Recursively compare two directory trees for identical content."""
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(
        dirs_equal(a / sub, b / sub) for sub in cmp.common_dirs
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="verify committed dist/ matches a fresh build; exit non-zero if stale",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dist = Path(tmp) / "dist"
                built = build_all(tmp_dist)
                if not DIST_DIR.exists() or not dirs_equal(DIST_DIR, tmp_dist):
                    print(
                        "dist/ is out of sync with skills/. Run: python build/build.py",
                        file=sys.stderr,
                    )
                    return 1
            print(f"dist/ is in sync ({len(built)} skill(s)).")
            return 0

        built = build_all(DIST_DIR)
    except SkillError as exc:
        print(f"build error: {exc}", file=sys.stderr)
        return 2

    providers = ", ".join((*SKILL_MD_PROVIDERS, "gemini-cli"))
    print(f"Built {len(built)} skill(s) for: {providers}")
    for name in built:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
