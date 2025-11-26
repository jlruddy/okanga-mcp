# Okanga-MCP - Token-Optimizing MCP Server

A custom Model Context Protocol (MCP) server designed specifically for iOS/Swift development with Claude.

Unlike standard file-system tools, this server is token-aware. It provides specialized tools to inspect Swift code structure, search projects server-side, and diagnose Xcode build issues without flooding the LLM's context window with massive files.

🚀 Key Features

1. 🧠 Token Optimization Tools

Standard "read file" tools can burn 5,000+ tokens just to find a single function signature. This server introduces:

read_swift_structure: Parses a Swift file and returns only class definitions, properties, and function signatures. Hides implementation bodies. Reduces token usage by ~90%.

read_file_snippet: Read specific line ranges (e.g., lines 50-100) instead of the whole file.

search_project: Runs grep locally on your machine. Finds usage examples without Claude having to open every file.

check_file_size: Acts as a guardrail, warning Claude before it attempts to ingest massive files.

2. 🛠 Xcode Diagnostics

analyze_xcode_project: specific understanding of .xcodeproj and .xcworkspace structures.

read_build_settings: Extracts resolved build settings (debug/release) via xcodebuild.

check_framework_search_paths: Validates that all search paths actually exist (fix "Library not found" errors).

get_recent_build_logs: Fetches recent errors from DerivedData without needing Xcode open.

📦 Dependencies

OS: macOS (Required for xcodebuild and xcrun)

Python: 3.10 or higher

Xcode: Installed with Command Line Tools active (xcode-select --install)

Python Packages: mcp (managed automatically if using uv)

⚡️ Installation & Setup

We recommend using uv (a fast Python package manager) to run this server. It handles virtual environments automatically, ensuring the script always runs with the correct dependencies.

Option 1: The uv Method (Recommended)

This is the easiest setup. It doesn't require manually creating virtual environments.

Install uv (if you haven't):

curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh


Clone this repo:

git clone [https://github.com/yourusername/xcode-mcp-server.git](https://github.com/yourusername/xcode-mcp-server.git)
cd xcode-mcp-server


Get the absolute path:
Run pwd in the terminal inside the folder. Copy this path.

Option 2: The Standard pip Method

If you prefer managing your own environments:

Create a virtual environment:

python3 -m venv venv
source venv/bin/activate


Install dependencies:

pip install -r requirements.txt
# OR if using pyproject.toml
pip install .


🔌 Connecting to Claude

To use this with the Claude Desktop App, you need to edit your configuration file.

Config Location: ~/Library/Application Support/Claude/claude_desktop_config.json

Add the following entry to the mcpServers object.

If using uv (Recommended):

Replace /ABSOLUTE/PATH/TO/REPO with the path you copied earlier.

{
  "mcpServers": {
    "xcode-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "/ABSOLUTE/PATH/TO/REPO/xcode_server.py"
      ]
    }
  }
}


If using standard python (venv):

You must point to the python executable inside your venv.

{
  "mcpServers": {
    "xcode-mcp": {
      "command": "/ABSOLUTE/PATH/TO/REPO/venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/REPO/xcode_server.py"
      ]
    }
  }
}


💡 How to Use (Prompting Strategy)

To get the most out of the token optimization, explicitly instruct Claude on how to use these tools.

Add this to your CLAUDE.md or System Prompt:

"When exploring Swift code, ALWAYS prioritize token efficiency:

Use search_project to find where classes/functions are defined.

Use read_swift_structure to understand the API surface of a file.

Only use read_file_snippet to inspect specific function implementations.

Do not read entire files unless absolutely necessary for a refactor."

Example Conversation Flow

You: "Why is my UserProfileView not updating?"

Claude (using this server):

Calls search_project("UserProfileView", ...) -> Finds it in Views/UserProfileView.swift.

Calls read_swift_structure("Views/UserProfileView.swift") -> Sees the body var and a refresh() function, but no code inside them.

Calls read_file_snippet("Views/UserProfileView.swift", 45, 60) -> Reads just the refresh() function logic.

Result: Claude finds the bug using 300 tokens instead of 4,000.

🛡 Troubleshooting

"Executable not found"
Ensure you provided the absolute path in the JSON config. ~ (tilde) expansion often does not work in JSON config files. Use /Users/yourname/....

"Library not found" errors in Xcode analysis
Make sure you have run pod install (if using CocoaPods) before asking Claude to analyze the project.

Grep returning too many results
The search_project tool is configured to ignore .git, Pods, and DerivedData automatically. If you have other large folders (like assets), you may need to modify the exclusion list in xcode_server.py.
