---
id: focusgroup-5nq
status: closed
deps: []
links: []
created: 2026-01-06T14:32:48.351240076-05:00
type: task
priority: 2
---
# Document rationale for CLI-only agent architecture

Add documentation explaining why focusgroup only supports CLI-based agents:

1. We want feedback from the ACTUAL agents, not approximations
2. Many agent implementations are closed-source - we can't know exactly how their harnesses are configured (system prompts, tool configurations, safety layers, etc.)
3. Since AI agents are the primary customers of the tools being evaluated, we want THEIR authentic feedback - not a simulation we cobbled together using agent SDKs
4. CLI tools represent the most accurate form of each agent as its provider intends it to operate

This philosophy should be documented prominently, perhaps in providers.md or a dedicated 'Why CLI-only?' section.
