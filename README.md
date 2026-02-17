# airewrite

Terminal-first AI rewrite assistant.

Paste text, get back an improved version, iterate.

Supports:

- OpenAI and Anthropic APIs
- Interactive persistent session (paste multi-line text)
- Multiple “modes” (proofread / rewrite / professional / concise)
- Custom modes via Markdown instruction files
- Optional persistent history (daily JSONL) with retention

## Install

This project is set up for `uv`.

```bash
uv run airewrite --help
```

If you want to install it into a virtualenv as a CLI tool:

```bash
uv sync
uv run airewrite --help
```

## Quickstart

1. Set an API key:

- OpenAI

```bash
export OPENAI_API_KEY="..."
```

- Anthropic

```bash
export ANTHROPIC_API_KEY="..."
```

1. Start the interactive session:

```bash
uv run airewrite
```

Or use the short alias:

```bash
uv run rewrite
```

## Usage

### Interactive session (persistent)

Start:

```bash
uv run airewrite
```

Then:

- Paste text (multi-line is fine)
- Submit with an **empty line** (press Enter twice)

By default, responses render with a nicer “pretty” UI using `rich`.

#### In-session commands

- `:mode <name>`
- `:provider openai|anthropic`
- `:model <model-name>`
- `:explain` (toggle adding a short explanation after the rewritten text)
- `:pretty` (toggle rich output on/off)
- `:show` (print effective configuration)
- `:where` (print resolved paths)
- `:quit`

### Non-interactive (stdin)

Pipe input:

```bash
echo "this are bad." | uv run airewrite run --mode proofread
```

Or:

```bash
cat draft.txt | uv run airewrite run --mode concise
```

## Providers

### OpenAI

- Credential: `OPENAI_API_KEY`
- Default model: `gpt-4o-mini`

Example:

```bash
uv run airewrite run --provider openai --mode proofread
```

### Anthropic

- Credential: `ANTHROPIC_API_KEY`
- Default model: `claude-3-5-sonnet-20241022`

Example:

```bash
uv run airewrite run --provider anthropic --mode professional
```

## Modes

Built-in modes:

- `proofread`
- `rewrite`
- `professional`
- `concise`

Select a mode:

```bash
uv run airewrite run --mode concise
```

### Custom modes (Markdown)

Create a file:

```text
~/.config/airewrite/modes/<mode>.md
```

Example:

```bash
mkdir -p ~/.config/airewrite/modes
cat > ~/.config/airewrite/modes/friendly.md << 'EOF'
Rewrite the text to sound friendly and approachable.
Keep it clear and professional.
Return only the rewritten text.
EOF
```

Then run:

```bash
uv run airewrite run --mode friendly
```

## History

By default, history is enabled and written as JSONL (one file per day):

```text
~/.config/airewrite/history/YYYY-MM-DD.jsonl
```

Each line contains:

- timestamp
- mode/provider/model
- explain
- input_text
- output_text

### Retention

Default retention is **30 days**.

Override:

```bash
uv run airewrite run --history-days 7
```

Disable history:

```bash
uv run airewrite run --no-history
```

### Custom history location

Override the history directory:

```bash
uv run airewrite run --history-dir ~/somewhere/airewrite-history
```

Or via env var:

```bash
export AIREWRITE_HISTORY_DIR=~/somewhere/airewrite-history
```

## Configuration inspection

Print effective config:

```bash
uv run airewrite show-config
```

Print resolved paths (config/modes/history):

```bash
uv run airewrite paths
```

Print config when starting `run`:

```bash
uv run airewrite run --print-config
```

## Pretty output

Pretty output is enabled by default in interactive mode.

Disable:

```bash
uv run airewrite run --no-pretty
```

You can also toggle it in-session with `:pretty`.
