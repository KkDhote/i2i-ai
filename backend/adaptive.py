"""Validated screen plans for the adaptive workspace. Never generate UI code."""
import json
import logging
import re
from time import monotonic
from typing import Literal

from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, field_validator

CardId = Literal['metrics', 'performance', 'assistant', 'tasks', 'client',
                 'communications', 'issues', 'usage', 'cohorts', 'meeting',
                 'overdue', 'blockers', 'actions']
Mode = Literal['home', 'meeting', 'usage', 'overdue', 'custom']

CATALOG = {
    'metrics': ('Workspace overview', 'Live task counts and completion rate'),
    'performance': ('Business performance', 'Illustrative activity chart'),
    'assistant': ('I2I AI', 'Ask questions grounded in workspace tasks'),
    'tasks': ('Team tasks', 'Search, create and update live tasks'),
    'client': ('Client overview', 'Sample client account and meeting context'),
    'communications': ('Recent conversations', 'Sample client emails and notes'),
    'issues': ('Open issues', 'Sample customer issues and their owners'),
    'usage': ('Product usage', 'Sample active-user trend and release event'),
    'cohorts': ('Affected segments', 'Sample usage changes by customer segment'),
    'meeting': ('Meeting brief', 'Sample agenda and suggested talking points'),
    'overdue': ('Overdue work', 'Live incomplete tasks past their due date'),
    'blockers': ('Project blockers', 'Sample dependencies blocking project work'),
    'actions': ('Next actions', 'Suggested actions for the current goal'),
}
LAYOUTS = {
    'home': ('Your business at a glance', 'A familiar dashboard. Tell us your goal to shape it around your work.',
             [('metrics', 12), ('performance', 8), ('assistant', 4), ('tasks', 12)]),
    'meeting': ('Walk into your meeting prepared', 'Client context, open issues and talking points in one workspace.',
                [('client', 4), ('meeting', 8), ('communications', 6), ('issues', 6), ('usage', 8), ('actions', 4)]),
    'usage': ('Understand what changed', 'Follow the usage drop from the trend to affected segments and possible causes.',
              [('usage', 8), ('cohorts', 4), ('issues', 6), ('communications', 6), ('actions', 12)]),
    'overdue': ('Get project work moving again', 'Bring overdue work, blockers and priorities to the front.',
                [('metrics', 12), ('overdue', 8), ('blockers', 4), ('tasks', 8), ('actions', 4)]),
}


