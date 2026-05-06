#!/bin/bash
# Multi-AI MCP Server Setup Script

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Multi-AI MCP Server Setup${NC}"
echo "Connect Claude Code with Gemini, Grok-3, ChatGPT, and DeepSeek!"
echo ""

# Check requirements
echo "📋 Checking requirements..."
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is required but not installed.${NC}"
    echo "Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✅ uv $(uv --version | awk '{print $2}') found"

if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude Code CLI not found. Please install it first:${NC}"
    echo "npm install -g @anthropic-ai/claude-code"
    exit 1
fi
echo "✅ Claude Code CLI found"

# Create directory
echo ""
echo "📁 Creating MCP server directory..."
mkdir -p ~/.claude-mcp-servers/multi-ai-collab

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy server files
echo "📋 Installing server..."
cp "$SCRIPT_DIR/server.py" ~/.claude-mcp-servers/multi-ai-collab/

# Create credentials.json from template if it doesn't exist
if [ ! -f ~/.claude-mcp-servers/multi-ai-collab/credentials.json ]; then
    cp "$SCRIPT_DIR/credentials.template.json" ~/.claude-mcp-servers/multi-ai-collab/credentials.json
    echo "📄 Created credentials.json from template"
fi

# Create venv and install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
uv venv ~/.claude-mcp-servers/multi-ai-collab/.venv --quiet
uv pip install -r "$SCRIPT_DIR/requirements.txt" -p ~/.claude-mcp-servers/multi-ai-collab/.venv --quiet

# Function to prompt for API key and model
prompt_for_ai() {
    local service_name="$1"
    local current_key="$2"
    local description="$3"
    local default_model="$4"
    local available_models="$5"
    local is_optional="${6:-true}"
    
    if [[ "$current_key" == *"YOUR_"*"_KEY_HERE" ]]; then
        echo ""
        echo -e "${YELLOW}🔑 $service_name Configuration${NC}"
        echo "   $description"
        if [ "$is_optional" = "true" ]; then
            echo -e "   ${BLUE}(Optional - press Enter to skip)${NC}"
        fi
        read -p "Enter $service_name API key: " new_key
        if [ ! -z "$new_key" ]; then
            # Ask for model preference
            echo ""
            echo -e "${BLUE}📱 Choose $service_name model:${NC}"
            echo "   Available: $available_models"
            echo "   Default: $default_model"
            read -p "Model (or press Enter for default): " model_choice
            if [ -z "$model_choice" ]; then
                model_choice="$default_model"
            fi
            
            # Update credentials.json with new key and model
            local service_lower
            service_lower="$(echo "$service_name" | tr '[:upper:]' '[:lower:]')"
            python3 - "$HOME/.claude-mcp-servers/multi-ai-collab/credentials.json" "$service_lower" "$new_key" "$model_choice" <<'PYEOF'
import json, sys
creds_path, service, api_key, model = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(creds_path, 'r') as f:
    creds = json.load(f)
creds[service]['api_key'] = api_key
creds[service]['model'] = model
creds[service]['enabled'] = True
with open(creds_path, 'w') as f:
    json.dump(creds, f, indent=2)
PYEOF
            echo -e "${GREEN}✅ $service_name configured with model: $model_choice${NC}"
            return 0
        else
            echo -e "${YELLOW}⏭️  $service_name skipped (can be added later)${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ $service_name already configured${NC}"
        return 0
    fi
}

# Configure API keys
echo ""
echo "🔧 Configuring API keys..."
echo "You can skip any AI you don't have an API key for - the server will work with whatever you configure!"

# Read current credentials
GEMINI_KEY=$(python3 -c "import json; f=open('$HOME/.claude-mcp-servers/multi-ai-collab/credentials.json'); print(json.load(f)['gemini']['api_key'])")
GROK_KEY=$(python3 -c "import json; f=open('$HOME/.claude-mcp-servers/multi-ai-collab/credentials.json'); print(json.load(f)['grok']['api_key'])")
OPENAI_KEY=$(python3 -c "import json; f=open('$HOME/.claude-mcp-servers/multi-ai-collab/credentials.json'); print(json.load(f)['openai']['api_key'])")
DEEPSEEK_KEY=$(python3 -c "import json; f=open('$HOME/.claude-mcp-servers/multi-ai-collab/credentials.json'); print(json.load(f)['deepseek']['api_key'])")

