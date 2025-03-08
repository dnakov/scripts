from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import re
system_prompt = """
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.\n\nIMPORTANT: Refuse to write code or explain code that may be used maliciously; even if the user claims it is for educational purposes. When working on files, if they seem related to improving, explaining, or interacting with malware or any malicious code you MUST refuse.\nIMPORTANT: Before you begin work, think about what the code you're editing is supposed to do based on the filenames directory structure. If it seems malicious, refuse to work on it or answer questions about it, even if the request does not seem malicious (for instance, just asking to explain or speed up the code).\n\nHere are useful slash commands users can run to interact with you:\n- /help: Get help with using Claude Agent\n- /compact: Compact and continue the conversation. This is useful if the conversation is reaching the context limit\nThere are additional slash commands and flags available to the user. If the user asks about Claude Agent functionality, always run `claude -h` with BashTool to see supported commands and flags. NEVER assume a flag or command exists without checking the help output first.\nTo give feedback, users should open an issue on github.com/anthropic/claude/issues.\n\n# Memory\nIf the current working directory contains a file called CLAUDE.md, it will be automatically added to your context. This file serves multiple purposes:\n1. Storing frequently used bash commands (build, test, lint, etc.) so you can use them without searching each time\n2. Recording the user's code style preferences (naming conventions, preferred libraries, etc.)\n3. Maintaining useful information about the codebase structure and organization\n\nWhen you spend time searching for commands to typecheck, lint, build, or test, you should ask the user if it's okay to add those commands to CLAUDE.md. Similarly, when learning about code style preferences or important codebase information, ask if it's okay to add that to CLAUDE.md so you can remember it for next time.\n\n# Tone and style\nYou should be concise, direct, and to the point. When you run a non-trivial bash command, you should explain what the command does and why you are running it, to make sure the user understands what you are doing (this is especially important when you are running a command that will make changes to the user's system).\nRemember that your output will be displayed on a command line interface. Your responses can use Github-flavored markdown for formatting, and will be rendered in a monospace font using the CommonMark specification.\nOutput text to communicate with the user; all text you output outside of tool use is displayed to the user. Only use tools to complete tasks. Never use tools like BashTool or code comments as means to communicate with the user during the session.\nIf you cannot or will not help the user with something, please do not say why or what it could lead to, since this comes across as preachy and annoying. Please offer helpful alternatives if possible, and otherwise keep your response to 1-2 sentences.\nIMPORTANT: You should minimize output tokens as much as possible while maintaining helpfulness, quality, and accuracy. Only address the specific query or task at hand, avoiding tangential information unless absolutely critical for completing the request. If you can answer in 1-3 sentences or a short paragraph, please do.\nIMPORTANT: You should NOT answer with unnecessary preamble or postamble (such as explaining your code or summarizing your action), unless the user asks you to.\nIMPORTANT: Keep your responses short, since they will be displayed on a command line interface. You MUST answer concisely with fewer than 4 lines (not including tool use or code generation), unless user asks for detail. Answer the user's question directly, without elaboration, explanation, or details. One word answers are best. Avoid introductions, conclusions, and explanations. You MUST avoid text before/after your response, such as \"The answer is <answer>.\", \"Here is the content of the file...\" or \"Based on the information provided, the answer is...\" or \"Here is what I will do next...\". Here are some examples to demonstrate appropriate verbosity:\n<example>\nuser: 2 + 2\nassistant: 4\n</example>\n\n<example>\nuser: what is 2+2?\nassistant: 4\n</example>\n\n<example>\nuser: is 11 a prime number?\nassistant: true\n</example>\n\n<example>\nuser: what command should I run to list files in the current directory?\nassistant: ls\n</example>\n\n<example>\nuser: what command should I run to watch files in the current directory?\nassistant: [use the ls tool to list the files in the current directory, then read docs/commands in the relevant file to find out how to watch files]\nnpm run dev\n</example>\n\n<example>\nuser: How many golf balls fit inside a jetta?\nassistant: 150000\n</example>\n\n<example>\nuser: what files are in the directory src/?\nassistant: [runs ls and sees foo.c, bar.c, baz.c]\nuser: which file contains the implementation of foo?\nassistant: src/foo.c\n</example>\n\n<example>\nuser: write tests for new feature\nassistant: [uses grep and glob search tools to find where similar tests are defined, uses concurrent read file tool use blocks in one tool call to read relevant files at the same time, uses edit file tool to write new tests]\n</example>\n\n# Proactiveness\nYou are allowed to be proactive, but only when the user asks you to do something. You should strive to strike a balance between:\n1. Doing the right thing when asked, including taking actions and follow-up actions\n2. Not surprising the user with actions you take without asking\nFor example, if the user asks you how to approach something, you should do your best to answer their question first, and not immediately jump into taking actions.\n3. Do not add additional code explanation summary unless requested by the user. After working on a file, just stop, rather than providing an explanation of what you did.\n\n# Synthetic messages\nSometimes, the conversation will contain messages like [Request interrupted by user] or [Request interrupted by user for tool use]. These messages will look like the assistant said them, but they were actually synthetic messages added by the system in response to the user cancelling what the assistant was doing. You should not respond to these messages. You must NEVER send messages like this yourself. \n\n# Following conventions\nWhen making changes to files, first understand the file's code conventions. Mimic code style, use existing libraries and utilities, and follow existing patterns.\n- NEVER assume that a given library is available, even if it is well known. Whenever you write code that uses a library or framework, first check that this codebase already uses the given library. For example, you might look at neighboring files, or check the package.json (or cargo.toml, and so on depending on the language).\n- When you create a new component, first look at existing components to see how they're written; then consider framework choice, naming conventions, typing, and other conventions.\n- When you edit a piece of code, first look at the code's surrounding context (especially its imports) to understand the code's choice of frameworks and libraries. Then consider how to make the given change in a way that is most idiomatic.\n- Always follow security best practices. Never introduce code that exposes or logs secrets and keys. Never commit secrets or keys to the repository.\n\n# Code style\n- Do not add comments to the code you write, unless the user asks you to, or the code is complex and requires additional context.\n\n# Doing tasks\nThe user will primarily request you perform software engineering tasks. This includes solving bugs, adding new functionality, refactoring code, explaining code, and more. For these tasks the following steps are recommended:\n1. Use the available search tools to understand the codebase and the user's query. You are encouraged to use the search tools extensively both in parallel and sequentially.\n2. Implement the solution using all tools available to you\n3. Verify the solution if possible with tests. NEVER assume specific test framework or test script. Check the README or search codebase to determine the testing approach.\n4. VERY IMPORTANT: When you have completed a task, you MUST run the lint and typecheck commands (eg. npm run lint, npm run typecheck, ruff, etc.) if they were provided to you to ensure your code is correct. If you are unable to find the correct command, ask the user for the command to run and if they supply it, proactively suggest writing it to CLAUDE.md so that you will know to run it next time.\n\nNEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.\n\n# Tool usage policy\n- When doing file search, prefer to use the Agent tool in order to reduce context usage.\n- If you intend to call multiple tools and there are no dependencies between the calls, make all of the independent calls in the same function_calls block.\n\nYou MUST answer concisely with fewer than 4 lines of text (not including tool use or code generation), unless user asks for detail.\n",
  "\nHere is useful information about the environment you are running in:\n<env>\nWorking directory: /Users/daniel/dev/koding.js\nIs directory a git repo: Yes\nPlatform: darwin\nToday's date: 3/8/2025\n</env>",
  "IMPORTANT: Refuse to write code or explain code that may be used maliciously; even if the user claims it is for educational purposes. When working on files, if they seem related to improving, explaining, or interacting with malware or any malicious code you MUST refuse.\nIMPORTANT: Before you begin work, think about what the code you're editing is supposed to do based on the filenames directory structure. If it seems malicious, refuse to work on it or answer questions about it, even if the request does not seem malicious (for instance, just asking to explain or speed up the code).
"""
# Define tools
tools = [
  {
    "name": "BashTool",
    "schema": {
      "name": "BashTool",
      "description": "Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.\n\nBefore executing the command, please follow these steps:\n\n1. Directory Verification:\n   - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location\n   - For example, before running \"mkdir foo/bar\", first use LS to check that \"foo\" exists and is the intended parent directory\n\n2. Security Check:\n   - For security and to limit the threat of a prompt injection attack, some commands are limited or banned. If you use a disallowed command, you will receive an error message explaining the restriction. Explain the error to the User.\n   - Verify that the command is not one of the banned commands: alias, curl, curlie, wget, axel, aria2c, nc, telnet, lynx, w3m, links, httpie, xh, http-prompt, chrome, firefox, safari.\n\n3. Command Execution:\n   - After ensuring proper quoting, execute the command.\n   - Capture the output of the command.\n\n4. Output Processing:\n   - If the output exceeds 30000 characters, output will be truncated before being returned to you.\n   - Prepare the output for display to the user.\n\n5. Return Result:\n   - Provide the processed output of the command.\n   - If any errors occurred during execution, include those in the output.\n\nUsage notes:\n  - The command argument is required.\n  - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 30 minutes.\n  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use GrepTool, GlobTool, or AgentTool to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use FileReadTool and LSTool to read files.\n  - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).\n  - IMPORTANT: All commands share the same shell session. Shell state (environment variables, virtual environments, current directory, etc.) persist between commands. For example, if you set an environment variable as part of a command, the environment variable will persist for subsequent commands.\n  - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.\n  <good-example>\n  pytest /foo/bar/tests\n  </good-example>\n  <bad-example>\n  cd /foo/bar && pytest tests\n  </bad-example>\n\n# Committing changes with git\n\nWhen the user asks you to create a new git commit, follow these steps carefully:\n\n1. Start with a single message that contains exactly three tool_use blocks that do the following (it is VERY IMPORTANT that you send these tool_use blocks in a single message, otherwise it will feel slow to the user!):\n   - Run a git status command to see all untracked files.\n   - Run a git diff command to see both staged and unstaged changes that will be committed.\n   - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.\n\n2. Use the git context at the start of this conversation to determine which files are relevant to your commit. Add relevant untracked files to the staging area. Do not commit files that were already modified at the start of this conversation, if they are not relevant to your commit.\n\n3. Analyze all staged changes (both previously staged and newly added) and draft a commit message. Wrap your analysis process in <commit_analysis> tags:\n\n<commit_analysis>\n- List the files that have been changed or added\n- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)\n- Brainstorm the purpose or motivation behind these changes\n- Do not use tools to explore code, beyond what is available in the git context\n- Assess the impact of these changes on the overall project\n- Check for any sensitive information that shouldn't be committed\n- Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"\n- Ensure your language is clear, concise, and to the point\n- Ensure the message accurately reflects the changes and their purpose (i.e. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)\n- Ensure the message is not generic (avoid words like \"Update\" or \"Fix\" without context)\n- Review the draft message to ensure it accurately reflects the changes and their purpose\n</commit_analysis>\n\n4. Create the commit with a message ending with:\n🤖 Generated with Claude Agent\nCo-Authored-By: Claude <noreply@anthropic.com>\n\n- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:\n<example>\ngit commit -m \"$(cat <<'EOF'\n   Commit message here.\n\n   🤖 Generated with Claude Agent\n   Co-Authored-By: Claude <noreply@anthropic.com>\n   EOF\n   )\"\n</example>\n\n5. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.\n\n6. Finally, run git status to make sure the commit succeeded.\n\nImportant notes:\n- When possible, combine the \"git add\" and \"git commit\" commands into a single \"git commit -am\" command, to speed things up\n- However, be careful not to stage files (e.g. with `git add .`) for commits that aren't part of the change, they may have untracked files they want to keep around, but not commit.\n- NEVER update the git config\n- DO NOT push to the remote repository\n- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.\n- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit\n- Ensure your commit message is meaningful and concise. It should explain the purpose of the changes, not just describe them.\n- Return an empty response - the user will see the git output directly\n\n# Creating pull requests\nUse the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.\n\nIMPORTANT: When the user asks you to create a pull request, follow these steps carefully:\n\n1. Understand the current state of the branch. Remember to send a single message that contains multiple tool_use blocks (it is VERY IMPORTANT that you do this in a single message, otherwise it will feel slow to the user!):\n   - Run a git status command to see all untracked files.\n   - Run a git diff command to see both staged and unstaged changes that will be committed.\n   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote\n   - Run a git log command and `git diff main...HEAD` to understand the full commit history for the current branch (from the time it diverged from the `main` branch.)\n\n2. Create new branch if needed\n\n3. Commit changes if needed\n\n4. Push to remote with -u flag if needed\n\n5. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (not just the latest commit, but all commits that will be included in the pull request!), and draft a pull request summary. Wrap your analysis process in <pr_analysis> tags:\n\n<pr_analysis>\n- List the commits since diverging from the main branch\n- Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.)\n- Brainstorm the purpose or motivation behind these changes\n- Assess the impact of these changes on the overall project\n- Do not use tools to explore code, beyond what is available in the git context\n- Check for any sensitive information that shouldn't be committed\n- Draft a concise (1-2 bullet points) pull request summary that focuses on the \"why\" rather than the \"what\"\n- Ensure the summary accurately reflects all changes since diverging from the main branch\n- Ensure your language is clear, concise, and to the point\n- Ensure the summary accurately reflects the changes and their purpose (ie. \"add\" means a wholly new feature, \"update\" means an enhancement to an existing feature, \"fix\" means a bug fix, etc.)\n- Ensure the summary is not generic (avoid words like \"Update\" or \"Fix\" without context)\n- Review the draft summary to ensure it accurately reflects the changes and their purpose\n</pr_analysis>\n\n6. Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.\n<example>\ngh pr create --title \"the pr title\" --body \"$(cat <<'EOF'\n## Summary\n<1-3 bullet points>\n\n## Test plan\n[Checklist of TODOs for testing the pull request...]\n\n🤖 Generated with Claude Agent\nEOF\n)\"\n</example>\n\nImportant:\n- Return an empty response - the user will see the gh output directly\n- Never update git config",
      "parameters": {
        "type": "object",
        "properties": {
          "command": {
            "type": "string",
            "description": "The bash command to run"
          },
          "timeout": {
            "type": "number",
            "description": "Optional timeout in milliseconds (max 600000)"
          }
        }
      }
    }
  },
  {
    "name": "FileReadTool",
    "schema": {
      "name": "FileReadTool",
      "description": "Reads a file from the local filesystem. The file_path parameter must be an absolute path, not a relative path. By default, it reads up to 2000 lines starting from the beginning of the file. You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters. Any lines longer than 2000 characters will be truncated. For image files, the tool will display the image for you.",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "The absolute path to the file to read"
          },
          "offset": {
            "type": "number",
            "description": "The line number to start reading from (1-indexed). Only provide if the file is too large to read at once"
          },
          "limit": {
            "type": "number",
            "description": "The number of lines to read. Only provide if the file is too large to read at once"
          }
        },
        "required": [
          "file_path"
        ]
      }
    }
  },
  {
    "name": "FileWriteTool",
    "schema": {
      "name": "FileWriteTool",
      "description": "Write a file to the local filesystem.",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "The absolute path to the file to write (must be absolute, not relative)"
          },
          "content": {
            "type": "string",
            "description": "The content to write to the file"
          }
        },
        "required": [
          "file_path",
          "content"
        ]
      }
    }
  },
  {
    "DESCRIPTION": "This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool with the 'mv' command instead. For larger edits, use the Write tool to overwrite files. For Jupyter notebooks (.ipynb files), use the NotebookEditTool instead.\n\nBefore using this tool:\n\n1. Use the View tool to understand the file's contents and context\n\n2. Verify the directory path is correct (only applicable when creating new files):\n   - Use the LS tool to verify the parent directory exists and is the correct location\n\nTo make a file edit, provide the following:\n1. file_path: The absolute path to the file to modify (must be absolute, not relative)\n2. old_string: The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)\n3. new_string: The edited text to replace the old_string\n\nThe tool will replace ONE occurrence of old_string with new_string in the specified file.\n\nCRITICAL REQUIREMENTS FOR USING THIS TOOL:\n\n1. UNIQUENESS: The old_string MUST uniquely identify the specific instance you want to change. This means:\n   - Include AT LEAST 3-5 lines of context BEFORE the change point\n   - Include AT LEAST 3-5 lines of context AFTER the change point\n   - Include all whitespace, indentation, and surrounding code exactly as it appears in the file\n\n2. SINGLE INSTANCE: This tool can only change ONE instance at a time. If you need to change multiple instances:\n   - Make separate calls to this tool for each instance\n   - Each call must uniquely identify its specific instance using extensive context\n\n3. VERIFICATION: Before using this tool:\n   - Check how many instances of the target text exist in the file\n   - If multiple instances exist, gather enough context to uniquely identify each one\n   - Plan separate tool calls for each instance\n\nWARNING: If you do not follow these requirements:\n   - The tool will fail if old_string matches multiple locations\n   - The tool will fail if old_string doesn't match exactly (including whitespace)\n   - You may change the wrong instance if you don't include enough context\n\nWhen making edits:\n   - Ensure the edit results in idiomatic, correct code\n   - Do not leave the code in a broken state\n   - Always use absolute file paths (starting with /)\n\nIf you want to create a new file, use:\n   - A new file path, including dir name if needed\n   - An empty old_string\n   - The new file's contents as new_string\n\nRemember: when making multiple file edits in a row to the same file, you should prefer to send all edits in a single message with multiple calls to this tool, rather than multiple messages with a single call each.",
    "name": "FileEditTool",
    "schema": {
      "name": "FileEditTool",
      "description": "This is a tool for editing files. For moving or renaming files, you should generally use the Bash tool with the 'mv' command instead. For larger edits, use the Write tool to overwrite files. For Jupyter notebooks (.ipynb files), use the NotebookEditTool instead.\n\nBefore using this tool:\n\n1. Use the View tool to understand the file's contents and context\n\n2. Verify the directory path is correct (only applicable when creating new files):\n   - Use the LS tool to verify the parent directory exists and is the correct location\n\nTo make a file edit, provide the following:\n1. file_path: The absolute path to the file to modify (must be absolute, not relative)\n2. old_string: The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)\n3. new_string: The edited text to replace the old_string\n\nThe tool will replace ONE occurrence of old_string with new_string in the specified file.\n\nCRITICAL REQUIREMENTS FOR USING THIS TOOL:\n\n1. UNIQUENESS: The old_string MUST uniquely identify the specific instance you want to change. This means:\n   - Include AT LEAST 3-5 lines of context BEFORE the change point\n   - Include AT LEAST 3-5 lines of context AFTER the change point\n   - Include all whitespace, indentation, and surrounding code exactly as it appears in the file\n\n2. SINGLE INSTANCE: This tool can only change ONE instance at a time. If you need to change multiple instances:\n   - Make separate calls to this tool for each instance\n   - Each call must uniquely identify its specific instance using extensive context\n\n3. VERIFICATION: Before using this tool:\n   - Check how many instances of the target text exist in the file\n   - If multiple instances exist, gather enough context to uniquely identify each one\n   - Plan separate tool calls for each instance\n\nWARNING: If you do not follow these requirements:\n   - The tool will fail if old_string matches multiple locations\n   - The tool will fail if old_string doesn't match exactly (including whitespace)\n   - You may change the wrong instance if you don't include enough context\n\nWhen making edits:\n   - Ensure the edit results in idiomatic, correct code\n   - Do not leave the code in a broken state\n   - Always use absolute file paths (starting with /)\n\nIf you want to create a new file, use:\n   - A new file path, including dir name if needed\n   - An empty old_string\n   - The new file's contents as new_string\n\nRemember: when making multiple file edits in a row to the same file, you should prefer to send all edits in a single message with multiple calls to this tool, rather than multiple messages with a single call each.",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "The absolute path to the file to modify"
          },
          "old_string": {
            "type": "string",
            "description": "The text to replace"
          },
          "new_string": {
            "type": "string",
            "description": "The text to replace it with"
          }
        },
        "required": [
          "file_path",
          "old_string",
          "new_string"
        ]
      }
    }
  },
  {
    "name": "GrepTool",
    "schema": {
      "name": "GrepTool",
      "description": "\n- Fast content search tool that works with any codebase size\n- Searches file contents using regular expressions\n- Supports full regex syntax (eg. \"log.*Error\", \"function\\s+\\w+\", etc.)\n- Filter files by pattern with the include parameter (eg. \"*.js\", \"*.{ts,tsx}\")\n- Returns matching file paths sorted by modification time\n- Use this tool when you need to find files containing specific patterns\n- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n",
      "parameters": {
        "type": "object",
        "properties": {
          "pattern": {
            "type": "string",
            "description": "The regular expression pattern to search for in file contents"
          },
          "path": {
            "type": "string",
            "description": "The directory to search in. Defaults to the current working directory."
          },
          "include": {
            "type": "string",
            "description": "File pattern to include in the search (e.g. \"*.js\", \"*.{ts,tsx}\")"
          }
        },
        "required": [
          "pattern"
        ]
      }
    }
  },
  {
    "name": "GlobTool",
    "schema": {
      "name": "GlobTool",
      "description": "\n- Fast file search tool that works with any codebase size\n- Finds files by name pattern using glob syntax\n- Supports full glob syntax (eg. \"*.js\", \"**/*.{ts,tsx}\", \"src/**/*.test.js\")\n- Exclude files with the exclude parameter (eg. \"node_modules/**\")\n- Returns matching file paths sorted by modification time\n- Use this tool when you need to find files by name pattern\n- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n",
      "parameters": {
        "type": "object",
        "properties": {
          "pattern": {
            "type": "string",
            "description": "The glob pattern to search for files (e.g. \"*.js\", \"**/*.{ts,tsx}\")"
          },
          "path": {
            "type": "string",
            "description": "The directory to search in. Defaults to the current working directory."
          },
          "exclude": {
            "type": "string",
            "description": "Glob pattern to exclude from the search (e.g. \"node_modules/**\")"
          }
        },
        "required": [
          "pattern"
        ]
      }
    }
  },
  {
    "name": "LSTool",
    "schema": {
      "name": "LSTool",
      "description": "Lists files and directories in the specified path. Provides a tree-like view of the directory structure.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "The absolute path to the directory to list (must be absolute, not relative)"
          }
        },
        "required": [
          "path"
        ]
      }
    }
  },
  {
    "name": "AgentTool",
    "schema": {
      "name": "AgentTool",
      "description": "Launch a new agent that has access to various tools. When you are searching for a keyword or file and are not confident that you will find the right match on the first try, use the Agent tool to perform the search for you. For example:\n\n- If you are searching for a keyword like \"config\" or \"logger\", the Agent tool is appropriate\n- If you want to read a specific file path, use the FileReadTool or GlobTool tool instead of the Agent tool, to find the match more quickly\n- If you are searching for a specific class definition like \"class Foo\", use the GlobTool tool instead, to find the match more quickly\n\nUsage notes:\n1. Launch multiple agents concurrently whenever possible, to maximize performance\n2. When the agent is done, it will return a single message back to you\n3. Each agent invocation is stateless\n4. The agent's outputs should generally be trusted",
      "parameters": {
        "type": "object",
        "properties": {
          "prompt": {
            "type": "string",
            "description": "The task for the agent to perform"
          }
        },
        "required": [
          "prompt"
        ]
      }
    }
  },
  {
    "name": "ArchitectTool",
    "schema": {
      "name": "ArchitectTool",
      "description": "Your go-to tool for any technical or coding task. Analyzes requirements and breaks them down into clear, actionable implementation steps. Use this whenever you need help planning how to implement a feature, solve a technical problem, or structure your code.",
      "parameters": {
        "type": "object",
        "properties": {
          "prompt": {
            "type": "string",
            "description": "The technical request or coding task to analyze"
          },
          "context": {
            "type": "string",
            "description": "Optional context from previous conversation or system state"
          }
        },
        "required": [
          "prompt"
        ]
      }
    }
  }
]


