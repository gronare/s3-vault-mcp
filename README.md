# s3-vault-mcp

Gives [Claude Code](https://claude.ai/download) read/write access to a markdown note vault stored in S3. Claude can search your notes for context, read them, and write new ones — directly from the S3 bucket, without any intermediate app.

Designed for [Obsidian](https://obsidian.md) vaults synced to S3 via [Remotely Save](https://github.com/remotely-save/remotely-save), but works with any S3 bucket of markdown files.

## How it works

Claude Code supports MCP (Model Context Protocol) — a standard for connecting Claude to external tools and data sources. This server implements that protocol for an S3-backed markdown vault. It runs as a Docker container; Claude Code starts it automatically when needed and communicates over stdio.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Claude Code](https://claude.ai/download) CLI

## Setup

Run this once to register the server with Claude Code. Replace the placeholder values with your S3 credentials.

```bash
claude mcp add vault \
  -s user \
  -e S3_ENDPOINT=https://your-s3.example.com \
  -e S3_ACCESS_KEY=yourkey \
  -e S3_SECRET_KEY=yoursecret \
  -e S3_BUCKET=your-bucket \
  -e S3_SEARCH_FIELDS=title,tags,path \
  -- docker run -i --rm \
    -e S3_ENDPOINT -e S3_ACCESS_KEY -e S3_SECRET_KEY -e S3_BUCKET -e S3_SEARCH_FIELDS \
    ghcr.io/gronare/s3-vault-mcp:latest
```

The `-s user` flag registers the server for your user account across all projects. Docker pulls the image automatically on first run.

**Verify:** restart Claude Code and run `/mcp` — `vault` should appear with a green connected status.

## Configure for your vault

### `S3_SEARCH_FIELDS`

Controls which [frontmatter](https://help.obsidian.md/Editing+and+formatting/Properties) fields the `search` tool matches against when you use `query=`. Set this to match the property names you use in your notes.

```bash
# If your notes have: title, tags, and a path property
-e S3_SEARCH_FIELDS=title,tags,path

# If your notes use different property names
-e S3_SEARCH_FIELDS=title,topics,area
```

The filename is always matched regardless of this setting.

### `CLAUDE.md`

`CLAUDE.md` is a plain text file that Claude Code reads at the start of every session. It lets you define conventions that Claude should follow consistently — folder structure, note format, workflow rules.

The server already sends Claude instructions on *how to use the tools* (tool cost, when to search vs read, etc.). `CLAUDE.md` is where you define *what to put in the vault* — your structure and conventions.

Create or edit `~/.claude/CLAUDE.md` (applies to all projects) and add:

```markdown
## Vault

The `vault` MCP connects to my notes in S3. Search it at the start of every
session before doing any work.

## Note structure

<!-- Describe your folder layout, e.g.: -->
- `Projects/`  — active work with a defined goal
- `Areas/`     — ongoing topics (work, homelab, etc.)
- `Resources/` — reference notes, how-tos, snippets
- `Archive/`   — completed notes; move here, never delete

<!-- Describe your frontmatter fields, e.g.: -->
Frontmatter: title, date (YYYY-MM-DD), tags, status (draft/active/complete),
path (the filesystem path this note relates to).
```

Adjust to match your actual structure. Set `S3_SEARCH_FIELDS` to the same frontmatter field names you list here.

## Tools

The server tells Claude which tools to use and when — you don't need to manage this. For reference:

| Tool | Description |
|------|-------------|
| `search` | Frontmatter only — no file bodies. Fast. Use `query=` to match across filename and configured fields. Filters: `tag=`, `status=`. |
| `read_file` | Read a single file's full content. |
| `grep_vault` | Full-text search across all file bodies. Slow — downloads everything. Last resort. |
| `list_files` | File paths only. Not useful for context lookup. |
| `write_file` | Write or overwrite a file. |
| `append_file` | Append to a file; creates it if it doesn't exist. |
| `delete_file` | Delete a file. |
| `move_file` | Move or rename — use for archiving completed notes. |