class Card(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: CardId
    # Gemini's SDK accepts string enums, so validate numeric spans after parsing.
    span: int = Field(ge=4, le=12)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator('span')
    @classmethod
    def grid_span(cls, value):
        if value not in (4, 6, 8, 12):
            raise ValueError('Card spans must be 4, 6, 8 or 12.')
        return value


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Mode
    title: str = Field(min_length=1, max_length=100)
    desc: str = Field(max_length=240)
    components: list[Card] = Field(min_length=1, max_length=10)


class IntentRequest(BaseModel):
    text: str = Field(default='', max_length=2000)
    pick: Literal['home', 'meeting', 'usage', 'overdue'] | None = None
    current: Plan | None = None


class Decision(BaseModel):
    # Required fields keep the model's output schema small and predictable.
    op: Literal['replace', 'patch', 'clarify', 'unsupported']
    mode: Mode
    title: str
    desc: str
    summary: str
    components: list[Card]
    remove: list[CardId]
    message: str


def options():
    return [{'key': k, 'label': label} for k, label in
            [('meeting', 'Prepare a client meeting'), ('usage', 'Investigate a usage drop'),
             ('overdue', 'Review overdue work')]]


def finish(plan, source, summary='', op='replace'):
    if len({c.id for c in plan.components}) != len(plan.components):
        raise ValueError('Duplicate cards in plan')
    return {'status': 'plan', 'op': op, 'source': source, 'summary': summary,
            'plan': plan.model_dump()}


def curated(mode, source='preset'):
    title, desc, cards = LAYOUTS[mode]
    components = [Card(id=id, span=span, reason=CATALOG[id][1] + '.') for id, span in cards]
    return finish(Plan(mode=mode, title=title, desc=desc, components=components), source,
                  'The most relevant information and actions are arranged for this goal.')


def clarification(message, source='rules'):
    return {'status': 'clarify', 'message': message, 'options': options(), 'source': source}


def apply_decision(out, current):
    if out.op in ('clarify', 'unsupported'):
        return {'status': out.op, 'message': out.message[:300] or 'Which workspace goal do you mean?',
                'options': options(), 'source': 'gemini'}
    if out.op == 'patch':
        if not current:
            raise ValueError('A refinement needs a current screen')
        # Reuse existing cards and their ordering; an update never duplicates a card.
        cards = {c.id: c for c in current.components if c.id not in out.remove}
        for card in out.components:
            cards[card.id] = card
        plan = current.model_copy(update={'components': list(cards.values())})
        plan = Plan.model_validate(plan.model_dump())
    else:
        plan = Plan(mode=out.mode, title=out.title, desc=out.desc, components=out.components)
    return finish(plan, 'gemini', out.summary[:300], out.op)


def by_rules(text, current=None):
    t = text.lower().strip()
    if re.fullmatch(r'(home|dashboard|reset|back to dashboard)', t):
        return curated('home', 'rules')
    # ponytail: finite demo vocabulary; Gemini handles broader language when configured.
    add = bool(re.search(r'\b(also|add|include|show)\b', t))
    remove = bool(re.search(r'\b(remove|hide|without)\b', t))
    aliases = {'overdue': ('overdue', 'late tasks'), 'issues': ('issues', 'bugs'),
               'actions': ('next actions', 'actions'), 'tasks': ('team tasks', 'tasks'),
               'usage': ('usage', 'active users'), 'client': ('client details', 'client overview'),
               'communications': ('conversations', 'emails'), 'blockers': ('blockers',),
               'assistant': ('assistant', 'copilot'), 'metrics': ('metrics',)}
    is_refine = current and (remove or t.startswith(('also ', 'add ', 'include ', 'show ')))
    if is_refine:
        matched = [id for id, words in aliases.items() if any(word in t for word in words)]
        # "Overdue tasks" refers to the filtered card, not both task tables.
        if 'overdue' in matched and 'tasks' in matched:
            matched.remove('tasks')
        if not matched or (add and remove):
            return clarification('Please add or remove one kind of information at a time.')
        cards = {c.id: c for c in current.components}
        for id in matched:
            if remove:
                cards.pop(id, None)
            else:
                cards[id] = Card(id=id, span=8 if id in ('tasks', 'overdue', 'usage') else 4,
                                 reason='You asked to include this in the current workspace.')
        if not cards:
            return clarification('Keep at least one card, or choose a different goal.')
        return finish(Plan(**{**current.model_dump(), 'components': list(cards.values())}),
                      'rules', 'Updated only the information you asked to change.', 'patch')
    keywords = {'meeting': ('meeting', 'talking points', 'agenda'),
                'usage': ('usage', 'active users', 'drop', 'retention', 'engagement'),
                'overdue': ('overdue', 'late', 'deadline', 'blocked', 'prioritize')}
    hits = [mode for mode, words in keywords.items()
            if any(re.search(r'\b' + re.escape(word) + r'\b', t) for word in words)]
    if len(hits) == 1:
        return curated(hits[0], 'rules')
    if len(hits) > 1:
        return clarification('Which goal should lead the workspace? You can add more cards afterward.')
    return clarification('What would you like to focus on: a client meeting, product usage, or overdue work?')


_plans = {}
_demo_goals = {"prepare for tomorrow's client meeting", 'investigate why active users dropped', 'review overdue project work'}


def arrange(request, client, model):
    if request.pick:
        return curated(request.pick)
    text = request.text.strip()
    if not text:
        raise ValueError('Please enter a goal.')
    if client:
        # Plans contain no task data. Repeating a goal can reuse its validated layout.
        current = None if text.lower() in _demo_goals else request.current
        key = json.dumps([model, text.lower(), current.model_dump() if current else None], sort_keys=True)
        cached = _plans.get(key)
        if cached and monotonic() - cached[0] < 300:
            return {**cached[1], 'cached': True}
        try:
            response = client.models.generate_content(
                model=model, contents=json.dumps({'goal': text, 'current': current.model_dump()
                                                 if current else None}),
                config=types.GenerateContentConfig(
                    response_mime_type='application/json', response_json_schema=Decision.model_json_schema(),
                    thinking_config=types.ThinkingConfig(thinking_level='minimal'),
                    max_output_tokens=1600, http_options=types.HttpOptions(timeout=12000),
                    system_instruction=(
                        'Plan an adaptive business workspace using ONLY the catalog below. '
                        'Never write HTML or code or invent available data. New goals replace the layout '
                        'with 3-7 relevant cards, ordered by importance. Follow-up instructions add, update '
                        'or remove cards using op patch; components contains only additions or updates. '
                        'Card spans must be 4, 6, 8 or 12, with each row adding to 12 where possible. '
                        'Keep the current goal for patches. If ambiguous, clarify instead of guessing. '
                        'For unrelated requests return unsupported. Put an explanation in each reason '
                        'and a brief user-facing explanation in summary. Required but unused string '
                        'fields should be empty, unused arrays empty. Sample cards use demo data. '
                        'Catalog: ' + json.dumps(CATALOG))))
            result = apply_decision(Decision.model_validate_json(response.text), current)
            if result['status'] == 'plan':
                if len(_plans) >= 128:
                    _plans.pop(next(iter(_plans)))
                _plans[key] = (monotonic(), result)
            return result
        except Exception as exc:
            logging.warning('Adaptive planner fell back to rules (%s)', type(exc).__name__)
    result = by_rules(text, request.current)
    result['fallback'] = bool(client)
    return result


# Explicit sample context shared by the three demo scenarios.
DEMO = {
    'client': {'name': 'Northstar Labs', 'contact': 'Maya Chen', 'role': 'Head of Operations',
               'plan': 'Growth', 'seats': 48, 'renewal': 'In 6 weeks', 'health': 'Needs attention',
               'meeting': 'Tomorrow · 10:00 AM', 'goal': 'Review adoption and agree on a recovery plan.'},
    'communications': [
        {'from': 'Maya Chen', 'when': 'Yesterday', 'text': 'Our team is struggling to finish onboarding. Can we review the workflow in our meeting?'},
        {'from': 'Customer success', 'when': '2 days ago', 'text': 'Northstar reported slower exports after the latest release. Engineering is investigating.'},
        {'from': 'Account team', 'when': '4 days ago', 'text': 'Bring adoption numbers and a clear owner for each open issue to the next review.'}],
    'issues': [
        {'title': 'Onboarding stalls at workspace setup', 'owner': 'Product', 'priority': 'High', 'status': 'Investigating'},
        {'title': 'Exports take longer after release', 'owner': 'Engineering', 'priority': 'High', 'status': 'In Progress'},
        {'title': 'Admin training session requested', 'owner': 'Customer success', 'priority': 'Medium', 'status': 'Pending'}],
    'usage': {'before': [1200, 1260, 1240, 1310, 1290, 1340, 1300],
              'after': [1280, 1220, 1140, 1020, 940, 890, 860],
              'event': 'Release v2.4 · day 3', 'note': 'The drop follows a release; timing alone does not establish its cause.'},
    'cohorts': [{'name': 'New users', 'before': 420, 'after': 210},
               {'name': 'Returning users', 'before': 640, 'after': 500},
               {'name': 'Account admins', 'before': 240, 'after': 150}],
    'blockers': [{'title': 'Export fix awaiting regression review', 'owner': 'Engineering', 'impact': 'Customer issue remains open'},
                 {'title': 'Onboarding copy awaiting approval', 'owner': 'Product', 'impact': 'New users cannot finish setup confidently'},
                 {'title': 'Account training needs a time slot', 'owner': 'Customer success', 'impact': 'Client adoption plan is delayed'}],
    'meeting': ['Confirm the client’s goals and onboarding difficulties.',
                'Review the usage trend and distinguish evidence from hypotheses.',
                'Agree on owners and timelines for the two high-priority issues.',
                'Schedule admin training and a follow-up adoption review.'],
    'actions': {
        'meeting': ['Review Maya’s latest message.', 'Discuss open onboarding and export issues.', 'Create follow-up tasks with owners and dates.'],
        'usage': ['Compare new and returning user cohorts.', 'Check the release against onboarding and export errors.', 'Create a task to validate the cause before proposing a fix.'],
        'overdue': ['Review incomplete tasks past their due dates.', 'Assign an owner to the most urgent blocker.', 'Update status and schedule the next checkpoint.'],
        'home': ['Review team tasks.', 'Choose a goal to focus this workspace.', 'Ask I2I AI what to prioritize.'],
        'custom': ['Review the surfaced evidence.', 'Create a task for the next concrete step.']}
}
