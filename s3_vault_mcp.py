#!/usr/bin/env python3
"""
S3 Vault MCP Server
Generic S3-backed markdown vault — works with MinIO or any S3-compatible storage.
"""

import os
import asyncio
from typing import Any

import yaml
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ——————————————————————————————
# Config from environment
# ——————————————————————————————

S3_ENDPOINT   = os.environ["S3_ENDPOINT"]     # e.g. https://minio.example.com
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_BUCKET     = os.environ.get("S3_BUCKET", "obsidian")

# Comma-separated frontmatter fields to include in search() query matching.
# Adapt to your team's note conventions.
# Default covers: title, tags list, and path field.
_SEARCH_FIELDS_ENV = os.environ.get("S3_SEARCH_FIELDS", "title,tags,path")
SEARCH_FIELDS = [f.strip() for f in _SEARCH_FIELDS_ENV.split(",") if f.strip()]

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)

SERVER_INSTRUCTIONS = """\
S3 Vault MCP — tool usage guide

Tools are listed cheapest-first. Always start with the cheapest tool that can answer the question.

────────────────────────────────────────
1. search  ← START HERE for context lookup
────────────────────────────────────────
Returns frontmatter metadata only. Does NOT fetch file bodies. Fast.

Use query= to match across filename, title, tags, and configured path fields simultaneously:
  search(query="secret-santa")        # finds all notes mentioning secret-santa anywhere in metadata
  search(query="homelab", tag="apps") # combine free-text with tag filter

Filters (applied after query):
  tag=      exact tag match
  status=   e.g. active, draft, complete
  fs_path=  substring match on the path frontmatter field

Session-start pattern:
  1. search(query="<topic or directory name>")
  2. read_file on the 2-3 most relevant results
  3. Proceed with full context

────────────────────────────────────────
2. read_file
────────────────────────────────────────
Reads a single file's full content. Use after search has identified the relevant notes.

────────────────────────────────────────
3. grep_vault  ← LAST RESORT
────────────────────────────────────────
Full-text search — downloads every file in the vault. Expensive.
Only reach for this when search + read_file cannot answer the question
(e.g. searching for a specific string inside note bodies).

────────────────────────────────────────
4. list_files
────────────────────────────────────────
Returns file paths only — no content, no metadata.
Not useful for context lookup. Use search instead.

────────────────────────────────────────
5. write_file, append_file, delete_file, move_file
────────────────────────────────────────
Standard file operations. move_file is useful for archiving completed notes.
"""

app = Server("s3-vault", instructions=SERVER_INSTRUCTIONS)

# ——————————————————————————————
# Tools
# ——————————————————————————————

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search",
            description=(
                "CHEAPEST — use this first. Returns frontmatter metadata for all notes "
                "without fetching file bodies. Use query= to match across filename, title, "
                "tags, and path fields in one call. Then read_file only the notes you need. "
                "Supports optional tag, status, fs_path filters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Optional vault directory prefix to limit scope", "default": ""},
                    "query":   {"type": "string", "description": "Free-text match across filename, title, tags, and path fields (case-insensitive)"},
                    "tag":     {"type": "string", "description": "Only return notes containing this exact tag"},
                    "status":  {"type": "string", "description": "Only return notes with this status (e.g. active, draft, complete)"},
                    "fs_path": {"type": "string", "description": "Filter by filesystem path field in frontmatter (substring match)"},
                },
            },
        ),
        Tool(
            name="read_file",
            description="Read the content of a markdown file from the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path e.g. 'Projects/my-plan.md'"}
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="Write or overwrite a markdown file in the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "File path e.g. 'Projects/my-plan.md'"},
                    "content": {"type": "string", "description": "Full markdown content to write"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="append_file",
            description="Append content to an existing file, or create it if it doesn't exist",
            inputSchema={
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                    "content": {"type": "string", "description": "Markdown content to append"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="delete_file",
            description="Delete a file from the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="move_file",
            description="Move or rename a file — useful for archiving completed projects",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Current file path"},
                    "dest":   {"type": "string", "description": "New file path"},
                },
                "required": ["source", "dest"],
            },
        ),
        Tool(
            name="list_files",
            description="List all files in the vault or in a specific directory. Returns paths only — no metadata. Use search instead for context lookup.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional directory prefix e.g. 'Projects/' or 'Areas/homelab'",
                        "default": "",
                    }
                },
            },
        ),
        Tool(
            name="grep_vault",
            description=(
                "EXPENSIVE — last resort. Full-text search: downloads every file in the vault. "
                "Only use when search + read_file are not sufficient (e.g. searching inside note bodies). "
                "Prefer search for all metadata/context lookups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query":       {"type": "string", "description": "Text to search for"},
                    "path":        {"type": "string", "description": "Optional directory to limit search", "default": ""},
                    "max_results": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
    ]

# ——————————————————————————————
# Helpers
# ——————————————————————————————

def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a markdown file. Returns empty dict if none."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[4:end]) or {}
    except Exception:
        return {}


def _matches_query(key: str, fm: dict, query: str) -> bool:
    """Return True if the note matches the free-text query against filename + SEARCH_FIELDS."""
    q = query.lower()
    # Always check filename stem
    stem = key.rsplit("/", 1)[-1].removesuffix(".md").lower()
    if q in stem:
        return True
    # Check configured frontmatter fields
    for field in SEARCH_FIELDS:
        val = fm.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            if any(q in str(v).lower() for v in val):
                return True
        else:
            if q in str(val).lower():
                return True
    return False


def list_all_keys(prefix: str = "") -> list[str]:
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def get_object(key: str) -> str:
    resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return resp["Body"].read().decode("utf-8")


def put_object(key: str, content: str) -> None:
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/markdown",
    )

