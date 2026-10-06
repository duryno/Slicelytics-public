---
name: slicelytics
description: Open datasets in Slicelytics (slicelytics.com), a browser app for exploring, charting and comparing JSON, NDJSON/JSONL, CSV and TOON data. Use when the user asks to visualise, chart, plot, explore, inspect, diff or compare dataset files or a script's structured output, such as benchmark or eval results, experiment runs, JSONL logs or API responses - e.g. "visualise this CSV", "plot p95 latency over time", "compare these two runs", "show only the errors in this log". The data stays in the user's browser.
---

# Slicelytics

Slicelytics shows a dataset as an explorable tree (**explore**), as charts (**visualize**), or as the diff of two datasets (**compare**). You hand it data plus an optional **view** that says what to show. The user must be signed in with a Slicelytics subscription. If they aren't, a link survives login and checkout, and they land on it afterwards.

You cannot see what Slicelytics renders. After opening something, tell the user what you opened and how it's set up (e.g. "Visualize: `p95_ms` as a line over `day`, filtered to `/api/search`"), so they can confirm it's what they asked for.

## Leave the data alone

Only do what the user asked for:

- **Pass files as they are.** Don't sort, filter, aggregate, convert, clean, deduplicate or reshape the data, unless the user asks. Filtering and counting the user wants to _see_ belong in the ViewSpec (`filters`, `density`), which leaves the file untouched.
- **Read only what you need to build the view:** the field names, e.g. a CSV header or one record. For Compare, you may also read each item's key in both files, to check they're in the same order.
- **Don't analyse:** no statistics, counts, summaries, findings or descriptions of what the data shows, unless the user asks. Slicelytics is where they look at it.
- **If the data won't display well as it is** (rows out of order, two runs in different orders, an unsupported format), say what will happen and ask whether to prepare a copy. Ask before building or opening anything, and include the option to open it as it is. Don't prepare the copy on your own. If they agree, change a copy, never the original.

## Pick a route

| Situation                                                                                   | Route                                                 |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| You can only reply with text (web chat, sandbox, sharing with someone else)                 | **Link**, printed. Only when it is ≤ 8,000 characters |
| You can run commands on the user's computer                                                 | **Link**, opened (≤ 900,000 characters)               |
| Bigger data, repeated runs (e.g. an experiment loop), or a watched folder is already set up | **Watched folder**                                    |

## Link route

If the user clicks your link in a browser (e.g. in a web chat) and has the Slicelytics app installed, it opens in the app. If the app is already open, the link doesn't replace their view: the app shows "A link was opened in Slicelytics" with a **Show** button. Tell the user to click it.

Use `scripts/slicelytics_link.py` in this skill's directory, called by its absolute path (Python 3, standard library only). It infers the format from the extension, gzips and encodes the data, and picks the page. It prints the link on stdout and its length on stderr. Flags:

- `--compare FILE`: a second dataset.
- `--name` and `--compare-name`: the names shown.
- `--view JSON|FILE`: a ViewSpec.
- `--base URL`: default `https://slicelytics.com`.
- `--open`: open the link instead of printing it.
- `--app`: with `--open`, open it in the installed app.

Examples:

```sh
python3 scripts/slicelytics_link.py results.csv --view '<ViewSpec JSON>'      # prints the link
python3 scripts/slicelytics_link.py run-41.ndjson --compare run-42.ndjson --open
python3 scripts/slicelytics_link.py data.json --open --app   # macOS: in the installed app
```

To build a link without the script:

```
https://slicelytics.com/data/<explore|compare|visualize>?view=<URL-encoded ViewSpec JSON>#v=1&data=<D>&format=<F>&name=<N>
```

- `data`: the file's text, gzipped, then base64url-encoded (`-` and `_`, no `=` padding).
- `format`: `json` (the default), `ndjson`, `csv` or `toon`.
- `name` is optional.
- For Compare, add `&compare=<D2>&compareFormat=<F2>&compareName=<N2>` and use `/data/compare`.
- Every value after `#` is URL-encoded, like a query string.
- `?view=` is optional.

### Size limits

These were measured on macOS with Chrome on 2026-09-22:

- **Printed links:** keep them to 8,000 characters. Every character is output you generate and text the user has to copy. Above that, open the link or use the folder.
- **Opened links** (`open <url>`, `xdg-open`, `--app`): the OS limits one argument to 1 MiB. A 964 KB link arrived intact; a 1.29 MB one failed with "argument list too long". Keep to **900,000 characters**, and use the watched folder above that.
- **Chrome** caps URLs at 2 MB anyway.
- **Compression:** gzip makes typical JSON or CSV 5–10× smaller, and base64 adds a third back. Random numeric data only compresses about 2×. Don't guess: the script prints the length.

### Opening in the installed app (macOS, local)

