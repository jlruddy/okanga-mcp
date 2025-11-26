How to Use (Prompting Strategy)
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

Troubleshooting
"Executable not found" Ensure you provided the absolute path in the JSON config. (~) expansion
often does not work in JSON config files. Use /Users/yourname/...

Library not found" errors in Xcode analysis Make sure you have run pod install (if using CocoaPods) 
before asking Claude to analyze the project.

Grep returning too many results The search_project tool is configured to ignore .git, Pods, 
and DerivedData automatically. If you have other large folders (like assets), 
you may need to modify the exclusion list in okanga_server.py
