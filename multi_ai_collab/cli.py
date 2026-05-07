"""
CLI entry point for multi-ai-collab.

  multi-ai-collab           Run the MCP server (stdio transport)
  multi-ai-collab --setup   Interactive configuration wizard
  multi-ai-collab --status  Show configured providers
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from multi_ai_collab import __version__
from multi_ai_collab.server import CONFIG_DIR, CREDENTIALS_FILE

PROVIDERS = {
    "gemini": {
        "display": "Gemini",
        "key_url": "https://aistudio.google.com/apikey",
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro"],
        "billing": "Free tier (rate-limited)",
    },
    "grok": {
        "display": "Grok",
        "key_url": "https://console.x.ai/",
        "default_model": "grok-3",
        "models": ["grok-3", "grok-2"],
        "base_url": "https://api.x.ai/v1",
        "billing": "Per-token",
    },
    "openai": {
        "display": "OpenAI",
        "key_url": "https://platform.openai.com/api-keys",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "billing": "Per-token",
    },
    "deepseek": {
        "display": "DeepSeek",
        "key_url": "https://platform.deepseek.com/",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-coder"],
        "base_url": "https://api.deepseek.com",
        "billing": "Per-token",
    },
}


def load_existing_credentials() -> dict:
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def prompt_provider(name: str, info: dict, existing: dict) -> dict | None:
    current = existing.get(name, {})
    current_key = current.get("api_key", "")
    is_configured = current_key and not current_key.startswith("YOUR_")

    print(f"\n{'─' * 50}")
    print(f"  {info['display']}  ({info['billing']})")
    print(f"  API key: {info['key_url']}")

    if is_configured:
        masked = current_key[:8] + "..." + current_key[-4:]
        print(f"  Current key: {masked}")
        resp = input("  Keep existing? [Y/n]: ").strip().lower()
        if resp in ("", "y", "yes"):
            return current
        elif resp == "remove":
            return None

    key = input("  API key (Enter to skip): ").strip()
    if not key:
        print(f"  Skipped {info['display']}")
        return None

    print(f"\n  Models: {', '.join(info['models'])}")
    print(f"  Default: {info['default_model']}")
    model = input("  Model (Enter for default): ").strip()
    if not model:
        model = info["default_model"]

    entry = {
        "api_key": key,
        "model": model,
        "enabled": True,
    }
    if "base_url" in info:
        entry["base_url"] = info["base_url"]

    print(f"  ✓ {info['display']} configured with {model}")
    return entry


def register_with_claude():
    resp = input("\n  Register as MCP server in Claude Code? [Y/n]: ").strip().lower()
    if resp not in ("", "y", "yes"):
        print("  Skipped Claude Code registration.")
        print("  See README for manual MCP configuration instructions.")
        return False

    if not shutil.which("claude"):
        print("  Claude Code CLI not found — skipping MCP registration.")
        print("  After installing Claude Code, run:")
        print("    claude mcp add --scope user multi-ai-collab -- multi-ai-collab")
        return False

    print("  Registering with Claude Code...")
    try:
        subprocess.run(
            ["claude", "mcp", "remove", "multi-ai-collab"],
            capture_output=True,
        )
        result = subprocess.run(
            [
                "claude", "mcp", "add", "--scope", "user",
                "multi-ai-collab", "--",
                "multi-ai-collab",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  ✓ Registered as MCP server in Claude Code")
            return True
        else:
            print(f"  Registration failed: {result.stderr.strip()}")
            print("  Manual registration:")
            print("    claude mcp add --scope user multi-ai-collab -- multi-ai-collab")
            return False
    except Exception as e:
        print(f"  Registration error: {e}")
        return False


def run_setup():
    print(f"multi-ai-collab v{__version__} — Setup")
    print("=" * 50)
    print("Configure which AI providers to enable.")
    print("You only need API keys for the ones you want to use.")

    existing = load_existing_credentials()
    credentials = {}
    configured = []

    for name, info in PROVIDERS.items():
        result = prompt_provider(name, info, existing)
        if result:
            credentials[name] = result
            configured.append(info["display"])
        else:
            credentials[name] = {
                "api_key": "",
                "model": info["default_model"],
                "enabled": False,
            }
            if "base_url" in info:
                credentials[name]["base_url"] = info["base_url"]

    if not configured:
        print("\nNo providers configured. Run --setup again with at least one API key.")
        sys.exit(1)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)
    print(f"\n  ✓ Credentials saved to {CREDENTIALS_FILE}")

    register_with_claude()

    print(f"\n{'=' * 50}")
    print(f"  Ready — {len(configured)} provider(s): {', '.join(configured)}")
    print()
    print("  Available tools:")
    print("    server_status")
    for name in PROVIDERS:
        if credentials[name].get("enabled"):
            extra = " (supports web_search=true)" if name == "grok" else ""
            print(f"    ask_{name}{extra}")
    print()
    print("  If you skipped Claude Code registration, configure your MCP client")
    print("  to run: multi-ai-collab (stdio transport)")
    print()


def run_status():
    print(f"multi-ai-collab v{__version__}")

    if not CREDENTIALS_FILE.exists():
        print(f"\nNo credentials found at {CREDENTIALS_FILE}")
        print("Run: multi-ai-collab --setup")
        return

    try:
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
    except Exception as e:
        print(f"\nFailed to read credentials: {e}")
        return

    print(f"Config: {CREDENTIALS_FILE}\n")

    for name, info in PROVIDERS.items():
        entry = creds.get(name, {})
        enabled = entry.get("enabled", False)
        model = entry.get("model", "—")
        key = entry.get("api_key", "")

        if enabled and key and not key.startswith("YOUR_"):
            masked = key[:8] + "..." + key[-4:]
            print(f"  ✓ {info['display']:12s}  model={model}  key={masked}")
        else:
            print(f"  ✗ {info['display']:12s}  (disabled)")


def main():
    parser = argparse.ArgumentParser(
        prog="multi-ai-collab",
        description="MCP server giving any MCP-compatible agent access to multiple AI providers",
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Interactive configuration wizard",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show configured providers",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"multi-ai-collab {__version__}",
    )

    args = parser.parse_args()

    if args.setup:
        run_setup()
    elif args.status:
        run_status()
    else:
        from multi_ai_collab.server import serve
        serve()
