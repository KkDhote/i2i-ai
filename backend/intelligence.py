"""Explainable local reasoning: explicit claims, conflicts, and task scores."""
from datetime import date
import json
from contextlib import closing
import sqlite3


def initialize(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS evidence_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER NOT NULL, step_id INTEGER NOT NULL,
            source TEXT NOT NULL, metric TEXT NOT NULL, period TEXT NOT NULL,
            value TEXT NOT NULL, observed_on TEXT NOT NULL, note TEXT NOT NULL)''')
        if 'active' not in {r[1] for r in db.execute('PRAGMA table_info(evidence_records)')}:
            db.execute('ALTER TABLE evidence_records ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
        db.execute('''CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, kind TEXT NOT NULL,
            detail TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        db.execute('''CREATE TABLE IF NOT EXISTS action_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER NOT NULL,
            kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending review',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        db.execute('''CREATE TABLE IF NOT EXISTS goal_constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER NOT NULL,
            name TEXT NOT NULL, value TEXT NOT NULL)''')
        if 'active' not in {r[1] for r in db.execute('PRAGMA table_info(goal_constraints)')}:
            db.execute('ALTER TABLE goal_constraints ADD COLUMN active INTEGER NOT NULL DEFAULT 1')


def journal(db, goal_id, kind, detail):
    db.execute('INSERT INTO decisions(goal_id,kind,detail) VALUES (?,?,?)', (goal_id, kind, detail))


def score_task(task, today=None):
    today = today or date.today()
    days = (date.fromisoformat(task['due_date']) - today).days if task.get('due_date') else None
    urgency = 30 if days is None else 100 if days < 0 else 90 if days == 0 else 75 if days == 1 else 50 if days <= 3 else 30 if days <= 7 else 10
    impact = task.get('impact', 50)
    dependency = task.get('dependency_score', 0)
    risk = task.get('delay_risk', 35)
    score = round(.35 * urgency + .30 * impact + .20 * dependency + .15 * risk, 2)
    critical = impact == 100 or dependency == 100
    label = 'Critical' if critical or score >= 80 else 'High' if score >= 60 else 'Medium' if score >= 40 else 'Low'
    return dict(task, dtps=score, dtps_label=label, critical_override=critical,
                factors={'urgency': urgency, 'impact': impact, 'dependency': dependency, 'delay_risk': risk},
                score_note='User-supplied factors; defaults are impact 50, dependency 0, delay risk 35. No dependency is inferred.')


def enrich(path, goal):
    if not goal:
        return None
    initialize(path)
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        records = [dict(row) for row in db.execute('SELECT * FROM evidence_records WHERE goal_id=? AND active=1 ORDER BY id', (goal['id'],))]
        decisions = [dict(row) for row in db.execute('SELECT * FROM decisions WHERE goal_id=? ORDER BY id DESC LIMIT 30', (goal['id'],))]
        constraints = [dict(row) for row in db.execute('SELECT * FROM goal_constraints WHERE goal_id=? AND active=1', (goal['id'],))]
        drafts = [dict(row) for row in db.execute('SELECT * FROM action_drafts WHERE goal_id=? ORDER BY id DESC', (goal['id'],))]
    claims = {}
    for record in records:
        record['stale'] = (date.today() - date.fromisoformat(record['observed_on'])).days > 30
        key = (record['metric'].strip().casefold(), record['period'].strip().casefold())
        claims.setdefault(key, []).append(record)
    conflicts = []
    for (metric, period), group in claims.items():
        if len({r['value'].strip().casefold() for r in group}) > 1:
            conflicts.append({'metric': metric, 'period': period, 'evidence_ids': [r['id'] for r in group], 'message': 'Conflicting values for the same metric and period. Reconcile the sources before drawing conclusions.'})
    constraint_groups = {}
    for item in constraints:
        constraint_groups.setdefault(item['name'].casefold(), set()).add(item['value'].casefold())
    goal_conflicts = [{'name': key, 'values': sorted(values)} for key, values in constraint_groups.items() if len(values) > 1]
    for step in goal['steps']:
        step['evidence_records'] = [r for r in records if r['step_id'] == step['id']]
    next_step = next((s for s in goal['steps'] if s['status'] != 'Completed'), None)
    relevant = [r for r in records if next_step and r['step_id'] == next_step['id']]
    next_action = None
    if next_step:
        next_action = {'step_id': next_step['id'], 'title': next_step['title'], 'evidence_ids': [r['id'] for r in relevant],
                       'reason': 'First unfinished step in the saved dependency sequence.',
                       'action': 'Reconcile conflicting evidence' if conflicts else 'Gather required evidence' if not next_step['evidence'].strip() else 'Create or link a task' if not next_step['task_id'] else 'Complete the linked task'}
    status = 'Conflicting evidence' if conflicts else 'Evidence supplied; not independently verified' if records else 'Insufficient sourced evidence'
    goal.update(evidence_records=records, contradictions=conflicts, constraints=constraints, goal_conflicts=goal_conflicts,
                decisions=decisions, drafts=[dict(d, payload=json.loads(d['payload'])) for d in drafts],
                next_action=next_action, evidence_status=status,
                stage='Completion review' if goal['status'] == 'Completed' else 'Planning' if not any(s['task_id'] for s in goal['steps']) else 'Investigation' if goal['gaps'] else 'Execution')
    if conflicts:
        goal['status'] = 'Needs evidence review'
        affected = {r['step_id'] for r in records if any(r['id'] in c['evidence_ids'] for c in conflicts)}
        blocked = False
        for step in goal['steps']:
            if step['id'] in affected:
                step['status'] = 'Conflicting evidence'; blocked = True
            elif blocked:
                step['status'] = 'Blocked'
        goal['completed'] = sum(s['status'] == 'Completed' for s in goal['steps'])
        first_conflict = next(s for s in goal['steps'] if s['status'] == 'Conflicting evidence')
        goal['next_action'] = {'step_id': first_conflict['id'], 'title': first_conflict['title'],
                               'action': 'Reconcile conflicting evidence', 'reason': 'Conflicting source values prevent a supported conclusion.',
                               'evidence_ids': [r['id'] for r in records if r['step_id'] == first_conflict['id']]}
        goal['stage'] = 'Investigation'
    if goal_conflicts:
        goal['status'] = 'Needs constraint review'
    # A stall is an explicit operational threshold, not an AI prediction.
    last = decisions[0]['created_at'][:10] if decisions else None
    goal['stalled'] = bool(last and (date.today() - date.fromisoformat(last)).days >= 3 and goal['status'] != 'Completed')
    return goal


def report(goal):
    lines = [f"# {goal['intent']}", '', f"Stage: {goal['stage']}", f"Evidence status: {goal['evidence_status']}", '', '## Progress']
    for step in goal['steps']:
        lines.extend([f"- {step['title']}: {step['status']}", f"  Evidence requirement: {step['requirement']}", f"  User notes: {step['evidence'] or 'Missing'}"])
    lines += ['', '## Source records (user supplied)']
    for r in goal['evidence_records']:
        lines.append(f"- [E{r['id']}] {r['source']}: {r['metric']} ({r['period']}) = {r['value']}; observed {r['observed_on']}. {r['note']}")
    lines += ['', '## Unresolved gaps'] + [f"- {g['title']}: {g['next_action']}" for g in goal['gaps']]
    lines += [f"- Conflict: {c['metric']} ({c['period']}); records {c['evidence_ids']}" for c in goal['contradictions']]
    lines += ['', '## Goal constraints'] + [f"- {c['name']}: {c['value']}" for c in goal['constraints']]
    lines += [f"- Conflicting constraint: {c['name']}; values {c['values']}" for c in goal['goal_conflicts']]
    lines += ['', '## Recommended next action', str(goal['next_action']['action'] if goal['next_action'] else 'Review and accept the completed outcome.'), '', 'Evidence is not independently verified. This draft does not send email or modify external tools.']
    return '\n'.join(lines)