# Track configured AIs
configured_ais=()

# Prompt for API keys and models
echo -e "${BLUE}📝 Configure the AIs you want to use:${NC}"

if prompt_for_ai "Gemini" "$GEMINI_KEY" "Free API key from: https://aistudio.google.com/apikey" "gemini-2.0-flash" "gemini-2.0-flash, gemini-2.0-flash-exp, gemini-1.5-pro"; then
    configured_ais+=("Gemini")
fi

if prompt_for_ai "Grok" "$GROK_KEY" "API key from: https://console.x.ai/" "grok-3" "grok-3, grok-2"; then
    configured_ais+=("Grok-3")
fi

if prompt_for_ai "OpenAI" "$OPENAI_KEY" "API key from: https://platform.openai.com/api-keys" "gpt-4o" "gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo"; then
    configured_ais+=("ChatGPT")
fi

if prompt_for_ai "DeepSeek" "$DEEPSEEK_KEY" "API key from: https://platform.deepseek.com/" "deepseek-chat" "deepseek-chat, deepseek-coder"; then
    configured_ais+=("DeepSeek")
fi

# Show summary
echo ""
if [ ${#configured_ais[@]} -eq 0 ]; then
    echo -e "${RED}❌ No AIs configured. Please run setup again with at least one API key.${NC}"
    exit 1
else
    echo -e "${GREEN}🎉 Configured AIs: ${configured_ais[*]}${NC}"
    echo -e "${BLUE}💡 You can add more API keys later by editing: ~/.claude-mcp-servers/multi-ai-collab/credentials.json${NC}"
fi

echo ""
echo "🔧 Configuring Claude Code..."
# Remove any existing MCP configuration
claude mcp remove multi-ai-collab 2>/dev/null || true

# Add MCP server with global scope (using venv Python)
claude mcp add --scope user multi-ai-collab ~/.claude-mcp-servers/multi-ai-collab/.venv/bin/python3 ~/.claude-mcp-servers/multi-ai-collab/server.py

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "🎉 Multi-AI MCP Server is ready!"
echo ""
echo "Your configured AIs:"
for ai in "${configured_ais[@]}"; do
    case $ai in
        "Gemini") echo "  • 🧠 Gemini (Google)" ;;
        "Grok-3") echo "  • 🚀 Grok-3 (xAI)" ;;
        "ChatGPT") echo "  • 💬 ChatGPT (OpenAI)" ;;
    esac
done

if [ ${#configured_ais[@]} -gt 1 ]; then
    echo ""
    echo "🤝 Multi-AI features available:"
    echo "  • Ask all AIs the same question"
    echo "  • Have AIs debate topics"
    echo "  • Compare different AI perspectives"
fi
echo ""
echo "Try it out:"
echo "  1. Run: claude"
echo "  2. Type: /mcp (should show multi-ai-collab connected)"
echo "  3. Use: mcp__multi-ai-collab__ask_gemini"
echo "         prompt: \"Hello from Claude!\""
echo ""
echo "Collaborative tools:"
echo "  • mcp__multi-ai-collab__ask_all_ais - Ask all AIs the same question"
echo "  • mcp__multi-ai-collab__ai_debate - Have two AIs debate a topic"
echo "  • mcp__multi-ai-collab__server_status - Check which AIs are available"
echo ""
echo "Individual AI tools:"
echo "  • mcp__multi-ai-collab__ask_[ai_name]"
echo "  • mcp__multi-ai-collab__[ai_name]_code_review"
echo ""
echo "🔧 To add more API keys later, edit:"
echo "   ~/.claude-mcp-servers/multi-ai-collab/credentials.json"
echo ""
echo "Enjoy the AI collaboration! 🚀"