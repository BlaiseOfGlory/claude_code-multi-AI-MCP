# Multi-AI MCP Server

MCP server that gives any MCP-compatible agent access to Gemini, Grok, and DeepSeek. Works with Claude Code, Cursor, Windsurf, Cline, and anything else that speaks the [Model Context Protocol](https://modelcontextprotocol.io). Forked from [RaiAnsar/claude_code-multi-AI-MCP](https://github.com/RaiAnsar/claude_code-multi-AI-MCP) and rebuilt for a minimal, cost-aware tool surface.

## What Changed From Upstream

v1.0.0 shipped 22 tools. Most were prompt templates (code_review, brainstorm, debug, architecture, think_deep — 5 variants per model) that an LLM doesn't need, plus multi-model orchestration tools (ask_all_ais, ai_debate, collaborative_solve, ai_consensus) that were broken — the "debate" never passed context between models, "collaborative_solve" never forwarded previous outputs, "consensus" just concatenated responses.

v2.0.0 stripped that to **4 tools** and added system prompt support and Grok web search.

v2.1.0 restructured as a UV tool — one command to install, one command to configure.

v2.1.1 pinned dependencies with `uv.lock` for supply chain protection, made Claude Code registration optional during `--setup`, and added generic MCP client configuration docs (Cursor, Windsurf, Cline, etc.).

## Install

```bash
# Install directly from GitHub
uv tool install git+https://github.com/BlaiseOfGlory/multi-ai-mcp.git

# Interactive setup — prompts for API keys, optionally registers with Claude Code
multi-ai-collab --setup
```

Or run without installing:

```bash
uvx --from git+https://github.com/BlaiseOfGlory/multi-ai-mcp.git multi-ai-collab --setup
```

### MCP Client Configuration

The `--setup` wizard can auto-register with Claude Code. If you skipped that step or use a different agent, configure your MCP client manually. The server uses **stdio transport** — your client runs the command and communicates over stdin/stdout.

#### Claude Code

```bash
claude mcp add --scope user multi-ai-collab -- multi-ai-collab
```

Or with `uvx` (no install needed):

```bash
claude mcp add --scope user multi-ai-collab -- uvx --from git+https://github.com/BlaiseOfGlory/multi-ai-mcp.git multi-ai-collab
```

#### Cursor / Windsurf / Cline / Generic MCP Clients

Add to your MCP configuration file (location varies by client):

```json
{
  "mcpServers": {
    "multi-ai-collab": {
      "type": "stdio",
      "command": "multi-ai-collab",
      "args": []
    }
  }
}
```

If you installed via `uvx` without a persistent install, use the full path:

```json
{
  "mcpServers": {
    "multi-ai-collab": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/BlaiseOfGlory/multi-ai-mcp.git", "multi-ai-collab"]
    }
  }
}
```

Common config file locations:
- **Cursor:** `.cursor/mcp.json` in your project or `~/.cursor/mcp.json` globally
- **Windsurf:** `~/.codeium/windsurf/mcp_config.json`
- **Cline:** VS Code settings → Cline MCP Servers

## Tools

Only enabled providers appear as tools. If you only have a Gemini key, you only see `ask_gemini` + `server_status`.

| Tool | Description |
|------|-------------|
| `server_status` | Check which models are configured and available |
| `ask_gemini` | Query Google Gemini |
| `ask_grok` | Query xAI Grok. Set `web_search=true` for live web results with citations. |
| `ask_deepseek` | Query DeepSeek |
| `ask_openai` | Query OpenAI (optional — configure if you have a key) |

### Common Parameters (all `ask_*` tools)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | *required* | The question or prompt |
| `system_prompt` | string | `""` | Set the model's role or constraints |
| `temperature` | number | `0.7` | Response temperature (0.0-1.0) |

### Grok-Only Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `web_search` | boolean | `false` | Enable live web search via xAI Responses API |
| `allowed_domains` | string[] | `[]` | Restrict search to these domains (max 5) |
| `excluded_domains` | string[] | `[]` | Exclude these domains from search (max 5) |

`allowed_domains` and `excluded_domains` are mutually exclusive and only apply when `web_search=true`.

## Models

| Provider | Default Model | Billing |
|----------|---------------|---------|
| Gemini | gemini-2.0-flash | Free tier (rate-limited) |
| Grok | grok-3 | Per-token |
| DeepSeek | deepseek-chat | Per-token |
| OpenAI | gpt-4o | Per-token (optional) |

Models are configured during `--setup`. Change them later by editing `~/.config/multi-ai-collab/credentials.json`.

## CLI

```bash
multi-ai-collab            # Run MCP server (stdio transport)
multi-ai-collab --setup    # Interactive configuration wizard
multi-ai-collab --status   # Show configured providers
multi-ai-collab --version  # Print version
```

## Usage Examples

```
# Basic query
ask_gemini(prompt="Explain the CAP theorem")

# With system prompt for focused output
ask_deepseek(prompt="Review this function", system_prompt="You are a security auditor. Focus only on injection vulnerabilities.")

# Grok with web search
ask_grok(prompt="What happened in tech news today?", web_search=true)

# Grok web search restricted to specific domains
ask_grok(prompt="Latest Claude Code features", web_search=true, allowed_domains=["docs.anthropic.com", "github.com"])
```

The caller handles all orchestration — if you need multiple models' opinions, make parallel `ask_*` calls. If you need debate or consensus, write the synthesis prompt yourself. Your agent is better at this than a server-side script.

## Cost Awareness

Gemini is rate-limited but free. Grok and DeepSeek are billed per token. Web search on Grok uses the Responses API which may have different pricing than Chat Completions. Don't fire these on every request — use them for cross-validation, conflict resolution, and cases where a second model's perspective adds real signal.

## Configuration

Credentials are stored at `~/.config/multi-ai-collab/credentials.json` (override with `MULTI_AI_COLLAB_CONFIG` env var).

To reconfigure: `multi-ai-collab --setup` (preserves existing keys, lets you update or skip each provider).

## Security

- Credentials stored locally in `~/.config/multi-ai-collab/credentials.json`
- Never commit credentials to version control
- Failed connections don't crash the server
- No data is logged or stored by the MCP server

## API Keys

- **Gemini** (free): [Google AI Studio](https://aistudio.google.com/apikey)
- **Grok** (paid): [xAI Console](https://console.x.ai/)
- **DeepSeek** (paid): [DeepSeek Platform](https://platform.deepseek.com/)
- **OpenAI** (paid, optional): [OpenAI Platform](https://platform.openai.com/api-keys)

## License

MIT
