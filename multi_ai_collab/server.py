"""
Multi-AI MCP Server
Enables Claude Code to query Gemini, Grok, and DeepSeek via MCP stdio transport.
"""

import json
import sys
import os
import urllib.request
from typing import Dict, Any
from pathlib import Path

from multi_ai_collab import __version__

KNOWN_PROVIDERS = {"gemini", "grok", "openai", "deepseek"}

CONFIG_DIR = Path(
    os.environ.get(
        "MULTI_AI_COLLAB_CONFIG",
        Path.home() / ".config" / "multi-ai-collab",
    )
)
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def load_credentials() -> dict:
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            f"credentials.json not found at {CREDENTIALS_FILE}. Run: multi-ai-collab --setup",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Failed to load {CREDENTIALS_FILE}: {e}", file=sys.stderr)
        sys.exit(1)


def init_clients(credentials: dict) -> dict:
    clients = {}

    if credentials.get("gemini", {}).get("enabled", False):
        try:
            import google.generativeai as genai

            genai.configure(api_key=credentials["gemini"]["api_key"])
            clients["gemini"] = {
                "client": genai.GenerativeModel(credentials["gemini"]["model"]),
                "type": "gemini",
            }
        except Exception as e:
            print(f"Warning: Gemini init failed: {e}", file=sys.stderr)

    if credentials.get("grok", {}).get("enabled", False) or credentials.get(
        "openai", {}
    ).get("enabled", False):
        try:
            from openai import OpenAI

            if credentials.get("grok", {}).get("enabled", False):
                clients["grok"] = {
                    "client": OpenAI(
                        api_key=credentials["grok"]["api_key"],
                        base_url=credentials["grok"]["base_url"],
                    ),
                    "model": credentials["grok"]["model"],
                    "type": "openai",
                }

            if credentials.get("openai", {}).get("enabled", False):
                clients["openai"] = {
                    "client": OpenAI(api_key=credentials["openai"]["api_key"]),
                    "model": credentials["openai"]["model"],
                    "type": "openai",
                }
        except Exception as e:
            print(f"Warning: OpenAI client init failed: {e}", file=sys.stderr)

    if credentials.get("deepseek", {}).get("enabled", False):
        try:
            from openai import OpenAI

            clients["deepseek"] = {
                "client": OpenAI(
                    api_key=credentials["deepseek"]["api_key"],
                    base_url=credentials["deepseek"]["base_url"],
                ),
                "model": credentials["deepseek"]["model"],
                "type": "openai",
            }
        except Exception as e:
            print(f"Warning: DeepSeek init failed: {e}", file=sys.stderr)

    return clients


def send_response(response: Dict[str, Any]):
    print(json.dumps(response), flush=True)


def call_ai(clients: dict, credentials: dict, ai_name: str, prompt: str,
            system_prompt: str = "", temperature: float = 0.7) -> str:
    if ai_name not in clients:
        return f"Error: {ai_name.upper()} is not available or not configured"

    try:
        client_info = clients[ai_name]
        client = client_info["client"]

        if client_info["type"] == "gemini":
            import google.generativeai as genai

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                ),
            )
            return response.text

        elif client_info["type"] == "openai":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=client_info["model"],
                messages=messages,
                temperature=temperature,
                max_tokens=8192,
            )
            return response.choices[0].message.content

    except Exception as e:
        return f"Error calling {ai_name.upper()}: {e}"


def call_grok_search(
    credentials: dict,
    query: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    allowed_domains: list = None,
    excluded_domains: list = None,
) -> str:
    try:
        api_key = credentials["grok"]["api_key"]
        base_url = credentials["grok"]["base_url"].rstrip("/")
        model = credentials["grok"]["model"]

        web_search_tool = {"type": "web_search"}
        if allowed_domains:
            web_search_tool["allowed_domains"] = allowed_domains[:5]
        elif excluded_domains:
            web_search_tool["excluded_domains"] = excluded_domains[:5]

        body = {
            "model": model,
            "input": [{"role": "user", "content": query}],
            "tools": [web_search_tool],
            "temperature": temperature,
        }

        if system_prompt:
            body["instructions"] = system_prompt

        req = urllib.request.Request(
            f"{base_url}/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        texts = []
        for item in result.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        texts.append(block["text"])
        return "\n\n".join(texts) if texts else "No response text returned"

    except Exception as e:
        return f"Error calling GROK search: {e}"


def handle_initialize(request_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "multi-ai-mcp", "version": __version__},
        },
    }