# ——————————————————————————————
# Tool handlers
# ——————————————————————————————

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except Exception as e:
        result = f"Error: {e}"
    return [TextContent(type="text", text=result)]


async def _dispatch(name: str, args: dict) -> str:
    if name == "search":
        prefix = args.get("path", "")
        query = args.get("query", "").strip()
        tag_filter = args.get("tag", "").lower()
        status_filter = args.get("status", "").lower()
        fs_path_filter = args.get("fs_path", "").lower()
        keys = [k for k in list_all_keys(prefix) if k.endswith(".md")]

        rows = []
        for key in keys:
            try:
                content = get_object(key)
            except Exception:
                continue
            fm = parse_frontmatter(content)
            if not fm:
                continue

            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tags_lower = [t.lower() for t in tags]

            status = str(fm.get("status", "")).lower()
            fs_path = str(fm.get("path", "")).lower()

            if query and not _matches_query(key, fm, query):
                continue
            if tag_filter and tag_filter not in tags_lower:
                continue
            if status_filter and status != status_filter:
                continue
            if fs_path_filter and fs_path_filter not in fs_path:
                continue

            title = fm.get("title", "")
            tags_str = ", ".join(tags)
            path_str = fm.get("path", "")
            rows.append(f"{key} | {title} | [{tags_str}] | {status} | {path_str}")

        if not rows:
            return "No notes matched."
        return "\n".join(rows)

    elif name == "list_files":
        prefix = args.get("path", "")
        keys = list_all_keys(prefix)
        if not keys:
            return f"No files found under '{prefix}'"
        return "\n".join(keys)

    elif name == "read_file":
        return get_object(args["path"])

    elif name == "write_file":
        put_object(args["path"], args["content"])
        return f"Written: {args['path']}"

    elif name == "append_file":
        path = args["path"]
        try:
            existing = get_object(path)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                existing = ""
            else:
                raise
        put_object(path, existing + "\n" + args["content"])
        return f"Appended to: {path}"

    elif name == "delete_file":
        s3.delete_object(Bucket=S3_BUCKET, Key=args["path"])
        return f"Deleted: {args['path']}"

    elif name == "move_file":
        content = get_object(args["source"])
        put_object(args["dest"], content)
        s3.delete_object(Bucket=S3_BUCKET, Key=args["source"])
        return f"Moved: {args['source']} → {args['dest']}"

    elif name == "grep_vault":
        query = args["query"].lower()
        prefix = args.get("path", "")
        max_results = args.get("max_results", 20)
        keys = [k for k in list_all_keys(prefix) if k.endswith(".md")]

        results = []
        for key in keys:
            try:
                content = get_object(key)
            except Exception:
                continue
            lines = content.splitlines()
            matches = [
                f"  L{i+1}: {line.strip()}"
                for i, line in enumerate(lines)
                if query in line.lower()
            ]
            if matches:
                results.append(f"{key}:\n" + "\n".join(matches))
            if len(results) >= max_results:
                break

        if not results:
            return f"No results for '{query}'"
        return "\n\n".join(results)

    else:
        return f"Unknown tool: {name}"

# ——————————————————————————————
# Entrypoint
# ——————————————————————————————

async def _main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
