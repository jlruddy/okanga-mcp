# Okanga Token-Optimized MCP Server

A custom Model Context Protocol (MCP) server designed specifically for iOS/Swift development with Claude, named **Okanga**.

Unlike standard file-system tools, this server is **token-aware**. It provides specialized tools to inspect Swift code structure, search projects server-side, and diagnose Xcode build issues without flooding the LLM's context window with massive files.

## Key Features

### 1.  Token Optimization Tools
Standard "read file" tools can burn 5,000+ tokens just to find a single function signature. This server introduces:
* **`read_swift_structure`**: Parses a Swift file and returns *only* class definitions, properties, and function signatures. Hides implementation bodies. **Reduces token usage by ~90%.**
* **`read_file_snippet`**: Read specific line ranges (e.g., lines 50-100) instead of the whole file.
* **`search_project`**: Runs `grep` locally on your machine. Finds usage examples without Claude having to open every file.
* **`check_file_size`**: Acts as a guardrail, warning Claude before it attempts to ingest massive files.

### 2. 🛠 Xcode Diagnostics
* **`analyze_xcode_project`**: specific understanding of `.xcodeproj` and `.xcworkspace` structures.
* **`read_build_settings`**: Extracts resolved build settings (debug/release) via `xcodebuild`.
* **`check_framework_search_paths`**: Validates that all search paths actually exist (fix "Library not found" errors).
* **`get_recent_build_logs`**: Fetches recent errors from `DerivedData` without needing Xcode open.

---

## Dependencies

* **OS**: macOS (Required for `xcodebuild` and `xcrun`)
* **Python**: 3.10 or higher
* **Xcode**: Installed with Command Line Tools active (`xcode-select --install`)
* **Python Packages**: `mcp` (managed automatically if using `uv`)

---

## Installation & Setup

We recommend using **`uv`** (a fast Python package manager) to run this server. It handles virtual environments automatically, ensuring the script always runs with the correct dependencies.

### Option 1: The `uv` Method (Recommended)
This is the easiest setup. It doesn't require manually creating virtual environments.

1.  **Install uv** (if you haven't):
    ```bash
    curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
    ```
2.  **Clone this repo**:
    ```bash
    git clone [https://github.com/yourusername/okanga-mcp-server.git](https://github.com/yourusername/okanga-mcp-server.git)
    cd okanga-mcp-server
    ```
3.  **Get the absolute path**:
    Run `pwd` in the terminal inside the folder. Copy this path.

### Option 2: The Standard `pip` Method
If you prefer managing your own environments:

1.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    # OR if using pyproject.toml
    pip install .
    ```

---

## Connecting to Claude

To use this with the Claude Desktop App, you need to edit your configuration file.

**Config Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following entry to the `mcpServers` object. 

### If using `uv` (Recommended):
*Replace `/ABSOLUTE/PATH/TO/REPO` with the path you copied earlier.*

```json
{
  "mcpServers": {
    "okanga-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "/ABSOLUTE/PATH/TO/REPO/okanga_server.py"
      ]
    }
  }
}
