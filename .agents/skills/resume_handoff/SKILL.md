---
description: Resume work from a saved handoff document, validating its state against the current codebase before continuing. Use when resuming work from a saved handoff after a context clear or in a new session (path, session name, or GitHub issue).
disable-model-invocation: true
---

# Resume work from a handoff document

Resume work from a handoff document through an interactive process. Handoffs (written by `create_handoff`) carry context, learnings, and next steps from a previous session. Validate that the handoff still matches the codebase, then continue — never assume the snapshot is current.

## Initial Response

When this command is invoked:

1. **If the path to a handoff document was provided**:
   - If a handoff document path was provided as a parameter, skip the default message
   - Immediately read the handoff document FULLY
   - Immediately read any research or plan documents that it links to under `thoughts/shared/plans`. do NOT use a sub-agent to read these critical files.
   - Begin the analysis process by ingesting relevant context from the handoff document, reading additional files it mentions
   - Then propose a course of action to the user and confirm, or ask for clarification on direction.

2. **If a session name or GitHub issue (like `rbac-refactor` or `#1372`) was provided**:
   - locate the most recent handoff document for that work stream. Handoffs are located in `thoughts/shared/handoffs/{session-name}/` where `{session-name}` matches the active ledger name (kebab-case, e.g. `rbac-refactor`, `export-contract`). If a GitHub issue number was given, use the session-name folder whose handoffs reference that issue. **List this directory's contents.**
   - There may be zero, one or multiple files in the directory.
   - **If there are zero files in the directory, or the directory does not exist**: tell the user: "I'm sorry, I can't seem to find that handoff document. Can you please provide me with a path to it?"
   - **If there is only one file in the directory**: proceed with that handoff
   - **If there are multiple files in the directory**: using the date and time specified in the file name (it will be in the format `YYYY-MM-DD_HH-MM-SS` in 24-hour time format, e.g. `2026-06-20_14-30-00_description.md`), proceed with the _most recent_ handoff document.
   - Immediately read the handoff document FULLY
   - Immediately read any research or plan documents that it links to under `thoughts/shared/plans`; do NOT use a sub-agent to read these critical files.
   - Begin the analysis process by ingesting relevant context from the handoff document, reading additional files it mentions
   - Then propose a course of action to the user and confirm, or ask for clarification on direction.

3. **If no parameters provided**, respond with:
```
I'll help you resume work from a handoff document. Let me find the available handoffs.

Which handoff would you like to resume from?

Tip: You can invoke this command directly with a handoff path: `/resume_handoff thoughts/shared/handoffs/{session-name}/YYYY-MM-DD_HH-MM-SS_description.md`

or using a session name (or related GitHub issue) to resume from the most recent handoff for that work stream: `/resume_handoff rbac-refactor`
```

Then wait for the user's input.

## Process Steps

### Step 1: Read and Analyze Handoff

1. **Read handoff document completely**:
   - Use the Read tool WITHOUT limit/offset parameters
   - Extract all sections:
     - Task(s) and their statuses
     - Recent changes
     - Learnings
     - Artifacts
     - Action items and next steps
     - Other notes

2. **Spawn focused research tasks**:
   Based on the handoff content, spawn parallel research tasks to verify current state:

   ```
   Task 1 - Gather artifact context:
   Read all artifacts mentioned in the handoff.
   1. Read feature documents listed in "Artifacts"
   2. Read implementation plans referenced
   3. Read any research documents mentioned
   4. Extract key requirements and decisions
   Use tools: Read
   Return: Summary of artifact contents and key decisions
   ```

3. **Wait for ALL sub-tasks to complete** before proceeding

4. **Read critical files identified**:
   - Read files from "Learnings" section completely
   - Read files from "Recent changes" to understand modifications
   - Read any new related files discovered during research

### Step 2: Synthesize and Present Analysis

1. **Verify the handoff against the current codebase**, since the snapshot may be stale:
   - For every item in "Recent changes", confirm it is still present/missing/modified.
   - For every "Learnings" file:line reference, confirm it is still valid or note what changed.
   - Match the situation to the divergence type (clean / diverged / incomplete / stale)
     and adapt the plan accordingly — see
     `reference/synthesis-and-reconciliation.md`.

2. **Present the analysis** using the template in
   `reference/synthesis-and-reconciliation.md` (original tasks vs verification, validated
   learnings, recent-change status, artifacts, recommended next actions, potential issues).

3. **Get confirmation** before proceeding.

### Step 3: Create Action Plan

1. **Use TodoWrite to create task list**:
   - Convert action items from handoff into todos
   - Add any new tasks discovered during analysis
   - Prioritize based on dependencies and handoff guidance

2. **Present the plan**:
   ```
   I've created a task list based on the handoff and current analysis:

   [Show todo list]

   Ready to begin with the first task: [task description]?
   ```

### Step 4: Begin Implementation

1. **Start with the first approved task**
2. **Reference learnings from handoff** throughout implementation
3. **Apply patterns and approaches documented** in the handoff, and avoid the mistakes its "Learnings" / "What Failed" sections call out
4. **Update progress** as tasks are completed, and reference the handoff path in commits
