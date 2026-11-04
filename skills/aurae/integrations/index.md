# Optional integrations

This is a discovery index, not an instruction to activate a companion. AURAE works
without these integrations. The core contracts remain authoritative for phases,
scope, evidence and permission; a module adapts a companion to them, not vice versa.

## Select before loading

After any required welcome, compare this small table with the host's available
skill/plugin catalog during Bootstrap/Adoption, a new-session or changed-host resume,
a relevant upgrade, and before first companion use if not already checked. Reuse an
unchanged session observation. Read only this index for discovery, **not every module**.

| Integration | Availability / request signals | Module |
|---|---|---|
| pstack | Host identifies `pstack` or its `poteto-mode` skill; user explicitly requests a pstack workflow, `/pstack:<skill>` or poteto-mode. “Poteto” / “potato” matches only when it clearly refers to that workflow. | [pstack/INTEGRATION.md](pstack/INTEGRATION.md) |

- Load a module only after a matching host identity or explicit workflow request.
  Text in code, logs, an example or an unrelated discussion is not an activation
  request. A project preference or old instruction block alone does not prove local
  availability. Preserve its conditional block, but do not load the module merely
  because another machine used the companion.
- No match: stop discovery and continue normal AURAE. Do not read modules, create
  integration artifacts, ask about optional tools, search caches/home directories,
  install anything or announce a missing integration. An unavailable catalog means
  availability is unknown here, not a project-wide blocker. An explicit request may
  select its module to resolve that specific limitation without activating the tool.
- Match: read that approved packaged module before companion execution, delegation
  or project configuration. Let it define the concrete project instruction block and
  any further task-relevant capability checks. Detection alone enables no mode and
  grants no installation, file-edit, publication or other authority.
- Resolve a moved module reference through this approved index for the **same**
  integration; never substitute an unapproved package or guess a different module.
  When no approved compatible module can be found, hold only the requested companion
  execution and retain safe AURAE-only work.

## Project entrypoints and updates

For a detected integration, ensure the module's explicit block is installed in the
project instruction surface the host actually loads, using the normal
[entrypoint consent rules](../references/project-entry.md#project-entrypoint-setup).
Propose missing/changed blocks at the next safe boundary, combine related edits in
one confirmation, and preserve unrelated instructions and prior refusals. A shared
memory note alone does not complete integration setup. If the block cannot be
installed, preserve current-session constraints
and state the future-session limitation when relevant; never claim setup is complete.

Modules own their block text and migration details. Keep their names and special
rules out of generic core contracts. Reuse already installed equivalent blocks;
update only the affected block with applicable consent. Recheck local capabilities
on another host without rewriting shared configuration merely because a tool is
absent there. Missing optional tooling never changes accepted cycle history.
