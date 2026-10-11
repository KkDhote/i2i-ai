# I2I video: research and claim-verification brief

Prepared 11 October 2026 from the project source and primary publications. This is a literature-informed explanation of a hackathon prototype, not evidence of a completed I2I user study. Use original diagrams and paraphrased findings in the video; link the sources in the description and show a short reference card.

## Project facts the video can demonstrate

The problem statement asks for an interface that follows the user's current goal rather than requiring navigation through fixed dashboards, menus, filters and workflows. Its aim is to select useful information and tools, arrange them coherently on one page, adapt when the goal changes, and explain why content appears.

I2I currently implements a React workspace with intent controls on the left and an adaptive canvas on the right. A FastAPI backend asks Gemini 3.5 Flash-Lite for a structured plan. The model selects from 13 predefined cards; it does not generate executable interface code. Plans are checked using Pydantic, including allowed card identifiers, grid widths, unique cards and a nonempty layout. Ambiguous goals can prompt clarification. Follow-ups can add or remove information without replacing the whole view. Explicit demo rules provide a fallback, and successful plans can be cached for five minutes.

Three scenarios are implemented: prepare a client meeting, investigate a usage drop, and review overdue project work. Task creation, search, status updates, due dates, counts and the assistant use the API. Client context, conversations, usage numbers, cohorts and blockers are labeled sample data. Tasks are stored in memory and reset when the backend restarts; there is no production business-system integration or persistent database yet.

The frontend preserves task drafts, search and assistant state while cards change. Native browser animations move and resize retained cards, introduce new cards and fade removed cards. Retained-card motion is configured for 480 milliseconds; this is an animation duration, not a measured AI response time. Older layout responses are ignored after a newer request. Reduced-motion preferences are respected. Both the green theme and the dark-grey theme with red, yellow, green and light-blue accents are implemented.

## Seven primary research and technical references

### 1. Mixed initiative and uncertainty

**Eric Horvitz, 1999 — “Principles of Mixed-Initiative User Interfaces,” CHI '99.** [Microsoft Research publication](https://www.microsoft.com/en-us/research/publication/principles-mixed-initiative-user-interfaces/), [primary paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf).

**Supported finding:** Horvitz describes combining automation with direct user manipulation. The paper identifies mistaken guesses about goals, poor timing, inadequate consideration of automation costs and insufficient opportunities for people to guide or refine assistance as design problems. It explicitly treats uncertainty about user intentions as important.

**Application/inference:** I2I's explicit goal entry, clarification, refinement controls and dashboard reset fit this design direction. They do not prove that I2I has solved uncertainty or implemented Horvitz's decision-theoretic model.

**Video-safe wording:** “Our approach combines AI assistance with human direction. The user states the goal and can refine the result.”

### 2. Adaptation can create costs

