# Slicelytics

[Slicelytics.com](https://slicelytics.com?utm_source=github)

This is a public Slicelytics repository containing Agent skills for, e.g., Claude Code, Codex & Cursor, useful to visualise, explore and compare JSON, NDJSON, CSV and TOON data in Slicelytics.

Feel free to open new issues for any support requests, feedback, or feature requests.


## Installing the skills

The [`slicelytics`](.agents/skills/slicelytics/SKILL.md) skill follows the open [Agent Skills](https://agentskills.io) format: a folder with a `SKILL.md` and a helper script (`scripts/slicelytics_link.py`, Python 3, standard library only). To install it, copy that folder into the directory where your agent looks for skills.

First, download this repository:

```sh
git clone --depth 1 https://github.com/duryno/Slicelytics-public.git /tmp/slicelytics-public
```

### Claude Code

```sh
mkdir -p ~/.claude/skills
cp -R /tmp/slicelytics-public/.agents/skills/slicelytics ~/.claude/skills/
```

To install it for a single project only, copy it into `.claude/skills/` in that project instead. Start a new session, then ask Claude to e.g. "visualise results.csv in Slicelytics", or run `/slicelytics`.

### OpenAI Codex

```sh
mkdir -p ~/.agents/skills
cp -R /tmp/slicelytics-public/.agents/skills/slicelytics ~/.agents/skills/
```

To install it for a single project only, copy it into `.agents/skills/` in that repository instead. Restart Codex, then ask it to e.g. "plot p95 latency over time in Slicelytics", or mention `$slicelytics`.

### Cursor

```sh
mkdir -p ~/.cursor/skills
cp -R /tmp/slicelytics-public/.agents/skills/slicelytics ~/.cursor/skills/
```

To install it for a single project only, copy it into `.cursor/skills/` (or `.agents/skills/`) in that project instead. Cursor also picks up skills already installed in `~/.claude/skills/` or `~/.agents/skills/`, so if you've installed it for Claude Code or Codex, you're done. Restart Cursor, then ask the agent to e.g. "compare run-41.ndjson and run-42.ndjson in Slicelytics".

### Updating

To update, delete the installed `slicelytics` folder and repeat the steps above.
