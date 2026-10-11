"""Persistent goal steps and deterministic evidence-gap checks."""
import json
import sqlite3
from contextlib import closing
from datetime import date

TEMPLATES = {
    'meeting': [('Review client context', 'Client profile and previous commitments'), ('Review usage and open issues', 'Current usage figures and support-ticket references'), ('Prepare meeting agenda', 'Confirmed discussion points and desired decisions')],
    'usage': [('Establish the usage change', 'Baseline, comparison period and usage figures'), ('Investigate possible causes', 'Cohort comparisons, incidents and release references'), ('Recommend an investigation plan', 'Findings supported by the available evidence')],
    'overdue': [('Review overdue work', 'Task deadlines and current completion status'), ('Confirm blockers and owners', 'Confirmed dependencies, responsible owners and recovery dates'), ('Prepare recovery actions', 'Agreed next steps and realistic delivery dates')],
    'custom': [('Define the desired outcome', 'Success criteria and relevant context'), ('Gather supporting evidence', 'Sources needed to support the outcome'), ('Prepare the next steps', 'Evidence-supported actions and owners')],
}

def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db

def initialize(path):
    with closing(connect(path)) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, intent TEXT NOT NULL,
            mode TEXT NOT NULL, layout TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0)''')
        db.execute('''CREATE TABLE IF NOT EXISTS goal_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER NOT NULL REFERENCES goals(id),
            position INTEGER NOT NULL, title TEXT NOT NULL, requirement TEXT NOT NULL,
            task_id INTEGER REFERENCES tasks(id), evidence TEXT NOT NULL DEFAULT '')''')

def activate_plan(path, intent, layout, patch=False):
    initialize(path)
    with closing(connect(path)) as db, db:
        current = db.execute('SELECT * FROM goals WHERE active=1').fetchone()
        if patch and current:
            db.execute('UPDATE goals SET layout=? WHERE id=?', (json.dumps(layout), current['id']))
            return current['id']
        goal = db.execute('SELECT id FROM goals WHERE intent=? AND mode=? ORDER BY id DESC LIMIT 1', (intent, layout['mode'])).fetchone()
        db.execute('UPDATE goals SET active=0')
        if goal:
            id = goal['id']
            db.execute('UPDATE goals SET active=1, layout=? WHERE id=?', (json.dumps(layout), id))
        else:
            id = db.execute('INSERT INTO goals(intent,mode,layout,active) VALUES (?,?,?,1)', (intent, layout['mode'], json.dumps(layout))).lastrowid
            db.executemany('INSERT INTO goal_steps(goal_id,position,title,requirement) VALUES (?,?,?,?)', [(id, i, title, requirement) for i, (title, requirement) in enumerate(TEMPLATES.get(layout['mode'], TEMPLATES['custom']))])
        return id

def read_goal(path, id=None):
    initialize(path)
    with closing(connect(path)) as db, db:
        goal = db.execute('SELECT * FROM goals WHERE id=?' if id else 'SELECT * FROM goals WHERE active=1', (id,) if id else ()).fetchone()
        if not goal:
            return None
        steps = [dict(row) for row in db.execute('''SELECT s.*,t.status AS task_status,t.owner,t.due_date,t.title AS task_title
            FROM goal_steps s LEFT JOIN tasks t ON t.id=s.task_id WHERE goal_id=? ORDER BY position''', (goal['id'],))]
        gaps = []
        for i, step in enumerate(steps):
            step['depends_on'] = [steps[i-1]['id']] if i else []
            dependency_complete = not i or steps[i-1]['status'] == 'Completed'
            evidence = bool(step['evidence'].strip())
            if step['task_status'] == 'Completed' and evidence and dependency_complete:
                step['status'] = 'Completed'
            elif not dependency_complete:
                step['status'] = 'Blocked'
            elif not evidence:
                step['status'] = 'Awaiting evidence'
            else:
                step['status'] = step['task_status'] or 'Pending'
            if not evidence:
                gaps.append({'step_id': step['id'], 'title': 'Missing evidence: ' + step['title'], 'reason': step['requirement'], 'next_action': 'Add a source reference and findings before treating this step as supported.'})
            if not step['task_id']:
                gaps.append({'step_id': step['id'], 'title': 'No task linked: ' + step['title'], 'reason': 'This step has no tracked work item.', 'next_action': 'Link an existing task or create one for this step.'})
            elif step['task_status'] != 'Completed':
                gaps.append({'step_id': step['id'], 'title': 'Incomplete work: ' + step['title'], 'reason': 'The linked task is ' + step['task_status'] + '.', 'next_action': 'Finish or review this work before marking the goal complete.'})
                if step['owner'] == 'Unassigned':
                    gaps.append({'step_id': step['id'], 'title': 'Missing assignee', 'reason': step['title'], 'next_action': 'Confirm who owns this step.'})
                if not step['due_date'] or step['due_date'] < date.today().isoformat():
                    gaps.append({'step_id': step['id'], 'title': 'Deadline needs attention', 'reason': step['title'], 'next_action': 'Review the linked task deadline and agree on a recovery date.'})
        result = dict(goal)
        result['layout'] = json.loads(result['layout'])
        result['steps'] = steps
        result['gaps'] = gaps
        result['completed'] = sum(s['status'] == 'Completed' for s in steps)
        result['status'] = 'Completed' if result['completed'] == len(steps) else 'In Progress'
        return result