**Leah Findlater and Joanna McGrenere, 2004 — “A Comparison of Static, Adaptive, and Adaptable Menus,” CHI 2004.** [University of British Columbia publication page](https://www.cs.ubc.ca/labs/imager/tr/2004/findlater04menus/), [primary paper](https://www.cs.ubc.ca/labs/edapt/papers/findlater2004.pdf).

**Supported finding:** A controlled study of 27 participants compared three split-menu designs. The static menu was faster than the adaptive menu; the user-adaptable menu was faster under certain conditions. Most participants preferred the adaptable menu. This is evidence about those menu conditions, not a universal judgment about adaptive dashboards.

**Application/inference:** Rearrangement deserves evaluation. I2I preserves a stable shell, retains working state and lets users request refinements; these are design responses to potential disruption, not demonstrated performance gains.

**Video-safe wording:** “Research reminds us that changing an interface is not automatically helpful. We therefore keep people in control and preserve continuity.”

### 3. Human–AI interaction guidelines

**Saleema Amershi, Dan Weld, Mihaela Vorvoreanu, Adam Fourney, Besmira Nushi, Penny Collisson, Jina Suh, Shamsi Iqbal, Paul N. Bennett, Kori Inkpen, Jaime Teevan, Ruth Kikin-Gil and Eric Horvitz, 2019 — “Guidelines for Human-AI Interaction,” CHI 2019.** [Microsoft Research](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/), [primary paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/Guidelines-for-Human-AI-Interaction-camera-ready.pdf).

**Supported finding:** The paper proposes 18 guidelines and reports several evaluation rounds, including work with 49 design practitioners evaluating 20 AI-infused products. Relevant guidance concerns task context, easy invocation and correction, disambiguation, explanations and remembering recent interaction.

**Application/inference:** Goal-specific cards, per-card reasons, clarification and retained assistant drafts align with these guidelines. The publication's participant counts belong to the researchers' study, not to I2I.

**Video-safe wording:** “We use established human–AI design principles: show relevant context, make correction easy, and explain the adaptation.”

### 4. Workload evaluation

**Sandra G. Hart and Lowell E. Staveland, 1988 — “Development of NASA-TLX (Task Load Index): Results of Empirical and Theoretical Research,” in Human Mental Workload.** [NASA-hosted primary chapter](https://humansystems.arc.nasa.gov/groups/tlx/downloads/Hart_Staveland_ORIGINAL_1.pdf), [official NASA instrument overview](https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/).

**Supported finding:** NASA-TLX assesses subjective workload through mental demand, physical demand, temporal demand, performance, effort and frustration. It offers an established instrument for evaluating perceived workload; it is not a measure of task priority.

**Application/inference:** A future I2I usability study can combine a correctly administered workload questionnaire with completion times and task accuracy. This would test the project's aim of reducing navigation effort without assuming that fewer clicks equal better work.

**Video-safe wording:** “Our evaluation plan will measure task outcomes and perceived workload, rather than claiming productivity improvements from appearance alone.”

### 5. Accessible motion

**W3C Accessibility Guidelines Working Group — WCAG 2.2 Understanding Success Criterion 2.3.3, “Animation from Interactions” (Level AAA), living guidance.** [W3C guidance](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html).

**Supported finding:** Nonessential motion triggered by interaction should be disableable. W3C explains that motion can distract users or trigger vestibular symptoms, and describes respecting operating-system or browser reduced-motion preferences as an approach.

**Application/inference:** I2I checks `prefers-reduced-motion` and cancels moving-card effects when that preference is active. This addresses one motion-related concern. It does not establish complete WCAG conformance; contrast, focus, keyboard use and screen-reader behavior still require auditing.

**Video-safe wording:** “Smooth motion is optional: users who prefer reduced motion receive the layout change without those movement effects.”

### 6. Structured model output and validation

**Google — “Structured outputs,” Gemini Generate Content API documentation, updated 9 October 2026.** [Official documentation](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).

**Supported finding:** Gemini can produce JSON guided by a schema. Google's documentation distinguishes syntactic structure from semantic correctness and recommends validating final outputs in application code. The supported JSON Schema subset and schema complexity impose practical constraints.

**Application/inference:** I2I separates model planning from React rendering and validates the plan before using it. A valid plan can still select unhelpful cards; syntax checks are not a substitute for intent evaluation or grounded data.

**Video-safe wording:** “The AI returns a constrained plan. The backend validates it, and the frontend renders components we already control.”

### 7. Browser-native animation control

**W3C CSS Working Group — “Web Animations,” Working Draft, 5 June 2023.** [W3C specification](https://www.w3.org/TR/web-animations-1/).

**Supported finding:** Web Animations defines a model and scripting interface for animations, including timing, playback and cancellation. Its draft status should not be described as a final accessibility certification or performance guarantee.

**Application/inference:** I2I's FLIP-style process measures card positions before and after a layout update, then animates transforms between them using `Element.animate`. Capturing the current visual position before cancelling running animations allows subsequent changes to begin from the visible state. This behavior is verified in project code; the specification does not assert I2I's frame rate.

**Video-safe wording:** “AI chooses the arrangement; the browser controls the transition. The result is designed to feel continuous.”

## Proposed DTPS: clearly future work

The user's proposed Dynamic Task Priority Score is `P = 0.35U + 0.30I + 0.20D + 0.15B`, with urgency, business impact, dependency importance and delay risk scored from 0 to 100. It is not implemented. Current “High” and “Medium” issue badges are sample labels. A future backend could calculate deterministic scores, label priorities and expose each contribution. Confirmed critical impact or blockers could trigger a top-tier override. Gemini could suggest uncertain estimates for user confirmation, but missing deadlines or dependencies must remain explicit. Weights, urgency bands and thresholds are proposed design choices requiring team feedback and validation. NASA-TLX is unrelated to this formula.

## Uniqueness and evaluation claims

Describe I2I's distinction as its combination: natural-language intent, one adaptive canvas, reusable task tools, card explanations, preserved interaction state and controlled motion. Do not claim a world-first invention or a novel validated algorithm.

Next research should compare the adaptive canvas with a fixed dashboard on the same three tasks, using equivalent data and counterbalanced order. Measure completion accuracy, time, navigation effort, perceived workload, intent/card relevance and unwanted changes. Include ambiguous goals, rapid refinements, failed model calls and reduced motion. Code checks cover implementation behavior; they do not demonstrate usability benefits. Report actual study results only after the study exists.