`open <url>` always opens a browser tab. Chrome only routes links clicked inside the browser into an installed app. To open the installed app at a link, the script's `--app` flag runs:

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --app-id=<id> --app-launch-url-for-shortcuts-menu-item="<url>"
```

`<id>` is `CrAppModeShortcutID` in `~/Applications/Chrome Apps.localized/Slicelytics.app/Contents/Info.plist`. It differs for each install and origin; the script finds the one matching `--base`. The flag is Chrome-internal and undocumented. Use it locally and fall back to a browser tab if it fails.

## Watched folder route

**One-time setup, done by the user:**

- In Chrome or Edge, the user opens Slicelytics and clicks **Watch a folder** in the sidebar, then picks a folder. Ask which folder they picked, or suggest one (e.g. `~/Slicelytics`), and remember the path.
- Installing the app (the install icon in the address bar) makes the folder permission permanent. Otherwise, the user chooses "Allow on every visit" when the app asks to reconnect.

**Each time:**

1. Write the dataset into the folder under a new name, e.g. `run-42.ndjson`. Supported: `.json`, `.ndjson`, `.jsonl`, `.csv` or `.toon`, optionally `.gz` or `.zst`. The newest file by modification time counts as the latest run.
2. Optionally, write its view next to it: same base name, `.view.json`. So `run-42.ndjson` gets `run-42.view.json`, holding a ViewSpec.
3. Ask for it to be shown: write `slicelytics.show.json` into the folder, holding `{ "run": "run-42.ndjson" }`. Write it after the run and its view are complete.
4. Open the app: `open -a Slicelytics` on macOS. This also brings an open app to the front.
   - If the app is closed, it loads the requested run when it opens, and applies its view.
   - If it's already open, it loads the run within a couple of seconds.
   - Without a show request, a closed app opens on the newest run, if it's new since the app last saw the folder. Otherwise it reopens on what the user was last looking at.

**To compare two runs**, write both into the folder, the one to show as "original" last, so it's the newest. Then add `"compare": "<file name of the other run>"` to the newest run's `.view.json`. `compare` implies `"view": "compare"`:

```json
{ "v": 1, "compare": "run-41.ndjson" }
```

That run loads as the "current" side. Without `compare`, the current side keeps whatever the user last compared, which looks like a real comparison but isn't. If the named file is missing, the user is told, and the newest run still loads.

**Only write a show request when the user asked to see something.** A new run on its own appears in the folder list but does **not** load while the app is open. Slicelytics never swaps the data someone is looking at unasked. For runs the user didn't ask to see, e.g. each step of an experiment loop, skip the request and tell them to click the new run.

**If the app was opened with a link**, the link wins: the folder only lists its runs.

## ViewSpec

A ViewSpec is JSON describing the whole view. Anything left out is reset to its default, not kept from before.

```json
{
  "v": 1,
  "view": "visualize",
  "props": ["p95_ms", "errors"],
  "filters": { "endpoint": "/api/search" },
  "x": "day",
  "chart": "line",
  "series": { "errors": { "chart": "bar" } }
}
```

| Field     | Meaning                                                                                                                                                                |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `v`       | Always `1`.                                                                                                                                                            |
| `view`    | `explore`, `compare` or `visualize`.                                                                                                                                   |
| `props`   | Fields to show; everything else is hidden. Nested fields use dots (`a.b`). Omitted: all fields.                                                                        |
| `filters` | `{ "field": "value" }`. Keeps only items whose field equals the value, compared as strings. Several filters are ANDed. A filtered field doesn't need to be in `props`. |
| `x`       | Visualize: the field that labels the x-axis. Omitted: the item index.                                                                                                  |
| `chart`   | Visualize: chart type for every shown field. One of `bar`, `line`, `pie`, `radar`, `bubble`, `doughnut`, `polarArea`, `scatter`.                                       |
| `series`  | Visualize: per field, `{ "chart": <type>, "metric": <metric> }`. Overrides `chart`.                                                                                    |

**Metrics:**

- `density` counts items per distinct value of any field, and always draws one bar per value.
  - Example: `"props": ["endpoint"], "series": {"endpoint": {"metric": "density"}}` shows requests per endpoint.
  - The field must be shown, so put it in `props` (or leave `props` out).
  - Don't set `x` with it: `x` replaces the bars' labels.
  - Keep other fields out of that chart.
- For fields holding arrays of numbers: `sum`, `mean`, `median`, `mode`, `min`, `max`, `range`, `stdDev`, `variance`, `multiplication`.
- For arrays of dates: `min`, `max`, `range`, `density`.
- `size` gives the length of strings and arrays.
- `original` is the default: plot the values as they are.

**Getting a good chart:**

- **Visualize without a view:** a `/data/visualize` link with no `?view=` opens with no fields selected. Give a view.
- **Visualize:** plot one series per field in `props`, one point per item, in file order.
  - If the rows aren't ordered by your `x` field, a line chart will zigzag. Tell the user, and offer to sort a copy.
  - Put numeric fields in `props` and use a date or label field as `x`, not in `props`: date strings in `props` get plotted as timestamps.
- **Compare:** items are matched **by position**, not by key.
  - If the two files list their items in different orders, every item after the first mismatch shows as changed. Tell the user, and offer to sort copies of both by a key they choose. Numeric keys need a numeric sort, so `u10` comes after `u2`. With sorted copies, pass `--name` and `--compare-name` so the originals' names are shown.
  - The page shows the two datasets side by side, with changed items highlighted, plus a diff pane listing only the changes by item position (e.g. item `2`, `score: 999`).
  - A view doesn't apply on `/data/compare`, so skip `--view` there. In the watched folder, a `.view.json` with `compare` is how you get two runs side by side.
- **Two versions of one file** (e.g. a snapshot, mock or fixture changed in a pull request, often too large for GitHub to render): write each version to a temporary file with `git show <ref>:<path> > <tmp file>`, unchanged, and compare them with the older one first. That's the left side. For a pull request, the older version is at the merge base (`git merge-base origin/main HEAD`, with the PR's base branch), which is what GitHub diffs against. Pass `--name` and `--compare-name` that say which version is which, e.g. `users.json (main)` and `users.json (this PR)`.
- **Errors:** anything invalid (an unknown field, a bad chart type) is skipped, and the user is told in a message. The rest still applies.
