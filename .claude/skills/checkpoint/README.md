# checkpoint — compact-proof Claude Code sessions

A self-contained, **portable** skill that makes a Claude Code session survive
context **compaction** (`/compact`, auto-compact, resume) without losing
operational state. Stdlib-only, dependency-free; drops into any project.

---

## The problem

When Claude Code compacts a long session it replaces the transcript with an
auto-summary. That summary reliably drops the *operational* facts a resumed
session needs first: which processes are running and on what PIDs, the exact git
state, what you were about to do next, which files you just touched. You re-discover
all of it by hand.

## The mechanism

```
              ┌──────────────────────── before compaction ───────────────────────┐
 /compact ─▶  PreCompact hook ─▶ session_checkpoint.py --write
                                    │ snapshots:
                                    │  • processes (pgrep patterns)
                                    │  • git: branch, dirty?, recent commits
                                    │  • handoff doc "## Pending" section
                                    │  • recently-changed source files
                                    ▼
                            .claude/checkpoints/latest.md  (+ timestamped backups)
              └────────────────────────────────────────────────────────────────────┘

              ┌──────────────────────── after compaction ────────────────────────┐
 new session ─▶ SessionStart hook ─▶ session_checkpoint.py --session-start
                                    │ emits JSON hookSpecificOutput.additionalContext
                                    ▼
                            Claude Code injects it into the new session context
              └────────────────────────────────────────────────────────────────────┘
```

One script, two modes — the same proven design this project runs in production.
`CONTINUITY.md` is the one human-maintained piece: keep its **## Pending** section
current and the next session always knows what to do first.

## Install

From a project that has this skill at `.claude/skills/checkpoint/`:

```bash
# install into the current project (idempotent; preserves existing hooks)
python3 .claude/skills/checkpoint/scripts/install.py --target . --with-config

# preview without writing
python3 .claude/skills/checkpoint/scripts/install.py --target . --dry-run

# port into another project
python3 .claude/skills/checkpoint/scripts/install.py --target /path/to/other --with-config

# remove (leaves checkpoints/ and CONTINUITY.md in place)
python3 .claude/skills/checkpoint/scripts/install.py --target . --uninstall
```

The installer:

1. copies `session_checkpoint.py` → `<target>/.claude/hooks/`
2. **merges** the PreCompact + SessionStart hooks into `<target>/.claude/settings.json`
   (existing hooks left intact)
3. adds `checkpoints/` to `<target>/.claude/.gitignore`
4. seeds `CONTINUITY.md` from the template (only if absent)
5. with `--with-config`, seeds `.claude/continuity.json`

**Idempotent** — re-running never duplicates hooks.

> **Note on this repo:** the live hooks here point at `scripts/session_checkpoint.py`
> (project root) — the original install. The skill bundles an enhanced, portable copy
> under `scripts/`. Running `install.py --target .` would additionally wire the
> `.claude/hooks/` copy; the project root copy already works, so re-pointing is
> optional. For *other* projects, just run the installer.

## Configure (optional)

Without config it auto-detects and uses defaults. To customise, edit
`.claude/continuity.json` (see `scripts/continuity_config.example.json`):

| key | default | meaning |
|---|---|---|
| `processes` | `[]` | `pgrep -f <pattern>` entries pinned in the checkpoint; empty → section skipped |
| `handoff_doc` | auto | doc to extract pending from; auto-detects `CONTINUITY.md` → `RESTART_PROTOCOL.md` → `HANDOFF.md` → `SESSION.md` |
| `pending_markers` | `["Pending","다음 명령","다음 작업","Next actions"]` | section headers to extract |
| `pending_lines` | `40` | max lines of that section |
| `watch_globs` | common code exts | which recently-changed files to list |
| `recent_minutes` | `180` | change window |
| `max_recent_files` | `20` | cap on listed files |
| `inject_max_lines` | `80` | bound on what SessionStart injects |
| `recovery_checklist` | none | ordered first-actions-after-compact, printed in the checkpoint |
| `timezone_offset_hours` | `null` (local) | e.g. `9` for KST timestamps |
| `git_log_count` | `10` | recent commits shown |
| `keep_backups` | `20` | timestamped copies retained |

## Test

```bash
python3 .claude/skills/checkpoint/tests/test_checkpoint.py
# → 25 passed, 0 failed
# (also pytest-compatible:  pytest .claude/skills/checkpoint/tests/)
```

25 stdlib tests cover checkpoint generation (git/dirty/pending/Korean markers/
recent-files/process toggle/recovery-checklist/config/parse-error), write+prune,
both `--write` and `--session-start` modes, root resolution, and the installer
(merge/idempotency/preserve-existing/unmerge/dry-run/full/uninstall + an
end-to-end install→write→restore). Git-dependent tests self-skip if `git` is absent.

## Verify a live install

```bash
python3 .claude/hooks/session_checkpoint.py                 # prints a checkpoint (writes latest.md)
python3 .claude/hooks/session_checkpoint.py --session-start # emits the SessionStart JSON
```

Then trigger `/compact` and confirm the next session opens with a
"🔖 Session Checkpoint" block in its context.

## Two ways Claude uses this

- **Manual checkpoint of the current session** (before `/compact`): run `--write`,
  then append a short "## 🧠 현재 초점" block to `latest.md` with the conversational
  state the script can't infer (decisions in flight, the next move). See SKILL.md §A.
- **Install / port** the system into this or another project. See SKILL.md §B.

## Design notes

- **Portable by construction**: stdlib only; project root resolves from
  `$CLAUDE_PROJECT_DIR` (set by Claude Code) or by walking up to a `.git`/`.claude`
  marker, so the same file works at `scripts/` or `.claude/hooks/`.
- **Non-destructive**: settings merge is additive and idempotent.
- **Graceful**: missing git, missing handoff doc, malformed config, or no checkpoint
  all degrade quietly — a hook never blocks compaction or session start.
- **Local vs portable**: `.claude/checkpoints/` is machine state (git-ignored). The
  scripts, `settings.json` wiring, `continuity.json`, and `CONTINUITY.md` are what
  you commit and carry between projects.
```
