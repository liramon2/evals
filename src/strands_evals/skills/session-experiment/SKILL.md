---
name: session-experiment
description: Use when the user wants to turn past local agent conversations (Claude Code, Kiro CLI, Strands CLI, or any other harness) into strands-evals experiments. Locates the session files on the local filesystem that match the user's criteria and lists every matching session file. Skip for traces stored in trace providers (CloudWatch, Langfuse, OpenSearch).
version: 0.1.0
---

# session-experiment

Converts recorded local agent sessions into a strands-evals experiment.

## Steps

### 1. Locate sessions

Find every session file on the local filesystem that matches the user's criteria. Don't open whole files to do it: session files can be large, so read metadata, use `ls -t`, `find -newermt`, `grep`, `jq`, or targeted reads. Read the criteria from the prompt:

- **Harness**: search only the sessions for the agent harnesses the user names. If they name none, search all of them.
- **Date range**: resolve relative dates ("yesterday", "this week") against today's date in the user's local time zone. Timestamps in session files are UTC (`...Z`), so convert before comparing. A session matches if any of its activity falls in the range, not only its start.
- **Workspace**: "this repo" or "here" means the current working directory. Match a named project against workspace paths. With no workspace given, search all workspaces.

The following session file paths are best-effort and can change between releases. If a path is missing or looks different, check the linked doc.

**Claude Code** ([docs](https://code.claude.com/docs/en/claude-directory#application-data))
- Session file: `~/.claude/projects/<project>/<session_uuid>.jsonl`. `<project>` is the working directory with every non-alphanumeric character replaced by `-`. For example, `/Users/me/my.repo` becomes `-Users-me-my-repo`.
- Ignore `*.orphaned-*.jsonl`, `*.jsonl.superseded-*`, and `<session_uuid>/subagents/*.jsonl`.

**Strands CLI** ([docs](https://github.com/strands-agents/harness-sdk/blob/main/strands-cli/README.md))
- Session file: `<directory>/<session_id>/scopes/*/*/snapshots/snapshot_latest.json`. Its `createdAt` and mtime show only the last activity.
- The oldest `snapshots/immutable_history/snapshot_<uuid7>.json` shows the first activity. When that directory is empty, treat the first activity as unknown.
- To find session directories, read `roots[]` in `~/.strands/cli/session-roots.json`. Each entry has a `directory` (where sessions live) and a `workspace` (the repo it ran in). The catalog is best-effort and can miss entries, so also check `<workspace>/.agent/sessions`.

**Kiro CLI** ([docs](https://kiro.dev/docs/cli/chat/session-management/))
- Kiro home is `$KIRO_HOME` if set, otherwise `~/.kiro`. The layout depends on the kiro-cli version, so check both stores below.
- Session directory: `~/.kiro/sessions/<workspace_hash>/sess_<session_uuid>/`, holding the conversation in `messages.jsonl` and metadata in `session.json`. The metadata includes `workspacePaths` (on newer versions), `title`, `createdAt`, and `lastModifiedAt`.
- To search one workspace, compute its hash instead of scanning every directory:
  ```bash
  printf '%s' "<absolute_workspace_path>" | openssl dgst -sha256 | awk '{print substr($2,1,16)}'
  ```
- Sessions started outside a workspace live under `~/.kiro/sessions/_global/`.
- Some versions also write a flat store: `~/.kiro/sessions/cli/<session_uuid>.jsonl` with a `<session_uuid>.json` metadata sidecar.

**Other harnesses**: find the harness's session store (its docs, or recently modified `*.json` / `*.jsonl` files under its home directory) and apply the same prompt criteria.

## Output

List every matching session file, grouped by harness, with its workspace, its first and last activity time in local time, and the first user prompt when cheap to read. If nothing matches, say which locations you searched and what criteria you applied, then ask the user whether to widen the search.

Stop after listing. Converting these sessions into an experiment is not part of this skill yet, so don't write experiment code; ask the user what they want to do with the sessions you found.
