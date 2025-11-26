# Claude Instructions

## Token Efficiency Strategy (Okanga MCP)
When exploring Swift code, you MUST prioritize token efficiency:
1.  **Search First**: Use `search_project` to locate class/function definitions. Do not guess paths.
2.  **Structure Over Content**: Use `read_swift_structure` to see the API surface/outline of a file.
3.  **Snippets Only**: Only use `read_file_snippet` to inspect specific function implementations.
4.  **Avoid Full Reads**: Do not read entire files unless absolutely necessary for a refactor.

## Architecture
- Use SwiftUI for all new Views.
- ViewModels must be `ObservableObject` or use the `@Observable` macro.