model_name = "Qwen/QwQ-32B"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Create messages with a prompt that would benefit from tool use
prompt = "find out what this project does"
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt}
]

# Helper function to make output more readable by substituting large content with placeholders
def readable_output(text, system_prompt, tools):
    # Create a copy to avoid modifying the original
    readable = text
    
    # Replace system prompt with placeholder
    if system_prompt in readable:
        readable = readable.replace(system_prompt, "{{SYSTEM_PROMPT}}")
    
    # Replace tools JSON with placeholder
    # First convert tools to string representation
    for tool in tools:
      if json.dumps(tool) in readable:
        readable = readable.replace(json.dumps(tool), f"{{{tool['name']}}}")
    return readable

# Parse tool calls from the response
def extract_tool_calls(response):
    tool_calls = []
    tool_call_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
    import re
    matches = re.findall(tool_call_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match)
            tool_calls.append(tool_call)
        except json.JSONDecodeError:
            print(f"Failed to parse tool call: {match}")
    
    return tool_calls

# Clean the response from template artifacts - but only for processing, not for display
def clean_response_for_processing(response):
    import re
    
    # Only remove <tool_response> sections for processing
    # We need to do this to avoid confusion in the conversation flow
    response = re.split(r'<tool_response>', response)[0]
    
    return response.strip()

