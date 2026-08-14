---
id: focusgroup-spn
status: closed
deps: []
links: []
created: 2026-01-06T12:38:32.858026516-05:00
type: feature
priority: 1
---
# Document explore mode security implications

SECURITY: Explore mode requires relaxed sandbox controls (codex uses danger-full-access, claude uses reduced permissions). Users should be warned: 1) What permissions are granted, 2) What agents can access (filesystem, network, etc.), 3) Recommendation to run in isolated environments, 4) Consider --sandbox-level flag for granular control.
