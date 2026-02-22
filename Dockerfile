FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock s3_vault_mcp.py ./
RUN uv sync --frozen --no-dev
ENTRYPOINT ["uv", "run", "s3-vault-mcp"]