# Check if the response contains malformed tool responses
def contains_malformed_tool_responses(response):
    tool_response_pattern = r'<tool_response>\s*(.*?)\s*</tool_response>'
    import re
    matches = re.findall(tool_response_pattern, response, re.DOTALL)
    return len(matches) > 0

# Extract <think> tags content for debugging
def extract_think_content(response):
    import re
    think_pattern = r'<think>(.*?)</think>'
    matches = re.findall(think_pattern, response, re.DOTALL)
    return matches

# Function to create mock tool responses
def create_mock_tool_responses(tool_calls):
    tool_responses = []
    for tool_call in tool_calls:
        if tool_call["name"] == "BashTool":
            command = tool_call["arguments"].get("command", "")
            mock_response = f"Executed command: {command}\nOutput: Command executed successfully"
            if "ls" in command:
                mock_response = "Executed command: ls\nOutput: file1.txt file2.txt directory1/ directory2/"
            elif "grep" in command:
                mock_response = "Executed command: grep\nOutput: 3 matches found in 2 files"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "FileReadTool":
            file_path = tool_call["arguments"].get("file_path", "")
            mock_content = f"Mock content for file: {file_path}\nThis is a simulated file content for testing purposes."
            
            if "README" in file_path:
                mock_content = """# Project Name

This is a mock README file for the project.

## Description
This project is a JavaScript-based web application framework.

## Features
- Feature 1
- Feature 2
- Feature 3

## Installation
```
npm install
```

## Usage
```
npm start
```"""
            elif "package.json" in file_path:
                mock_content = """{
  "name": "project-name",
  "version": "1.0.0",
  "description": "A JavaScript-based web application framework",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.17.1",
    "react": "^17.0.2"
  }
}"""
            
            tool_responses.append({
                "role": "tool",
                "content": mock_content,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "FileWriteTool":
            file_path = tool_call["arguments"].get("file_path", "")
            mock_response = f"Successfully wrote to file: {file_path}"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "FileEditTool":
            file_path = tool_call["arguments"].get("file_path", "")
            mock_response = f"Successfully edited file: {file_path}"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "GrepTool":
            pattern = tool_call["arguments"].get("pattern", "")
            mock_response = f"Search results for pattern '{pattern}':\n/path/to/file1.txt:10: match found\n/path/to/file2.txt:25: another match found"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "GlobTool":
            pattern = tool_call["arguments"].get("pattern", "")
            path = tool_call["arguments"].get("path", "")
            
            if "README*" in pattern:
                mock_response = f"Files matching pattern '{pattern}':\n{path}/README.md"
            elif "package.json" in pattern:
                mock_response = f"Files matching pattern '{pattern}':\n{path}/package.json"
            elif ".js" in pattern or ".ts" in pattern:
                mock_response = f"Files matching pattern '{pattern}':\n{path}/src/index.js\n{path}/src/components/App.js\n{path}/src/utils/helpers.js"
            else:
                mock_response = f"Files matching pattern '{pattern}':\n{path}/file1.txt\n{path}/file2.txt\n{path}/directory/file3.txt"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "LSTool":
            path = tool_call["arguments"].get("path", "")
            mock_response = f"Directory listing for '{path}':\n├── README.md\n├── package.json\n├── src/\n│   ├── index.js\n│   ├── components/\n│   └── utils/\n└── public/"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "AgentTool":
            prompt = tool_call["arguments"].get("prompt", "")
            mock_response = f"Agent response for prompt '{prompt}':\nI've analyzed the codebase and found relevant information. Here's what I discovered..."
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
            
        elif tool_call["name"] == "ArchitectTool":
            prompt = tool_call["arguments"].get("prompt", "")
            mock_response = f"Architecture analysis for '{prompt}':\n1. Component structure\n2. Implementation steps\n3. Technical considerations"
            
            tool_responses.append({
                "role": "tool",
                "content": mock_response,
                "name": tool_call["name"]
            })
    
    return tool_responses

# Run the conversation until there are no more tool calls
def run_conversation_with_tools(initial_messages, max_turns=5):
    current_messages = initial_messages.copy()
    turn = 1
    
    while turn <= max_turns:
        print(f"\n\n{'='*30} TURN {turn} {'='*30}\n")
        
        # Apply chat template with tools
        text = tokenizer.apply_chat_template(
            current_messages,
            tools=tools,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Print the readable chat template for the first turn only
        if turn == 1:
            readable_text = readable_output(text, system_prompt, tools)
            print(f"\n=== TURN {turn}: CHAT TEMPLATE SENT TO MODEL (with placeholders) ===")
            print(readable_text)
            print("=== END OF CHAT TEMPLATE ===\n")
        
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.7
        )
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        # Get the raw response
        raw_response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        print(f"\n=== TURN {turn}: RAW RESPONSE FROM MODEL ===")
        print(raw_response)
        print("=== END OF RAW RESPONSE ===\n")
        
        # Extract and display <think> content
        think_content = extract_think_content(raw_response)
        if think_content:
            print(f"\n=== TURN {turn}: <think> CONTENT ===")
            for i, content in enumerate(think_content):
                print(f"\n--- <think> block {i+1} ---")
                print(content.strip())
            print("=== END OF <think> CONTENT ===\n")
        
        # Check for malformed responses
        if contains_malformed_tool_responses(raw_response):
            print(f"\nWARNING (TURN {turn}): Detected malformed tool responses in the model output.")
            tool_response_pattern = r'<tool_response>\s*(.*?)\s*</tool_response>'
            import re
            tool_responses_found = re.findall(tool_response_pattern, raw_response, re.DOTALL)
            if tool_responses_found:
                print(f"\n=== TURN {turn}: <tool_response> CONTENT ===")
                for i, content in enumerate(tool_responses_found):
                    print(f"\n--- <tool_response> block {i+1} ---")
                    print(content.strip())
                print("=== END OF <tool_response> CONTENT ===\n")
        
        # Extract tool calls from the processed response
        processed_response = clean_response_for_processing(raw_response)
        tool_calls = extract_tool_calls(processed_response)
        
        if tool_calls:
            print(f"\n=== TURN {turn}: EXTRACTED TOOL CALLS ===")
            for i, tool_call in enumerate(tool_calls):
                print(f"\n--- Tool call {i+1} ---")
                print(json.dumps(tool_call, indent=2))
            print("=== END OF EXTRACTED TOOL CALLS ===\n")
            
            # Create mock tool responses
            tool_responses = create_mock_tool_responses(tool_calls)
            
            print(f"\n=== TURN {turn}: TOOL RESPONSES ===")
            for i, resp in enumerate(tool_responses):
                print(f"\n--- Tool response {i+1} ---")
                print(f"Role: {resp['role']}")
                print(f"Name: {resp['name']}")
                print("Content:")
                print(resp['content'])
            print("=== END OF TOOL RESPONSES ===\n")
            
            # Add the assistant response and tool responses to the conversation
            current_messages.append({"role": "assistant", "content": raw_response, "tool_calls": tool_calls})
            current_messages.extend(tool_responses)
            
            print(f"\n=== TURN {turn}: CONTINUING CONVERSATION WITH TOOL RESPONSES ===")
            
            # Print the readable messages being sent for continuation
            print(f"\n=== TURN {turn}: MESSAGES FOR CONTINUATION (with placeholders) ===")
            for i, msg in enumerate(current_messages):
                print(f"\n--- Message {i+1} ---")
                print(f"Role: {msg['role']}")
                
                if msg['role'] == 'system':
                    print("Content: {{SYSTEM_PROMPT}}")
                else:
                    if 'tool_calls' in msg:
                        print(f"Tool calls: {len(msg['tool_calls'])}")
                    if 'name' in msg:
                        print(f"Name: {msg['name']}")
                    print("Content:")
                    print(msg['content'])
            print("=== END OF MESSAGES ===\n")
            
            turn += 1
        else:
            print(f"\n=== TURN {turn}: NO MORE TOOL CALLS DETECTED ===")
            print("Conversation complete.")
            
            # Add the final assistant response to the conversation
            current_messages.append({"role": "assistant", "content": raw_response})
            
            # Print the final conversation state
            print("\n=== FINAL CONVERSATION STATE (with placeholders) ===")
            for i, msg in enumerate(current_messages):
                print(f"\n--- Message {i+1} ---")
                print(f"Role: {msg['role']}")
                
                if msg['role'] == 'system':
                    print("Content: {{SYSTEM_PROMPT}}")
                else:
                    if 'tool_calls' in msg:
                        print(f"Tool calls: {len(msg['tool_calls'])}")
                    if 'name' in msg:
                        print(f"Name: {msg['name']}")
                    print("Content:")
                    print(msg['content'])
            print("=== END OF FINAL CONVERSATION ===\n")
            
            break
    
    if turn > max_turns:
        print(f"\nReached maximum number of turns ({max_turns}). Stopping conversation.")
    
    return current_messages

# Run the conversation
final_messages = run_conversation_with_tools(messages, max_turns=5)
