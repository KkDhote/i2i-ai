# I2I — Intelligence to Impact: narration script

Delivery: deep male voice, clear and calm, warm professional tone. Aim for about 140–150 words per minute, with brief pauses at scene changes. Speak “I two I,” “A I,” “Fast A P I,” and “J S O N” as written. Do not read headings, bullet lines or source IDs aloud.

Sixteen scenes; 1320 spoken words. Approximately 9.1 minutes of narration before scene pauses. Actual duration depends on speech synthesis and pacing.

## Scene 01 — Your goal. Your workspace.

Chapter: Introduction. Visual: intro. Sources: project source / proposal.

Imagine opening your work dashboard and saying, I need to prepare for tomorrow's client meeting. Instead of sending you through menus, the page brings the client, conversations, issues and talking points into view. That is the idea behind I two I, Intelligence to Impact: an adaptive A I workspace built for HackWave three point zero. This video explains the problem, our proposed solution, the working prototype, its research foundations and the next steps.

## Scene 02 — Why should work start with menus?

Chapter: Problem statement. Visual: problem. Sources: project source / proposal.

Modern applications organize information into fixed dashboards, menus, filters and workflows. But people's goals change. Preparing a meeting requires different evidence from investigating a usage drop or following up on overdue work. The user must translate a real need into a sequence of interface operations, find scattered information and assemble the context. Our problem statement challenges that pattern: can an interface adapt to the user's goal, instead of making the user adapt to the interface?

## Scene 03 — Turn intent into useful tools

Chapter: Aim and proposed solution. Visual: aim. Sources: 1, 3.

Our aim is to bring relevant information and useful actions together in a coherent, accessible workspace. The proposed solution has a simple loop: understand the goal, clarify uncertainty, select available components, arrange them, and explain the changes. It must remain usable when the goal changes again. Success means more than generating a page of text. The interface should give the user working tools, while preserving familiar controls, consistent design and the ability to correct the system.

## Scene 04 — Start familiar. Change with purpose.

Chapter: The working workspace. Visual: workspace. Sources: project source / proposal.

I two I begins with a general dashboard. The left panel holds the workspace goal, suggested scenarios, refinements and recent changes. The main canvas contains overview metrics, a performance card, the assistant and team tasks. You can enter your own goal or choose a demo. The page then selects and rearranges cards around that focus. Search, task drafts and assistant state stay with you. This is one continuing workspace, rather than a separate page for every task.

## Scene 05 — Walk into the meeting prepared

Chapter: Demo: client meeting. Visual: meeting. Sources: project source / proposal.

First, prepare a client meeting. The workspace brings together a client overview, recent conversations, open issues, product usage, an agenda and suggested next actions. Our demonstration account, Northstar Labs, has onboarding concerns and slower exports. Those details are explicitly sample data. The aim is to support a practical conversation: what does the client need, what evidence do we have, and who owns the follow-up? Suggested actions open the real task form so an idea can become assigned work.

## Scene 06 — Investigate the drop, not the guess

Chapter: Demo: product investigation. Visual: usage. Sources: project source / proposal.

Next, investigate why active users dropped. Usage trends and affected segments move into focus, alongside relevant issues, conversations and actions. The sample chart shows a drop following a release. That sequence is a clue, not proof of causation. A responsible investigation compares cohorts, checks onboarding and export errors, and validates hypotheses before proposing a fix. I two I organizes the evidence available in the demo; it does not claim to have discovered a real customer's root cause.

## Scene 07 — Bring overdue work into focus

Chapter: Demo: project follow-up. Visual: overdue. Sources: project source / proposal.

The third scenario is overdue project work. Incomplete tasks past their due dates appear together with task metrics, sample blockers and suggested next steps. Task records include an owner, team, deadline and status. You can search, create a task and update its status through the backend. Completed tasks are excluded from overdue work. The current prototype recognizes overdue dates, but it does not yet calculate the dynamic priority score discussed later. Its sample issue badges are not computed task priorities.

## Scene 08 — AI plans. Validated components render.

Chapter: Architecture. Visual: architecture. Sources: 6.

The architecture separates three responsibilities. React renders the workspace and keeps interaction state. Fast A P I handles tasks and validates layout plans. Gemini three point five Flash Lite interprets intent and returns structured J S O N describing available cards, widths and reasons. The backend checks allowed identifiers, supported widths, duplicate cards and nonempty layouts. Google's documentation makes an important distinction: structured output can constrain format, but cannot guarantee meaningful values. Validation and human correction therefore remain essential.

## Scene 09 — A controlled catalog, useful fallback

Chapter: Component selection and resilience. Visual: catalog. Sources: 6.

