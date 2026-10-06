# Slicelytics

[Slicelytics.com](https://slicelytics.com?utm_source=github)

This is a public Slicelytics repository containing Agent skills for, e.g., Claude Code, Codex & Cursor, useful to visualise, explore and compare JSON, NDJSON, CSV and TOON data in Slicelytics.

Feel free to open new issues for any support requests, feedback, or feature requests.

## What the skill does

The `slicelytics` skill lets your coding agent (Claude Code, Codex, Cursor, …) open data in [Slicelytics](https://slicelytics.com?utm_source=github) with the view already set up. You don't need a throwaway plotting script or a spreadsheet import. Ask the agent to show you the data, and it hands Slicelytics the file along with a view that sets which fields to show, how to filter them and which chart to draw.

Slicelytics has three views:

- **Explore**: browse a dataset as a collapsible tree, showing only the fields you care about.
- **Visualize**: chart one or more fields as bar, line, pie, scatter and other chart types. It can also count values per category or summarise arrays (mean, median, max, …).
- **Compare**: put two datasets side by side, with changed items highlighted and a list of exactly what changed.

It works with JSON, NDJSON/JSONL, CSV and TOON files, including gzipped & Zstandard-compressed ones.

### When to use it

It fits best when your agent produces or reads structured data that you want to *look at*, not just read about:

- **Benchmarks and evals:** "plot p95 latency per day for `/api/search` in Slicelytics"
- **Experiment loops:** the agent writes each run into a watched folder, and you open any run or compare two of them as they come in.
- **Comparing runs:** "compare run-41.ndjson and run-42.ndjson"
- **Comparing diffs too large to preview in GitHub:** "compare snapshot.ndjson from PR #1000 with master"
- **Logs:** "show only the errors in this JSONL log"
- **API responses and other ad-hoc output:** "open this response in Slicelytics"
- **Data files:** "visualise results.csv"

Since the agent can't see what Slicelytics renders, it tells you what it opened and how the view is set up (e.g. "Visualize: `p95_ms` as a line over `day`, filtered to `/api/search`"), so you can check it's what you asked for.

### How it gets the data to Slicelytics

- **Link:** for small and medium datasets, the bundled script compresses the file into a link and opens it in your browser or in the installed Slicelytics app. In web chats, the agent prints the link instead. The data lives in the link's `#fragment`, which browsers never send to a server.
- **Watched folder:** for bigger data or repeated runs, you point Slicelytics at a local folder once (Chrome or Edge). The agent then writes runs into it and asks the app to show them. Slicelytics never swaps out what you're looking at unless you asked to see the new run.

In both cases the data stays in your browser.

### What the agent won't do

The skill tells the agent to leave your data alone. It passes files as they are and reads only the field names it needs to build the view. It doesn't analyse or summarise the data unless you ask. If the data won't display well as it is (e.g. rows out of order for a line chart, or two runs listed in different orders for a comparison), the agent asks you before preparing a sorted copy, and it never modifies the original.

### Requirements

- A Slicelytics account. If you're not signed in, the link still works after login and checkout.
- Python 3 for the link script (standard library only).
- Chrome or Edge for the watched folder.

## Installing the skills

The [`slicelytics`](.agents/skills/slicelytics/SKILL.md) skill follows the open [Agent Skills](https://agentskills.io) format: a folder with a `SKILL.md` and a helper script (`scripts/slicelytics_link.py`, Python 3, standard library only).

### Claude Code plugin

This repository is also a Claude Code plugin marketplace. In a Claude Code session, run:

```
/plugin marketplace add duryno/Slicelytics-public
/plugin install slicelytics@slicelytics
```

Or, from your shell:

```sh
claude plugin marketplace add duryno/Slicelytics-public
claude plugin install slicelytics@slicelytics
```

Then ask Claude to e.g. "visualise results.csv in Slicelytics", or run `/slicelytics:slicelytics`. To update, run `claude plugin update slicelytics@slicelytics`.

### Copying the skill folder

For other agents, or to use the skill without the plugin, copy the skill folder into the directory where your agent looks for skills. First, download this repository:

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
