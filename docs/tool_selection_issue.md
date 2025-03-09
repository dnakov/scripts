# Tool Selection Inconsistency: AgentTool vs GlobTool

## Issue Summary

There is a design inconsistency between:
1. How the system prompt directs the model to use tools 
2. How the tools are defined
3. How the test suite evaluates tool selection

## Problem Details

In the test case `test_agent_tool`, the system prompt instructs the model to "prefer the Agent tool" for file searches:

```
# Tool usage policy
- When doing file search, prefer to use the Agent tool in order to reduce context usage.
```

However, the model selects `GlobTool` instead of `AgentTool` when asked to "Find all JavaScript files in the project". This appears to be a rational choice because:

1. `GlobTool` is explicitly described for finding files by name pattern (e.g., "*.js")
2. `AgentTool` is described for more complex, multi-step searches
3. The task of finding all JavaScript files is a direct file pattern search (better matched by GlobTool's description)

## Conflicting Instructions in Original Implementation

This issue is present in the original implementation (`qwq-tool-calling-test.py`), which contains these directly conflicting instructions:

### System Prompt (line 95-96)
```
# Tool usage policy
- When doing file search, prefer to use the Agent tool in order to reduce context usage.
```

### GlobTool Description (lines 142-148)
```
"description": "\n- Fast file search tool that works with any codebase size\n- Finds files by name pattern using glob syntax\n- Supports full glob syntax (eg. \"*.js\", \"**/*.{ts,tsx}\", \"src/**/*.test.js\")\n- Exclude files with the exclude parameter (eg. \"node_modules/**\")\n- Returns matching file paths sorted by modification time\n- Use this tool when you need to find files by name pattern\n- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n",
```

### AgentTool Description (lines 187-191)
```
"description": "Launch a new agent that has access to various tools. When you are searching for a keyword or file and are not confident that you will find the right match on the first try, use the Agent tool to perform the search for you. For example:\n\n- If you are searching for a keyword like \"config\" or \"logger\", the Agent tool is appropriate\n- If you want to read a specific file path, use the FileReadTool or GlobTool tool instead of the Agent tool, to find the match more quickly\n- If you are searching for a specific class definition like \"class Foo\", use the GlobTool tool instead, to find the match more quickly\n\n
```

The AgentTool's own description explicitly directs the model to use GlobTool for finding specific files or class definitions, which directly contradicts the system prompt's instruction to prefer AgentTool for file searches.

## Test Accommodation

The test suite allows flexibility in tool selection by defining certain tools as functionally equivalent:

```python
equivalent_tools = {
    "AgentTool": ["GlobTool", "SearchTool"],
    "GlobTool": ["FindTool", "AgentTool"],
    # Other equivalences...
}
```

This means the test will pass if either tool is chosen, allowing for flexibility in model decisions.

## Implications

1. **Correctness**: The model selects the most appropriate tool based on the specific task, which is technically correct.
2. **System Prompt Compliance**: The model does not strictly follow the system prompt's instruction to prefer AgentTool for file searches.
3. **Functionality**: In our test environment, GlobTool actually returns more useful, targeted output for this task than AgentTool would.

## Recommendations

1. **Clarify Tool Descriptions**: Specify more precisely when AgentTool should be used over GlobTool (or vice versa).
2. **Adjust System Prompt**: Make the guidance on tool selection consistent with the tool descriptions.
3. **Keep Test Flexibility**: The current test flexibility is useful for handling variations in model behavior.

This issue was present in the original implementation and has been carried over to the updated version. It represents a fundamental tension between specific tool-selection guidance and allowing the model to make contextually appropriate decisions. 