def handle_tools_list(request_id: Any, clients: dict) -> Dict[str, Any]:
    tools = [
        {
            "name": "server_status",
            "description": "Get server status and available AI models",
            "inputSchema": {"type": "object", "properties": {}},
        }
    ]

    for ai_name in clients.keys():
        schema = {
            "name": f"ask_{ai_name}",
            "description": f"Ask {ai_name.upper()} a question",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The question or prompt",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt to set the model's role or constraints",
                        "default": "",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for response (0.0-1.0)",
                        "default": 0.7,
                    },
                },
                "required": ["prompt"],
            },
        }

        if ai_name == "grok":
            schema["description"] = (
                "Ask GROK a question. Set web_search=true for real-time "
                "web access with citations via the xAI Responses API."
            )
            schema["inputSchema"]["properties"]["web_search"] = {
                "type": "boolean",
                "description": "Enable live web search. Uses the xAI Responses API for real-time results with citations.",
                "default": False,
            }
            schema["inputSchema"]["properties"]["allowed_domains"] = {
                "type": "array",
                "items": {"type": "string"},
                "description": "When web_search=true, restrict to these domains (max 5). Cannot combine with excluded_domains.",
                "default": [],
            }
            schema["inputSchema"]["properties"]["excluded_domains"] = {
                "type": "array",
                "items": {"type": "string"},
                "description": "When web_search=true, exclude these domains (max 5). Cannot combine with allowed_domains.",
                "default": [],
            }

        tools.append(schema)

    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}


def handle_tool_call(
    request_id: Any, params: Dict[str, Any], clients: dict, credentials: dict
) -> Dict[str, Any]:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        result = ""

        if tool_name == "server_status":
            available = list(clients.keys())
            enabled_count = len(
                [p for p in KNOWN_PROVIDERS if credentials.get(p, {}).get("enabled", False)]
            )
            result = f"Multi-AI MCP Server v{__version__}\n\n"
            result += f"Available AIs: {', '.join(ai.upper() for ai in available)}\n"
            result += f"Status: {len(available)}/{enabled_count} AIs ready\n\n"
            for ai_name, client_info in clients.items():
                model = client_info.get("model", credentials[ai_name]["model"])
                result += f"  {ai_name.upper()}: {model}\n"
            disabled = [
                p for p in KNOWN_PROVIDERS
                if not credentials.get(p, {}).get("enabled", False) or p not in clients
            ]
            if disabled:
                result += f"\nDisabled: {', '.join(p.upper() for p in disabled)}"

        elif tool_name.startswith("ask_"):
            ai_name = tool_name[4:]
            if ai_name not in clients:
                raise ValueError(f"Unknown tool: {tool_name}")

            prompt = arguments.get("prompt", "")
            system_prompt = arguments.get("system_prompt", "")
            temperature = arguments.get("temperature", 0.7)

            if ai_name == "grok" and arguments.get("web_search", False):
                allowed = arguments.get("allowed_domains") or None
                excluded = arguments.get("excluded_domains") or None
                result = call_grok_search(
                    credentials, prompt, system_prompt, temperature, allowed, excluded
                )
            else:
                result = call_ai(clients, credentials, ai_name, prompt, system_prompt, temperature)

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": result}]},
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)},
        }


def serve():
    sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 1)

    credentials = load_credentials()
    clients = init_clients(credentials)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})

            if request_id is None:
                continue

            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "tools/list":
                response = handle_tools_list(request_id, clients)
            elif method == "tools/call":
                response = handle_tool_call(request_id, params, clients, credentials)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            send_response(response)

        except json.JSONDecodeError:
            continue
        except EOFError:
            break
        except Exception as e:
            if "request_id" in locals() and request_id is not None:
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": f"Internal error: {e}"},
                    }
                )
