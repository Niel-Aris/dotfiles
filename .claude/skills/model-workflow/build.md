# Build mode: plain agentic coding, light documentation

Use this for areas the user doesn't want to learn right now (CI, configs, boilerplate). Write the code normally. Documentation is limited to:

- Journal lines as usual (`built`, `decided`).
- An ADR in `.op/Decisions/` for each real architectural fork.
- A Pattern note only when you introduce a named algorithm the user will want to reference later. Skip the Batch notes and the PRIMM checks.
- Before ending the session, put a short **For other agents** summary on your Card, via a checkpoint.

If the user starts asking how something works, offer to switch to Model mode for that part (`/op mode model`).
