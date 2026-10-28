---
name: session-experiment
description: Use when the user wants to turn past local agent conversations (Claude Code, Kiro CLI, Strands CLI, or any other harness) into strands-evals experiments. Locates the relevant session files on the local filesystem and extracts their user inputs and assistant responses. Skip for traces stored in trace providers (CloudWatch, Langfuse, OpenSearch).
version: 0.1.0
---

# session-experiment

Converts recorded local agent sessions into a strands-evals experiment.

## Steps

### 1. Locate sessions

Find every session file on the local filesystem that matches the user's criteria. Don't open whole files to do it: session files can be large, so read metadata, use `ls -t`, `find -newermt`, `grep`, `jq`, or targeted reads. Read the criteria from the prompt:

- **Harness**: default to all harnesses.
- **Date range**: resolve relative dates in the user's local time zone; session timestamps are UTC. A session matches if any of its activity falls in the range; mtime alone isn't enough.
- **Workspace**: "here" means the current working directory; default to all workspaces.
- **Content**: defer filtering on conversation content to step 2.

The following session file paths are best-effort and can change between releases. If a path is missing or looks different, check the linked doc.

**Claude Code** ([docs](https://code.claude.com/docs/en/claude-directory#application-data))
- Session file: `~/.claude/projects/<project>/<session_uuid>.jsonl`. `<project>` is the working directory with every non-alphanumeric character replaced by `-`. Pass `<project>` to tools as a full path, since a leading `-` parses as an option.
- Some records include activity times in their `timestamp` field.
- Ignore `*.orphaned-*.jsonl`, `*.jsonl.superseded-*`, and `<session_uuid>/subagents/*.jsonl`.

**Strands CLI** ([docs](https://github.com/strands-agents/harness-sdk/blob/main/strands-cli/README.md))
- Session file: `<directory>/<session_id>/scopes/*/*/snapshots/snapshot_latest.json`. Its `createdAt` and mtime show only the last activity.
- The oldest `snapshots/immutable_history/snapshot_<uuid7>.json` shows the first activity. When that directory is empty, treat the first activity as unknown.
- To find session directories, read `roots[]` in `~/.strands/cli/session-roots.json`. Each entry has a `directory` (where sessions live) and a `workspace` (the repo it ran in). The catalog is best-effort and can miss entries, so also check `<workspace>/.agent/sessions`.

**Kiro CLI** ([docs](https://kiro.dev/docs/cli/chat/session-management/))
- Session directory: `~/.kiro/sessions/<workspace_hash>/sess_<session_uuid>/`, holding the conversation in `messages.jsonl` and metadata in `session.json`. The metadata includes `workspacePaths` (on newer versions), `title`, `createdAt`, and `lastModifiedAt`.
- To search one workspace, compute its hash instead of scanning every directory:
  ```bash
  printf '%s' "<absolute_workspace_path>" | openssl dgst -sha256 -r | cut -c1-16
  ```
- Sessions started outside a workspace live under `~/.kiro/sessions/_global/`.
- Some versions also write a flat store: `~/.kiro/sessions/cli/<session_uuid>.jsonl` with a `<session_uuid>.json` metadata sidecar.

**Other harnesses**: find the harness's session store (its docs, or recently modified `*.json` / `*.jsonl` files under its home directory) and apply the same prompt criteria.

List the matching session file paths, grouped by harness. If nothing matches, say which locations you searched and what criteria you applied and any near misses, then ask the user whether to widen the search.

### 2. Read sessions

For each session file from step 1, use `jq` to extract the user inputs and assistant responses, in order, as `{role, text}`. Skip tool calls, tool results, reasoning, and harness bookkeeping. Session files can be large, so stream them through `jq` instead of reading them whole. Derive path names with shell parameter expansion (`${f##*/}`) instead of `basename`.

If the known fields below don't fit, print a condensed view of the file's shape:

```bash
jq -c '[paths(scalars) | map(if type == "number" then "[]" else . end) | join(".")] | unique' <file> | sort | uniq -c | sort -rn | head -20
```

From it, find the field that marks each record's type (user, assistant, tool, ...) and the field holding its text, then filter on them: `jq -c 'select(<is user or assistant text>) | {role: <role>, text: <text>}' <file>`. Known fields, best-effort:

- **Claude Code**: user is `type == "user"` and `origin.kind == "human"` (without `origin`, skip `isMeta`, `tool_result`-only, interrupt, and `<task-notification>` lines). Assistant is `type == "assistant"`. The text is in `message.content`, a string or `text` blocks. Slash command input is in `<command-args>`.
- **Strands CLI**: `data.messages[]` by `role`. The text is in `content[].text`; skip messages whose `content[]` has no `text` block (`toolUse`/`toolResult`-only messages are tool traffic, not turns).
- **Kiro CLI**: user is `payload.type == "user"`; assistant is `payload.type == "assistant"` with `payload.operationType == "Say"`. The text is in `payload.content`. This format is for `sess_*/messages.jsonl` files. The flat `cli/<session_uuid>.jsonl` store uses a different record shape; use the shape-discovery command above for it.

If the user gave content criteria (ex. a conversation topic), keep only the sessions that match them. Match conversation criteria against the extracted turns. Track the user inputs, assistant messages, conversation id, session timestamp, and source harness for each session file.

## Output

Stop after step 2. Report the output of the latest step. Converting these sessions into an experiment is not part of this skill yet, so don't write experiment code; ask the user what they want to do with the results you found.
