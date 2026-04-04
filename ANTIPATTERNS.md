# Antipatterns

This file records repeated implementation mistakes so they can be avoided in future work.

Entries here are patterns Copilot has repeated before. Treat each entry as a strong hint about what not to do again.

## Do Not Regress Overlay Controls To Top Toolbar

- Do not revert from the left explorer-style overlay panel in the dock back to top-toolbar overlay toggles.
- Preserve grouped overlay controls in the left dock unless the user explicitly requests a UI change.

## Do Not Start With Incorrect Initial Map View

- Do not start with a too-small initial map view.
- Startup map behavior should match the Full Map experience after layout initialization.

## Do Not Skip Startup In-Memory Scraper Refresh

- On startup, run the same in-memory scraper logic used at the end of a detected turn.
- Startup and end-turn refresh paths must stay behaviorally aligned for runtime overlay data.
