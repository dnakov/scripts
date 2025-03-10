from openai import OpenAI
import json
import os
import unittest
import re
import logging

# Set up logging
logger = logging.getLogger('tool_calling_tests')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('tool_calling_tests.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="test")

# Mock implementations of tool functions
def execute_bash_command(arguments):
    command = arguments["command"]
    if not command:
        return "Error: Empty command"
    if command == "xyz123":
        return "Error: command not found: xyz123"
    if command == "ls -l":
        return "Executed command: ls -l\nOutput: -rw-r--r-- 1 user 123 file1.txt\n-rw-r--r-- 1 user 456 file2.txt\n-rw-r--r-- 1 user 789 directory1/\ndrwxr-xr-x 1 user 123 directory2/"
    if "ls" in command:
        return "Executed command: ls\nOutput: file1.txt file2.txt directory1/ directory2/"
    if "grep" in command:
        return "Executed command: grep\nOutput: 3 matches found in 2 files"
    return f"Executed command: {command}\nOutput: Command executed successfully"

def read_file(arguments):
    file_path = arguments["file_path"]
    if "test_file.txt" in file_path:
        return f"Content of {file_path}:\nThis is mock content for testing purposes."
    if "README" in file_path:
        return """Content of README.md:
# Project Name

This is a mock README file for the project.

## Description
This project is a JavaScript-based web application framework.

## Features
- Feature 1
- Feature 2
- Feature 3"""
    elif "package.json" in file_path:
        return """Content of package.json:
{
  "name": "project-name",
  "version": "1.0.0",
  "description": "A JavaScript-based web application framework",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "jest"
  }
}"""
    return f"Content of {file_path}:\nThis is mock content for testing purposes."

def write_file(arguments):
    file_path = arguments["file_path"]
    content = arguments["content"]
    return f"Successfully wrote to file: {file_path}"

def edit_file(arguments):
    file_path = arguments["file_path"]
    old_string = arguments["old_string"]
    new_string = arguments["new_string"]
    if not old_string and not file_path.endswith(".txt"):
        return f"Successfully created file: {file_path}"
    if old_string and "not_found" in old_string:
        return f"Error: old_string not found in {file_path}"
    return f"Successfully edited file: {file_path}"

def grep_search(arguments):
    pattern = arguments["pattern"]
    path = arguments.get("path", os.getcwd())
    if "pattern" in pattern:
        return f"Search results for pattern '{pattern}':\n/path/to/file1.txt:10: match found\n/path/to/file2.txt:25: another match found"
    return f"No matches found for pattern '{pattern}'"

def glob_search(arguments):
    pattern = arguments["pattern"]
    path = arguments.get("path", os.getcwd())
    if "README*" in pattern:
        return f"Files matching pattern '{pattern}':\n{path}/README.md"
    elif "package.json" in pattern:
        return f"Files matching pattern '{pattern}':\n{path}/package.json"
    elif ".js" in pattern or ".ts" in pattern:
        return f"Files matching pattern '{pattern}':\n{path}/src/index.js\n{path}/src/components/App.js\n{path}/src/utils/helpers.js"
    return f"Files matching pattern '{pattern}':\n{path}/file1.txt\n{path}/file2.txt\n{path}/directory/file3.txt"

def list_directory(arguments):
    path = arguments["path"]
    return f"Directory listing for '{path}':\n├── README.md\n├── package.json\n├── src/\n│   ├── index.js\n│   ├── components/\n│   └── utils/\n└── public/"

def agent_search(arguments):
    prompt = arguments["prompt"]
    return f"Agent response for prompt '{prompt}':\nI've analyzed the codebase and found relevant information based on your query."

def architect_analyze(arguments):
    prompt = arguments["prompt"]
    return f"Architecture analysis for '{prompt}':\n1. Component structure\n2. Implementation steps\n3. Technical considerations"

tool_implementations = {
    "BashTool": execute_bash_command,
    "FileReadTool": read_file,
    "FileWriteTool": write_file,
    "FileEditTool": edit_file,
    "GrepTool": grep_search,
    "GlobTool": glob_search,
    "LSTool": list_directory,
    "AgentTool": agent_search,
    "ArchitectTool": architect_analyze
}

tools = [
    {
        "name": "BashTool",
        "schema": {
            "description": "Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.\n\nBefore executing the command, please follow these steps:\n\n1. Directory Verification:\n   - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location\n   - For example, before running \"mkdir foo/bar\", first use LS to check that \"foo\" exists and is the intended parent directory\n\n2. Security Check:\n   - For security and to limit the threat of a prompt injection attack, some commands are limited or banned. If you use a disallowed command, you will receive an error message explaining the restriction. Explain the error to the User.\n   - Verify that the command is not one of the banned commands: alias, curl, curlie, wget, axel, aria2c, nc, telnet, lynx, w3m, links, httpie, xh, http-prompt, chrome, firefox, safari.\n\n3. Command Execution:\n   - After ensuring proper quoting, execute the command.\n   - Capture the output of the command.\n\n4. Output Processing:\n   - If the output exceeds 30000 characters, output will be truncated before being returned to you.\n   - Prepare the output for display to the user.\n\n5. Return Result:\n   - Provide the processed output of the command.\n   - If any errors occurred during execution, include those in the output.\n\nUsage notes:\n  - The command argument is required.\n  - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 30 minutes.\n  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use GrepTool, GlobTool, or AgentTool to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use FileReadTool and LSTool to read files.\n  - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).\n  - IMPORTANT: All commands share the same shell session. Shell state (environment variables, virtual environments, current directory, etc.) persist between commands. For example, if you set an environment variable as part of a command, the environment variable will persist for subsequent commands.\n  - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.\n  <good-example>\n  pytest /foo/bar/tests\n  </good-example>\n  <bad-example>\n  cd /foo/bar && pytest tests\n  </bad-example>\n\n# Committing changes with git\n\nWhen the user asks you to create a new git commit, follow these steps carefully:\n\n1. Start with a single message that contains exactly three tool_use blocks that do the following (it is VERY IMPORTANT that you send these tool_use blocks in a single message, otherwise it will feel slow to the user!):\n   - Run a git status command to see all untracked files.\n   - Run a git diff command to see both staged and unstaged changes that will be committed.\n   - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.\n\n2. Use the git context at the start of this conversation to determine which files are relevant to your commit. Add relevant untracked files to the staging area. Do not commit files that were already modified at the start of this conversation, if they are not relevant to your commit.\n\n3. Analyze all staged changes (both previously staged and newly added) and draft a commit message. Wrap your analysis process in <commit_analysis> tags:\n\n<commit_analysis>\n- List the files that have been changed or added\n- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)\n- Brainstorm the purpose or motivation behind these changes\n- Do not use tools to explore code, beyond what is available in the git context\n- Assess the impact of these changes on the overall project\n- Check for any sensitive information that shouldn't be committed\n- Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"\n- Ensure your language is clear, concise, and to the point\n- Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)\n- Ensure the message is not generic (avoid words like \"Update\" or \"Fix\" without context)\n- Review the draft message to ensure it accurately reflects the changes and their purpose\n</commit_analysis>\n\n4. Create the commit with a message ending with:\n🤖 Generated with Claude Agent\nCo-Authored-By: Claude <noreply@anthropic.com>\n\n- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:\n<example>\ngit commit -m \"$(cat <<'EOF'\n   Commit message here.\n\n   🤖 Generated with Claude Agent\n   Co-Authored-By: Claude <noreply@anthropic.com>\n   EOF\n   )\"\n</example>\n\n5. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.\n\n6. Finally, run git status to make sure the commit succeeded.\n\nImportant notes:\n- When possible, combine the \"git add\" and \"git commit\" commands into a single \"git commit -am\" command, to speed things up\n- However, be careful not to stage files (e.g. with `git add .`) for commits that aren't part of the change, they may have untracked files they want to keep around, but not commit.\n- NEVER update the git config\n- DO NOT push to the remote repository\n- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.\n- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit\n- Ensure your commit message is meaningful and concise. It should explain the purpose of the changes, not just describe them.\n- Return an empty response - the user will see the git output directly\n\n# Creating pull requests\nUse the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.\n\nIMPORTANT: When the user asks you to create a pull request, follow these steps carefully:\n\n1. Understand the current state of the branch. Remember to send a single message that contains multiple tool_use blocks (it is VERY IMPORTANT that you do this in a single message, otherwise it will feel slow to the user!):\n   - Run a git status command to see all untracked files.\n   - Run a git diff command to see both staged and unstaged changes that will be committed.\n   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote\n   - Run a git log command and `git diff main...HEAD` to understand the full commit history for the current branch (from the time it diverged from the `main` branch.)\n\n2. Create new branch if needed\n\n3. Commit changes if needed\n\n4. Push to remote with -u flag if needed\n\n5. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (not just the latest commit, but all commits that will be included in the pull request!), and draft a pull request summary. Wrap your analysis process in <pr_analysis> tags:\n\n<pr_analysis>\n- List the commits since diverging from the main branch\n- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)\n- Brainstorm the purpose or motivation behind these changes\n- Assess the impact of these changes on the overall project\n- Do not use tools to explore code, beyond what is available in the git context\n- Check for any sensitive information that shouldn't be committed\n- Draft a concise (1-2 bullet points) pull request summary that focuses on the \"why\" rather than the \"what\"\n- Ensure the summary accurately reflects all changes since diverging from the main branch\n- Ensure your language is clear, concise, and to the point\n- Ensure the summary accurately reflects the changes and their purpose (ie. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)\n- Ensure the summary is not generic (avoid words like \"Update\" or \"Fix\" without context)\n- Review the draft summary to ensure it accurately reflects the changes and their purpose\n</pr_analysis>\n\n6. Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.\n<example>\ngh pr create --title \"the pr title\" --body \"$(cat <<'EOF'\n## Summary\n<1-3 bullet points>\n\n## Test plan\n[Checklist of TODOs for testing the pull request...]\n\n🤖 Generated with Claude Agent\nEOF\n)\"\n</example>\n\nImportant:\n- Return an empty response - the user will see the gh output directly\n- Never update git config",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to run"},
                    "timeout": {"type": "number", "description": "Optional timeout in milliseconds (max 600000)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "name": "FileReadTool",
        "schema": {
            "description": "Reads a file from the local filesystem. The file_path parameter must be an absolute path, not a relative path. By default, it reads up to 2000 lines starting from the beginning of the file. You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters. Any lines longer than 2000 characters will be truncated. For image files, the tool will display the image for you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the file to read"},
                    "offset": {"type": "number", "description": "The line number to start reading from (1-indexed). Only provide if the file is too large to read at once"},
                    "limit": {"type": "number", "description": "The number of lines to read. Only provide if the file is too large to read at once"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "name": "FileWriteTool",
        "schema": {
            "description": "Write a file to the local filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the file to write (must be absolute, not relative)"},
                    "content": {"type": "string", "description": "The content to write to the file"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "name": "FileEditTool",
        "schema": {
            "description": "This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool with the 'mv' command instead. For larger edits, use the Write tool to overwrite files. For Jupyter notebooks (.ipynb files), use the NotebookEditTool instead.\n\nBefore using this tool:\n\n1. Use the View tool to understand the file's contents and context\n\n2. Verify the directory path is correct (only applicable when creating new files):\n   - Use the LS tool to verify the parent directory exists and is the correct location\n\nTo make a file edit, provide the following:\n1. file_path: The absolute path to the file to modify (must be absolute, not relative)\n2. old_string: The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)\n3. new_string: The edited text to replace the old_string\n\nThe tool will replace ONE occurrence of old_string with new_string in the specified file.\n\nCRITICAL REQUIREMENTS FOR USING THIS TOOL:\n\n1. UNIQUENESS: The old_string MUST uniquely identify the specific instance you want to change. This means:\n   - Include AT LEAST 3-5 lines of context BEFORE the change point\n   - Include AT LEAST 3-5 lines of context AFTER the change point\n   - Include all whitespace, indentation, and surrounding code exactly as it appears in the file\n\n2. SINGLE INSTANCE: This tool can only change ONE instance at a time. If you need to change multiple instances:\n   - Make separate calls to this tool for each instance\n   - Each call must uniquely identify its specific instance using extensive context\n\n3. VERIFICATION: Before using this tool:\n   - Check how many instances of the target text exist in the file\n   - If multiple instances exist, gather enough context to uniquely identify each one\n   - Plan separate tool calls for each instance\n\nWARNING: If you do not follow these requirements:\n   - The tool will fail if old_string matches multiple locations\n   - The tool will fail if old_string doesn't match exactly (including whitespace)\n   - You may change the wrong instance if you don't include enough context\n\nWhen making edits:\n   - Ensure the edit results in idiomatic, correct code\n   - Do not leave the code in a broken state\n   - Always use absolute file paths (starting with /)\n\nIf you want to create a new file, use:\n   - A new file path, including dir name if needed\n   - An empty old_string\n   - The new file's contents as new_string\n\nRemember: when making multiple file edits in a row to the same file, you should prefer to send all edits in a single message with multiple calls to this tool, rather than multiple messages with a single call each.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the file to modify"},
                    "old_string": {"type": "string", "description": "The text to replace"},
                    "new_string": {"type": "string", "description": "The text to replace it with"}
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },
    {
        "name": "GrepTool",
        "schema": {
            "description": "\n- Fast content search tool that works with any codebase size\n- Searches file contents using regular expressions\n- Supports full regex syntax (eg. \"log.*Error\", \"function\\s+\\w+\", etc.)\n- Filter files by pattern with the include parameter (eg. \"*.js\", \"*.{ts,tsx}\")\n- Returns matching file paths sorted by modification time\n- Use this tool when you need to find files containing specific patterns\n- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "The regular expression pattern to search for in file contents"},
                    "path": {"type": "string", "description": "The directory to search in. Defaults to the current working directory."},
                    "include": {"type": "string", "description": "File pattern to include in the search (e.g. \"*.js\", \"*.{ts,tsx}\")"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "name": "GlobTool",
        "schema": {
            "description": "\n- Fast file search tool that works with any codebase size\n- Finds files by name pattern using glob syntax\n- Supports full glob syntax (eg. \"*.js\", \"**/*.{ts,tsx}\", \"src/**/*.test.js\")\n- Exclude files with the exclude parameter (eg. \"node_modules/**\")\n- Returns matching file paths sorted by modification time\n- Use this tool when you need to find files by name pattern\n- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "The glob pattern to search for files (e.g. \"*.js\", \"**/*.{ts,tsx}\")"},
                    "path": {"type": "string", "description": "The directory to search in. Defaults to the current working directory."},
                    "exclude": {"type": "string", "description": "Glob pattern to exclude from the search (e.g. \"node_modules/**\")"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "name": "LSTool",
        "schema": {
            "description": "Lists files and directories in the specified path. Provides a tree-like view of the directory structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the directory to list (must be absolute, not relative)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "name": "AgentTool",
        "schema": {
            "description": "Launch a new agent that has access to various tools. When you are searching for a keyword or file and are not confident that you will find the right match on the first try, use the Agent tool to perform the search for you. For example:\n\n- If you are searching for a keyword like \"config\" or \"logger\", the Agent tool is appropriate\n- If you want to read a specific file path, use the FileReadTool or GlobTool tool instead of the Agent tool, to find the match more quickly\n- If you are searching for a specific class definition like \"class Foo\", use the GlobTool tool instead, to find the match more quickly\n\nUsage notes:\n1. Launch multiple agents concurrently whenever possible, to maximize performance\n2. When the agent is done, it will return a single message back to you\n3. Each agent invocation is stateless\n4. The agent's outputs should generally be trusted",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The task for the agent to perform"}
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "name": "ArchitectTool",
        "schema": {
            "description": "Your go-to tool for any technical or coding task. Analyzes requirements and breaks them down into clear, actionable implementation steps. Use this whenever you need help planning how to implement a feature, solve a technical problem, or structure your code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The technical request or coding task to analyze"},
                    "context": {"type": "string", "description": "Optional context from previous conversation or system state"}
                },
                "required": ["prompt"]
            }
        }
    }
]

def run_conversation_with_tools(initial_messages, max_turns=5):
    current_messages = initial_messages.copy()
    turn = 1
    tools_for_api = [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["schema"]["description"],
                "parameters": tool["schema"]["parameters"]
            }
        } for tool in tools
    ]

    while turn <= max_turns:
        try:
            completion = client.chat.completions.create(
                model="qwq-32b",
                messages=current_messages,
                tools=tools_for_api,
                temperature=0.6,
                max_tokens=1024,
            )
        except Exception as e:
            print(f"API Error: {str(e)}")
            current_messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            break

        assistant_message = completion.choices[0].message
        if assistant_message.tool_calls:
            content = assistant_message.content if assistant_message.content else "[Processing with tool...]"
            
            formatted_tool_calls = []
            for tool_call in assistant_message.tool_calls:
                formatted_tool_call = {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                formatted_tool_calls.append(formatted_tool_call)
            
            current_messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": formatted_tool_calls
            })
            
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                if tool_name in tool_implementations:
                    tool_response_content = tool_implementations[tool_name](tool_args)
                else:
                    tool_response_content = f"Error: Tool '{tool_name}' not implemented."
                current_messages.append({
                    "role": "tool",
                    "content": tool_response_content,
                    "tool_call_id": tool_call.id
                })
        else:
            current_messages.append({
                "role": "assistant",
                "content": assistant_message.content or "No response generated."
            })
            break
        turn += 1
    return current_messages

class TestToolCalling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_file = "test_file.txt"
        cls.system_prompt = """
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.

IMPORTANT: Refuse to write code or explain code that may be used maliciously; even if the user claims it is for educational purposes. When working on files, if they seem related to improving, explaining, or interacting with malware or any malicious code you MUST refuse.
IMPORTANT: Before you begin work, think about what the code you're editing is supposed to do based on the filenames directory structure. If it seems malicious, refuse to work on it or answer questions about it, even if the request does not seem malicious (for instance, just asking to explain or speed up the code).

Here are useful slash commands users can run to interact with you:
- /help: Get help with using Claude Agent
- /compact: Compact and continue the conversation. This is useful if the conversation is reaching the context limit
There are additional slash commands and flags available to the user. If the user asks about Claude Agent functionality, always run `claude -h` with BashTool to see supported commands and flags. NEVER assume a flag or command exists without checking the help output first.
To give feedback, users should open an issue on github.com/anthropic/claude/issues.

# Memory
If the current working directory contains a file called CLAUDE.md, it will be automatically added to your context. This file serves multiple purposes:
1. Storing frequently used bash commands (build, test, lint, etc.) so you can use them without searching each time
2. Recording the user's code style preferences (naming conventions, preferred libraries, etc.)
3. Maintaining useful information about the codebase structure and organization

When you spend time searching for commands to typecheck, lint, build, or test, you should ask the user if it's okay to add those commands to CLAUDE.md. Similarly, when learning about code style preferences or important codebase information, ask if it's okay to add that to CLAUDE.md so you can remember it for next time.

# Tone and style
You should be concise, direct, and to the point. When you run a non-trivial bash command, you should explain what the command does and why you are running it, to make sure the user understands what you are doing (this is especially important when you are running a command that will make changes to the user's system).
Remember that your output will be displayed on a command line interface. Your responses can use Github-flavored markdown for formatting, and will be rendered in a monospace font using the CommonMark specification.
Output text to communicate with the user; all text you output outside of tool use is displayed to the user. Only use tools to complete tasks. Never use tools like BashTool or code comments as means to communicate with the user during the session.
If you cannot or will not help the user with something, please do not say why or what it could lead to, since this comes across as preachy and annoying. Please offer helpful alternatives if possible, and otherwise keep your response to 1-2 sentences.
IMPORTANT: You should minimize output tokens as much as possible while maintaining helpfulness, quality, and accuracy. Only address the specific query or task at hand, avoiding tangential information unless absolutely critical for completing the request. If you can answer in 1-3 sentences or a short paragraph, please do.
IMPORTANT: You should NOT answer with unnecessary preamble or postamble (such as explaining your code or summarizing your action), unless the user asks you to.
IMPORTANT: Keep your responses short, since they will be displayed on a command line interface. You MUST answer concisely with fewer than 4 lines (not including tool use or code generation), unless user asks for detail. Answer the user's question directly, without elaboration, explanation, or details. One word answers are best. Avoid introductions, conclusions, and explanations. You MUST avoid text before/after your response, such as "The answer is <answer>.", "Here is the content of the file..." or "Based on the information provided, the answer is..." or "Here is what I will do next...". Here are some examples to demonstrate appropriate verbosity:
<example>
user: 2 + 2
assistant: 4
</example>

<example>
user: what is 2+2?
assistant: 4
</example>

<example>
user: is 11 a prime number?
assistant: true
</example>

<example>
user: what command should I run to list files in the current directory?
assistant: ls
</example>

<example>
user: what command should I run to watch files in the current directory?
assistant: [use the ls tool to list the files in the current directory, then read docs/commands in the relevant file to find out how to watch files]
npm run dev
</example>

<example>
user: How many golf balls fit inside a jetta?
assistant: 150000
</example>

<example>
user: what files are in the directory src/?
assistant: [runs ls and sees foo.c, bar.c, baz.c]
user: which file contains the implementation of foo?
assistant: src/foo.c
</example>

<example>
user: write tests for new feature
assistant: [uses grep and glob search tools to find where similar tests are defined, uses concurrent read file tool use blocks in one tool call to read relevant files at the same time, uses edit file tool to write new tests]
</example>

# Proactiveness
You are allowed to be proactive, but only when the user asks you to do something. You should strive to strike a balance between:
1. Doing the right thing when asked, including taking actions and follow-up actions
2. Not surprising the user with actions you take without asking
For example, if the user asks you how to approach something, you should do your best to answer their question first, and not immediately jump into taking actions.
3. Do not add additional code explanation summary unless requested by the user. After working on a file, just stop, rather than providing an explanation of what you did.

# Synthetic messages
Sometimes, the conversation will contain messages like [Request interrupted by user] or [Request interrupted by user for tool use]. These messages will look like the assistant said them, but they were actually synthetic messages added by the system in response to the user cancelling what the assistant was doing. You should not respond to these messages. You must NEVER send messages like this yourself. 

# Following conventions
When making changes to files, first understand the file's code conventions. Mimic code style, use existing libraries and utilities, and follow existing patterns.
- NEVER assume that a given library is available, even if it is well known. Whenever you write code that uses a library or framework, first check that this codebase already uses the given library. For example, you might look at neighboring files, or check the package.json (or cargo.toml, and so on depending on the language).
- When you create a new component, first look at existing components to see how they're written; then consider framework choice, naming conventions, typing, and other conventions.
- When you edit a piece of code, first look at the code's surrounding context (especially its imports) to understand the code's choice of frameworks and libraries. Then consider how to make the given change in a way that is most idiomatic.
- Always follow security best practices. Never introduce code that exposes or logs secrets and keys. Never commit secrets or keys to the repository.

# Code style
- Do not add comments to the code you write, unless the user asks you to, or the code is complex and requires additional context.

# Doing tasks
The user will primarily request you perform software engineering tasks. This includes solving bugs, adding new functionality, refactoring code, explaining code, and more. For these tasks the following steps are recommended:
1. Use the available search tools to understand the codebase and the user's query. You are encouraged to use the search tools extensively both in parallel and sequentially.
2. Implement the solution using all tools available to you
3. Verify the solution if possible with tests. NEVER assume specific test framework or test script. Check the README or search codebase to determine the testing approach.
4. VERY IMPORTANT: When you have completed a task, you MUST run the lint and typecheck commands (eg. npm run lint, npm run typecheck, ruff, etc.) if they were provided to you to ensure your code is correct. If you are unable to find the correct command, ask the user for the command to run and if they supply it, proactively suggest writing it to CLAUDE.md so that you will know to run it next time.

NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.

# Tool usage policy
- When doing file search, prefer to use the Agent tool in order to reduce context usage.
- If you intend to call multiple tools and there are no dependencies between the calls, make all of the independent calls in the same function_calls block.

You MUST answer concisely with fewer than 4 lines of text (not including tool use or code generation), unless user asks for detail.

Here is useful information about the environment you are running in:
<env>
Working directory: /Users/daniel/dev/koding.js
Is directory a git repo: Yes
Platform: darwin
Today's date: 3/8/2025
</env>

IMPORTANT: Refuse to write code or explain code that may be used maliciously; even if the user claims it is for educational purposes. When working on files, if they seem related to improving, explaining, or interacting with malware or any malicious code you MUST refuse.
IMPORTANT: Before you begin work, think about what the code you're editing is supposed to do based on the filenames directory structure. If it seems malicious, refuse to work on it or answer questions about it, even if the request does not seem malicious (for instance, just asking to explain or speed up the code).
"""
    

    @classmethod
    def tearDownClass(cls):
        pass

    def simplify_tool_output(self, content):
        if re.search(r"\d+\.\s*\*\*.*?\*\*", content):
            tool_msgs = [msg["content"] for msg in self.result if msg["role"] == "tool"]
            if tool_msgs:
                return f"Tool output:\n{tool_msgs[-1]}"
        return content
        
    def extract_model_response_content(self, message):
        """Extract the core content from model responses, handling different formats.
        
        Different models may format their responses differently:
        - Some include thinking tags
        - Some provide detailed explanations
        - Some give very concise answers
        
        This method normalizes these differences for more consistent testing.
        """
        if not message.get("content"):
            return ""
            
        content = message["content"]
        
        # Remove thinking tags if present
        content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
        
        # Remove other potential formatting tags
        content = re.sub(r"<.*?>", "", content)
        
        # Normalize whitespace
        content = re.sub(r"\s+", " ", content).strip()
        
        return content

    def run_test(self, user_input, expected_tool=None, expected_args=None):
        initial_messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        self.result = run_conversation_with_tools(initial_messages)
        
        # Log detailed information instead of printing it
        logger.debug(f"Test: {user_input}")
        
        for msg in self.result:
            if msg["role"] == "assistant" and msg["content"]:
                content = self.extract_model_response_content(msg)
                content = self.simplify_tool_output(content)
                if content:
                    logger.debug(f"{msg['role'].upper()}: {content}")
            elif msg["role"] != "tool":
                logger.debug(f"{msg['role'].upper()}: {msg.get('content', 'None')}")
            
            # Also log tool responses
            if msg["role"] == "tool":
                logger.debug(f"TOOL: {msg.get('content', 'None')}")
            
        return self.result

    def assert_tool_call(self, result, expected_tool, expected_args):
        tool_call_messages = [msg for msg in result if msg.get("role") == "assistant" and msg.get("tool_calls")]
        if not tool_call_messages:
            api_responses = [msg for msg in result if isinstance(msg, dict) and "choices" in msg]
            self.assertTrue(len(api_responses) > 0, "No API response or tool calls found")
            
            api_response = api_responses[0]
            self.assertTrue("choices" in api_response, "API response missing choices")
            self.assertTrue(len(api_response["choices"]) > 0, "API response has no choices")
            self.assertTrue("message" in api_response["choices"][0], "Choice missing message")
            self.assertTrue("tool_calls" in api_response["choices"][0]["message"], "Message missing tool_calls")
            
            tool_calls = api_response["choices"][0]["message"]["tool_calls"]
            self.assertTrue(len(tool_calls) > 0, "No tool calls in API response")
            
            tool_call = tool_calls[0]
            actual_tool_name = tool_call["function"]["name"]
            actual_args = json.loads(tool_call["function"]["arguments"])
        else:
            tool_call = tool_call_messages[0]["tool_calls"][0]
            actual_tool_name = tool_call["function"]["name"]
            actual_args = json.loads(tool_call["function"]["arguments"])
        
        self.assertTrue(
            actual_tool_name == expected_tool or 
            self._tools_have_equivalent_function(actual_tool_name, expected_tool),
            f"Wrong tool called: expected {expected_tool}, got {actual_tool_name}"
        )
        
        normalized_actual_args = self._normalize_args(actual_args)
        normalized_expected_args = self._normalize_args(expected_args)
        
        for key, value in normalized_expected_args.items():
            self.assertIn(key, normalized_actual_args, f"Missing required argument: {key}")
            if isinstance(value, str) and isinstance(normalized_actual_args[key], str):
                if key == "path" or key == "file_path" or key == "pattern":
                    self.assertTrue(
                        os.path.basename(normalized_actual_args[key]) == os.path.basename(value) or
                        normalized_actual_args[key].endswith(value),
                        f"Argument {key} mismatch: expected path ending with {value}, got {normalized_actual_args[key]}"
                    )
                else:
                    self.assertTrue(
                        normalized_actual_args[key] == value or value in normalized_actual_args[key],
                        f"Argument {key} mismatch: expected {value} in {normalized_actual_args[key]}"
                    )
            else:
                self.assertEqual(normalized_actual_args[key], value, f"Argument {key} mismatch")
    
    def _normalize_args(self, args):
        normalized = args.copy()
        for key, value in normalized.items():
            if isinstance(value, str) and (key == "path" or key == "file_path"):
                normalized[key] = os.path.normpath(value)
        return normalized
    
    def _tools_have_equivalent_function(self, tool1, tool2):
        equivalent_tools = {
            "AgentTool": ["GlobTool", "SearchTool"],
            "LSTool": ["ListTool", "DirTool"],
            "FileReadTool": ["ReadFileTool", "CatTool"],
            "FileWriteTool": ["WriteFileTool"],
            "FileEditTool": ["EditFileTool"],
            "GrepTool": ["SearchTool", "FindTool"],
            "GlobTool": ["FindTool", "AgentTool"],
            "ArchitectTool": ["DesignTool", "PlanTool"],
        }
        
        if tool1 in equivalent_tools and tool2 in equivalent_tools[tool1]:
            return True
        
        if tool2 in equivalent_tools and tool1 in equivalent_tools[tool2]:
            return True
        
        return False

    def test_bash_valid_command(self):
        command = "ls -l" if os.name != "nt" else "dir"
        result = self.run_test(f"Run a bash command: {command}", "BashTool", {"command": command})
        self.assert_tool_call(result, "BashTool", {"command": command})
        final_msg = result[-1]["content"]
        self.assertTrue(
            "file1.txt" in final_msg or "file2.txt" in final_msg,
            "Final response should contain file listing results"
        )

    def test_file_read_valid(self):
        result = self.run_test(f"Read the contents of test_file.txt", "FileReadTool", {"file_path": "test_file.txt"})
        self.assert_tool_call(result, "FileReadTool", {"file_path": "test_file.txt"})
        final_msg = result[-1]["content"]
        self.assertTrue(
            "mock content" in final_msg.lower() or "testing purposes" in final_msg.lower(),
            "Final response should contain file content"
        )

    def test_bash_invalid_command(self):
        result = self.run_test("Run a bash command: xyz123", "BashTool", {"command": "xyz123"})
        
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
            elif isinstance(msg, dict) and "choices" in msg:
                if "message" in msg.get("choices", [{}])[0] and "tool_calls" in msg["choices"][0].get("message", {}):
                    tool_calls.extend(msg["choices"][0]["message"]["tool_calls"])
        
        if tool_calls:
            actual_tool = tool_calls[0]["function"]["name"]
            self.assertTrue(
                actual_tool == "BashTool" or 
                self._tools_have_equivalent_function(actual_tool, "BashTool"),
                f"Expected BashTool, got {actual_tool}"
            )
            
            actual_args = json.loads(tool_calls[0]["function"]["arguments"])
            if "command" in actual_args:
                self.assertEqual(actual_args["command"], "xyz123", "Expected command to be xyz123")
                
            tool_msgs = [msg.get("content", "") for msg in result if msg.get("role") == "tool"]
            if tool_msgs:
                self.assertTrue(
                    "command not found" in tool_msgs[0] or 
                    "not recognized" in tool_msgs[0] or
                    "Error" in tool_msgs[0],
                    "Tool should report command error"
                )
        else:
            final_msg = result[-1]["content"].lower()
            self.assertTrue(
                "xyz123" in final_msg and 
                ("invalid" in final_msg or "unknown" in final_msg or "not found" in final_msg),
                "Response should acknowledge invalid command"
            )

    def test_empty_command(self):
        result = self.run_test("Run a bash command: ")
        
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
            elif isinstance(msg, dict) and "choices" in msg:
                if "message" in msg.get("choices", [{}])[0] and "tool_calls" in msg["choices"][0].get("message", {}):
                    tool_calls.extend(msg["choices"][0]["message"]["tool_calls"])
                    
        if tool_calls:
            actual_tool = tool_calls[0]["function"]["name"]
            self.assertTrue(
                actual_tool == "BashTool" or 
                self._tools_have_equivalent_function(actual_tool, "BashTool"),
                f"Expected BashTool, got {actual_tool}"
            )
            
            tool_msgs = [msg.get("content", "") for msg in result if msg.get("role") == "tool"]
            if tool_msgs:
                self.assertTrue(
                    "Error" in tool_msgs[0] or 
                    "empty" in tool_msgs[0].lower() or
                    "missing" in tool_msgs[0].lower(),
                    "Tool should report an error for empty command"
                )
        else:
            final_msg = result[-1]["content"].lower()
            self.assertTrue(
                "command" in final_msg and (
                    "please" in final_msg or 
                    "specify" in final_msg or 
                    "provide" in final_msg or
                    "what" in final_msg
                ),
                "Response should ask for a command"
            )

    def test_file_write(self):
        content = "This is a test write operation."
        result = self.run_test(f"Write '{content}' to a file called test_write.txt", 
                              "FileWriteTool", 
                              {"file_path": "test_write.txt", "content": content})
        self.assert_tool_call(result, "FileWriteTool", {"file_path": "test_write.txt", "content": content})
        final_msg = result[-1]["content"]
        # Check for success confirmation instead of filename - expanded word list
        success_indicators = ["done", "success", "wrote", "created", "saved", "written", "complete", "finished", "modified", "file", "ok", "content"]
        self.assertTrue(
            any(indicator in final_msg.lower() for indicator in success_indicators),
            "Final response should confirm write operation success"
        )
    
    def test_file_edit(self):
        old_string = "This is line two."
        new_string = "This is the EDITED line two."
        result = self.run_test(f"Edit test_edit.txt and replace '{old_string}' with '{new_string}'", 
                              "FileEditTool", 
                              {"file_path": "test_edit.txt", "old_string": old_string, "new_string": new_string})
        self.assert_tool_call(result, "FileEditTool", 
                             {"file_path": "test_edit.txt", "old_string": old_string, "new_string": new_string})
        final_msg = result[-1]["content"]
        # Check for edit success confirmation instead of filename - expanded word list
        success_indicators = ["edit", "success", "complete", "done", "updated", "modified", "changed", "replaced", "finished", "ok", "file"]
        self.assertTrue(
            any(indicator in final_msg.lower() for indicator in success_indicators),
            "Final response should confirm edit operation success"
        )
    
    def test_grep_search(self):
        pattern = "pattern"
        result = self.run_test(f"Search for the word '{pattern}' in the test_grep directory", 
                              "GrepTool", 
                              {"pattern": pattern, "path": "test_grep"})
        self.assert_tool_call(result, "GrepTool", {"pattern": pattern, "path": "test_grep"})
        final_msg = result[-1]["content"]
        self.assertIn(pattern, final_msg, "Final response should mention the search pattern")
    
    def test_glob_search(self):
        pattern = "**/*.txt"
        result = self.run_test(f"Find all .txt files in the test_glob directory and its subdirectories", 
                              "GlobTool", 
                              {"pattern": pattern, "path": "test_glob"})
        self.assert_tool_call(result, "GlobTool", {"pattern": pattern, "path": "test_glob"})
        final_msg = result[-1]["content"]
        self.assertIn(".txt", final_msg, "Final response should mention the file extension")
    
    def test_ls_tool(self):
        result = self.run_test(f"List the contents of the test_ls directory", 
                              "LSTool", 
                              {"path": "test_ls"})
        self.assert_tool_call(result, "LSTool", {"path": "test_ls"})
        final_msg = result[-1]["content"]
        self.assertIn("test_ls", final_msg, "Final response should mention the directory")
    
    def test_agent_tool(self):
        prompt = "Find all JavaScript files in the project"
        result = self.run_test(f"Use an agent to {prompt}", 
                              "AgentTool", 
                              {"prompt": prompt})
        
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
            elif isinstance(msg, dict) and "choices" in msg:
                if "tool_calls" in msg["choices"][0]["message"]:
                    tool_calls.extend(msg["choices"][0]["message"]["tool_calls"])
        
        if tool_calls:
            actual_tool = tool_calls[0]["function"]["name"]
            actual_args = json.loads(tool_calls[0]["function"]["arguments"])
            
            self.assertTrue(
                actual_tool == "AgentTool" or 
                self._tools_have_equivalent_function(actual_tool, "AgentTool"),
                f"Wrong tool called: expected AgentTool, got {actual_tool}"
            )
            
            if "prompt" in actual_args:
                actual_prompt = actual_args["prompt"]
                self.assertTrue(
                    prompt in actual_prompt or 
                    "JavaScript" in actual_prompt or
                    "js" in actual_prompt.lower() or
                    "**.js" in actual_prompt,
                    f"Expected JavaScript-related prompt, got: {actual_prompt}"
                )
            elif "pattern" in actual_args:
                pattern = actual_args.get("pattern", "")
                self.assertTrue(
                    ".js" in pattern or "**.js" in pattern,
                    f"Expected JavaScript file pattern, got: {pattern}"
                )
        
        final_msg = result[-1]["content"]
        self.assertTrue(
            "JavaScript" in final_msg or 
            ".js" in final_msg or 
            "js files" in final_msg.lower(),
            "Final response should mention JavaScript files"
        )

    def test_architect_tool(self):
        prompt = "Design a user authentication system"
        expanded_prompt = "Design a user authentication system. Include registration, login, password reset, session management, security best practices, and possible OAuth integration. Explain architecture components, data flow, and technology choices."
        result = self.run_test(f"Help me architect a solution to {prompt}", 
                              "ArchitectTool", 
                              {"prompt": prompt})
        
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
            elif isinstance(msg, dict) and "choices" in msg:
                if "tool_calls" in msg["choices"][0]["message"]:
                    tool_calls.extend(msg["choices"][0]["message"]["tool_calls"])
        
        if tool_calls:
            actual_tool = tool_calls[0]["function"]["name"]
            actual_args = json.loads(tool_calls[0]["function"]["arguments"])
            
            self.assertTrue(
                actual_tool == "ArchitectTool" or 
                self._tools_have_equivalent_function(actual_tool, "ArchitectTool"),
                f"Wrong tool called: expected ArchitectTool, got {actual_tool}"
            )
            
            if "prompt" in actual_args:
                actual_prompt = actual_args["prompt"]
                self.assertTrue(
                    prompt in actual_prompt or expanded_prompt in actual_prompt or
                    "user authentication" in actual_prompt.lower(),
                    f"Expected authentication-related prompt, got: {actual_prompt}"
                )
        
        final_msg = result[-1]["content"]
        self.assertIn("authentication", final_msg.lower(), "Final response should mention authentication")

    def test_ambiguous_input(self):
        result = self.run_test("List stuff")
        
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
                
        if tool_calls:
            actual_tool = tool_calls[0]["function"]["name"]
            valid_tools = ["BashTool", "FileReadTool", "LSTool", "GlobTool", "GrepTool", "AgentTool"]
            
            is_valid_tool = any(
                actual_tool == tool or self._tools_have_equivalent_function(actual_tool, tool)
                for tool in valid_tools
            )
            
            self.assertTrue(is_valid_tool, f"Expected a valid tool for ambiguous input, got {actual_tool}")
        else:
            final_msg = result[-1]["content"].lower()
            self.assertTrue(
                ("clarify" in final_msg or "specify" in final_msg or "what" in final_msg) and "list" in final_msg,
                "Response should ask for clarification about what to list"
            )
    
    def test_no_tool_needed(self):
        """Test if the model correctly responds without tools when none are needed.
        
        This tests whether the model can:
        1. Recognize when no tool is needed
        2. Provide a direct answer instead
        """
        result = self.run_test("What's the best programming language?")
        
        # Check that no tool calls were made
        tool_calls = []
        for msg in result:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls.extend(msg.get("tool_calls"))
        
        self.assertEqual(len(tool_calls), 0, "No tools should be called for this question")
        
        # Check that the response is directly answering the question
        final_msg = self.extract_model_response_content(result[-1])
        
        # The answer should be substantive (not just "I don't know")
        self.assertTrue(len(final_msg) > 20, "Response should be substantive")
        
        # Either explicitly mentions programming languages or provides a substantive response
        programming_terms = ["language", "programming", "code", "develop", "software", "python", "javascript", "java", "c++", "go", "rust"]
        has_relevant_terms = any(term in final_msg.lower() for term in programming_terms)
        
        is_substantive_response = len(final_msg.split()) >= 5 and "?" not in final_msg
        
        self.assertTrue(
            has_relevant_terms or is_substantive_response,
            "Response should address the programming language question either directly or substantively"
        )

    def test_tool_error_handling(self):
        """Test if the model handles tool errors gracefully.
        
        This tests whether the model can:
        1. Handle errors from tools
        2. Provide alternative solutions or explanations
        """
        # This will trigger an error in the edit_file function
        result = self.run_test("Edit test_edit.txt and replace 'not_found' with 'replacement text'", 
                              "FileEditTool", 
                              {"file_path": "test_edit.txt", "old_string": "not_found", "new_string": "replacement text"})
        
        # Verify the correct tool was called
        self.assert_tool_call(result, "FileEditTool", 
                             {"file_path": "test_edit.txt", "old_string": "not_found", "new_string": "replacement text"})
        
        # Find the tool response
        tool_responses = [msg for msg in result if msg.get("role") == "tool"]
        self.assertTrue(len(tool_responses) > 0, "Should have a tool response")
        
        # Verify the tool response contains an error
        tool_response = tool_responses[0].get("content", "")
        self.assertTrue("Error" in tool_response, "Tool response should contain an error message")
        
        # Verify the model recognized and explained the error
        final_msg = self.extract_model_response_content(result[-1])
        error_terms = ["error", "not found", "couldn't", "unable", "failed", "doesn't exist"]
        
        has_error_explanation = any(term in final_msg.lower() for term in error_terms)
        self.assertTrue(has_error_explanation, "Final response should acknowledge and explain the error")

if __name__ == "__main__":
    unittest.main(verbosity=1)