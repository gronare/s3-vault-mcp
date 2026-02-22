# s3-vault-mcp

MCP server that gives Claude direct read/write access to a markdown vault stored in any S3-compatible bucket. Designed for use with [Obsidian](https://obsidian.md) vaults synced to S3 via [Remotely Save](https://github.com/remotely-save/remotely-save) or similar, but works with any bucket of markdown files.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Claude Code](https://claude.ai/download) CLI

## Add to Claude Code

```bash
claude mcp add vault \
  -s user \
  -e S3_ENDPOINT=https://your-s3.example.com \
  -e S3_ACCESS_KEY=yourkey \
  -e S3_SECRET_KEY=yoursecret \
  -e S3_BUCKET=obsidian \
  -e S3_SEARCH_FIELDS=title,tags,path \
  -- docker run -i --rm \
    -e S3_ENDPOINT -e S3_ACCESS_KEY -e S3_SECRET_KEY -e S3_BUCKET -e S3_SEARCH_FIELDS \
    ghcr.io/gronare/s3-vault-mcp:latest
```

Docker pulls the image automatically on first run. Verify the registration with `claude mcp get vault`, then restart Claude Code and check `/mcp`.

## Configuration

### `S3_SEARCH_FIELDS`

Controls which frontmatter fields the `search` tool matches against. Defaults to `title,tags,path`. Adjust to match your vault's frontmatter conventions:

```bash
# Default — matches title, tags list, and path field
-e S3_SEARCH_FIELDS=title,tags,path

# Custom — if your notes use different field names
-e S3_SEARCH_FIELDS=title,topics,area
```

The filename stem is always included in matching regardless of this setting.

## Recommended CLAUDE.md setup

Add the following to your `CLAUDE.md` to get consistent behaviour across sessions. The server sends tool usage instructions to Claude automatically via the MCP `instructions` field, so you only need to define your vault's content conventions here.

```markdown
## Vault MCP

The `vault` MCP connects to my Obsidian vault in S3. Use it at the start
of every session to search for context before doing any work.

## Note Conventions

PARA folder structure:
- `Projects/`  — active work with a clear goal
- `Areas/`     — ongoing responsibilities
- `Resources/` — reference notes, how-tos, snippets
- `Archive/`   — completed work; move here, never delete

Frontmatter fields: title, date (YYYY-MM-DD), tags, status
(draft/active/complete), path (filesystem path this note relates to).

Use [[wikilinks]] for cross-references. Before creating a new note,
search for an existing one that covers the same topic.

When starting new work, create a plan note in the vault before writing
any code or making changes.
```

Adjust the PARA structure and frontmatter fields to match your own conventions, and set `S3_SEARCH_FIELDS` to match.

## Tools

| Tool | Cost | Description |
|------|------|-------------|
| `search` | Low | Frontmatter metadata only — no file bodies. Use first for context lookup. Supports `query=` for free-text match across filename and configured fields. |
| `read_file` | — | Read a single file's full content |
| `grep_vault` | High | Full-text body search — downloads every file. Last resort only. |
| `list_files` | Low | File paths only. Not useful for context lookup. |
| `write_file` | — | Write or overwrite a file |
| `append_file` | — | Append to a file, creates if missing |
| `delete_file` | — | Delete a file |
| `move_file` | — | Move or rename — useful for archiving completed notes |