The model chooses from thirteen predefined cards, including tasks, client context, usage, cohorts, blockers and the assistant. It does not generate executable interface code. This keeps the design and available actions under application control. Follow-up requests can add or remove cards while retaining the current goal. If Gemini is unavailable or a response fails validation, explicit demo rules provide a fallback. Successful plans can be cached for five minutes, while task data is fetched separately.

## Scene 10 — Make the adaptation understandable

Chapter: User control and explanation. Visual: control. Sources: 1, 3.

An adaptive interface should explain itself. Each card has a reason for appearing, and recent changes show what was added, removed or retained. When a request is ambiguous, the system can ask which goal should lead. You can refine the view or return to the overview. We also keep newer instructions in charge: older layout responses cannot overwrite a more recent request. These controls make adaptation inspectable and correctable, rather than something the user must simply accept.

## Scene 11 — Continuous motion, preserved work

Chapter: Smooth transition. Visual: motion. Sources: 5, 7.

Smoothness comes from browser animation, not from asking the language model to animate. The frontend measures card positions before and after a change, then animates between them with native Web Animations. Retained cards move and resize over roughly four hundred and eighty milliseconds; new cards enter and removed cards fade. That duration is separate from A I response time, which varies. Interrupted changes begin from current visual positions. Reduced-motion preferences disable movement effects, because accessible control matters as much as visual polish.

## Scene 12 — Assistance that stays with your work

Chapter: Assistant and visual design. Visual: chat. Sources: 3.

The I two I A I assistant answers questions using current task context and clearly identified demo information. Suggested questions send immediately. Drafts, replies and pending requests survive layout changes, and the assistant can be brought back into any view. Two themes support the same workspace: the present green design and a dark grey design with red, yellow, green and light blue accents. Theme selection is saved in the browser without resetting the goal or ongoing work.

## Scene 13 — Adaptation needs evidence and control

Chapter: Research: adaptive interaction. Visual: research. Sources: 1, 2.

Our literature review offers both inspiration and caution. In nineteen ninety-nine, Eric Horvitz described mixed-initiative interfaces that combine automation with direct human control, including attention to uncertain goals and opportunities for correction. In two thousand four, Leah Findlater and Joanna McGrenere compared static, adaptive and user-adaptable menus. In that study, static menus were faster than adaptive menus, and most participants preferred user-adaptable menus. These findings do not directly predict our dashboard's performance. They explain why we preserve a stable shell, retain state and give users explicit control over changes.

## Scene 14 — A human-centered research direction

Chapter: Research: explainability and evaluation. Visual: research. Sources: 3, 4, 5.

Amershi and colleagues' twenty nineteen human–A I interaction guidelines emphasize relevant context, easy correction, clarification and understandable explanations. These principles inform our card reasons and refinement controls. W three C guidance supports disabling nonessential interaction motion, which informs reduced-motion behavior. For evaluation, Hart and Staveland's NASA Task Load Index provides an established way to assess perceived workload, including mental demand, effort and frustration. These are external research foundations. I two I has not yet completed a user study or demonstrated a measured productivity improvement.

## Scene 15 — DTPS: an explainable priority proposal

Chapter: Proposed task-priority research. Visual: priority. Sources: project source / proposal.

A proposed next feature is the Dynamic Task Priority Score. It combines zero point three five times urgency, zero point three zero times business impact, zero point two zero times dependency importance, and zero point one five times delay risk. Each factor runs from zero to one hundred. For a quarterly review, values of seventy-five, eighty, sixty and seventy produce seventy-two point seven five: high priority. For a productivity analysis, thirty, eighty, twenty and thirty-five produce forty-three point seven five: medium priority. Proposed tiers begin at forty, sixty and eighty. Confirmed critical impact or blockers could override the average. Python would calculate scores; Gemini could suggest uncertain estimates for user confirmation and explain them. Missing deadlines or dependencies would stay explicit. The weights and thresholds require validation.

## Scene 16 — From prototype to tested impact

Chapter: Uniqueness, limitations and next steps. Visual: closing. Sources: 2, 4.

I two I's distinction is the combination: natural-language intent, one adaptive canvas, reusable tools, explanations, preserved state and controlled motion. We are not claiming a world-first invention. Today, business context is sample data and tasks reset when the backend restarts. Next steps include persistent storage, real integrations and controlled comparison with a fixed dashboard using equivalent tasks. We should measure completion accuracy, time, navigation effort, perceived workload and unwanted changes, including failures and reduced motion. The vision is clear: state the work you need to do, and let the workspace help you do it.

Source IDs 1–7 correspond to the numbered primary references in research-notes.md. The project facts are verified against the current repository. DTPS, persistent storage, external business integrations and usability evaluation are explicitly future work.
