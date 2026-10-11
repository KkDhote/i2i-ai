# I2I by AI — Intelligence to Impact

An adaptive AI workspace built for HackWave 3.0. Describe a goal and the same page selects and rearranges useful cards around it.

## Merged workspace
- `update-2` is the main template: intent controls on the left, adaptive canvas on the right.
- Gemini 3.5 Flash-Lite returns validated JSON plans from a fixed catalog of cards.
- Follow-up requests add or remove cards without replacing the whole workspace.
- Cards move and resize with native browser FLIP animations; new cards enter gradually and removed cards fade out. Rapid requests cancel older responses and start from current visual positions.
- Assistant drafts, replies and pending requests survive layout changes. Suggested questions send immediately; **Ask I2I AI** restores the assistant in any goal view. Task drafts and search also survive layout changes. Reduced-motion preferences are respected.
- The original task creation, status updates, search, overview metrics and Gemini assistant are integrated into reusable cards.
- Per-card reasons and a short change history explain each adaptation.
- The **Green / Dark grey** control switches between the present green design and a charcoal theme combining red, yellow, green and light-blue accents. Theme preference stays on this browser and does not reset the workspace.
- Missing or unavailable Gemini falls back to explicit demo rules. Repeated successful plans are cached for five minutes; task data is fetched separately.

## Run locally

Start the API in one terminal:

```bash
cd backend
# Use your existing virtual environment, or create one and install requirements.txt.
.venv-new/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Set `GEMINI_API_KEY` in `backend/.env` for real AI planning. `backend/.env.example` documents the optional model setting. With no key, the three demo goals and task actions still work.

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. Its `/api` proxy targets port 8000 by default. Set `VITE_API_PROXY` to use a different development backend. For production, route `/api` to FastAPI on the same origin, or set `VITE_API_URL` and configure CORS for the deployed frontend.

## Demo

Start on the general dashboard, then enter:

1. "Prepare for tomorrow's client meeting"
2. "Investigate why active users dropped"
3. "Review overdue project work"

Try "Also show overdue tasks", "Also show open issues", or "Remove next actions". Use **Back to dashboard** to reset. Suggested next actions open the real task form rather than pretending to execute a workflow.

## Data and integration limits

Task cards and metrics use the API. Tasks and status updates persist in SQLite at `backend/workspace.sqlite3`. The task form supports description, assignee, due date, and Low/Medium/High/Critical priority; the API accepts both `assignee` and the existing `owner` field. Existing databases gain the priority column automatically with Medium as the default. The 15 initial tasks are demonstration seeds, inserted only when the database is first created. Client details, conversations, usage charts and blockers are explicitly labeled sample data; they are not connected to external business systems.

The supplied `update-2` directory contained only `App.jsx`, `server.js` and `llm.js`; its imported registry, catalog, rules, store, API helper and styles were absent. The missing pieces have been reconstructed in `frontend/src/Widgets.jsx` and `backend/adaptive.py`, reusing the original FastAPI/Gemini backend rather than requiring a second Node server, MongoDB or an Anthropic key. The original reference files are preserved in `update-2`.

The exact `update-2` colors could not be recovered without its stylesheet. The green palette and the requested dark grey multicolor theme are defined in `frontend/src/App.css`.

## Checks

```bash
cd backend
.venv-new/Scripts/python.exe -m unittest test_adaptive -v
cd ../frontend
npm run lint
npm run build
```

Backend checks cover all demo intents, clarification, refinements, validated model responses, failure fallback, caching and live task APIs without making paid Gemini calls.

## Project
Built for Hackwave 3.0.

### P0 goal workflow

Select a meeting, usage, or overdue-work goal to create a persistent three-step scenario plan. The Live Goal Graph connects the suggested steps, shows their evidence requirements, and links each step to an existing or newly created task. Task status can be changed directly in the graph.

Proactive Gap Radar checks missing evidence, unlinked work, incomplete tasks, unassigned owners, and missing or overdue deadlines after each saved change. Add a source reference and findings to a step to close its evidence gap. A step counts as complete only when its linked task is completed, evidence has been supplied, and preceding steps are complete. Evidence notes are user-provided and are not independently verified; the planner uses scenario templates rather than autonomous research.

Goals, layouts, task links, and evidence notes are saved in SQLite. Reload resumes the active goal; choosing the same scenario prompt resumes its previous plan. Existing demo client and usage data stays labeled Sample and does not automatically satisfy evidence requirements.
### P1 reasoning and control

Sourced observations store a goal step, source reference, metric (including cohort/unit), comparison period, value and observation date. The workspace cites record IDs in next-action reasoning and reports. Contradiction detection compares different values under the same metric and period; it is a deterministic check, not semantic verification of arbitrary documents. Withdraw an incorrect record to resolve the conflict while preserving the decision journal. Sources older than 30 days receive freshness alerts. Same-named constraints with different values are flagged, and can be withdrawn. Unfinished goals with no recorded activity for 3 days are marked stalled.

Tasks rank by critical-impact/blocker override, then DTPS, with completed work last. The formula is `0.35U + 0.30I + 0.20D + 0.15B`. Urgency comes from the saved deadline; impact, confirmed dependency score, and delay risk are editable in the task table. Defaults (50, 0, 35) are assumptions, not AI-inferred facts. Manually assigned priority labels are shown separately from the computed score.

AI layout changes now have a review preview before application. Cards can be pinned and moved manually; undo restores the last layout (up to 10 changes in the current browser session). The last card edited is protected until released. Theme, pins and the 4/6/all attention preference persist in this browser. A progress-stage control proposes an updated card order for review.

Outcome Mode prepares editable reports and action outlines with cited evidence, unresolved gaps and next steps. Approve/reject decisions persist in SQLite. Email/calendar/project previews record the intended destination but remain local: external integrations are not connected, and no endpoint sends them or performs external actions. Approval does not imply execution. Drafts describe the evidence snapshot at preparation time; prepare a new preview after evidence changes.

Validation: `python -m unittest test_adaptive -v` in backend and `node scripts/test-layout.mjs` in frontend. Frontend lint/build remain available through the existing npm scripts.
