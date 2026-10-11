"""Local review and approval endpoints. External delivery requires integrations."""
import json
from contextlib import closing
from datetime import date
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from adaptive import Plan, finish
import goals
import intelligence

class EvidenceCreate(BaseModel):
    step_id: int = Field(gt=0)
    source: str = Field(min_length=1, max_length=500)
    metric: str = Field(min_length=1, max_length=100)
    period: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)
    observed_on: date
    note: str = Field(default='', max_length=2000)
    @field_validator('source', 'metric', 'period', 'value')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('A value is required')
        return value.strip()
    @field_validator('observed_on')
    @classmethod
    def not_future(cls, value):
        if value > date.today(): raise ValueError('Observation date cannot be in the future')
        return value

class LayoutCommit(BaseModel):
    plan: Plan
    intent: str = Field(default='', max_length=2000)
    patch: bool = False
    goal_id: int | None = None

class ConstraintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)

class DraftCreate(BaseModel):
    kind: Literal['Report', 'Email', 'Calendar event', 'Project update']
    destination: str = Field(default='', max_length=300)

class DraftDecision(BaseModel):
    decision: Literal['Approved', 'Rejected']
    content: str = Field(max_length=15000)


def install(app, path):
    def goal(id):
        result = intelligence.enrich(path(), goals.read_goal(path(), id))
        if not result: raise HTTPException(status_code=404, detail='Goal not found')
        return result

    @app.post('/api/layout/commit')
    def commit(body: LayoutCommit):
        intelligence.initialize(path())
        if len({c.id for c in body.plan.components}) != len(body.plan.components):
            raise HTTPException(status_code=400, detail='Duplicate cards')
        if body.goal_id:
            goal(body.goal_id)
            with closing(goals.connect(path())) as db, db:
                db.execute('UPDATE goals SET active=0')
                db.execute('UPDATE goals SET active=1,layout=? WHERE id=?', (body.plan.model_dump_json(), body.goal_id))
                intelligence.journal(db, body.goal_id, 'Layout approved', body.plan.title)
        elif body.plan.mode != 'home':
            id = goals.activate_plan(path(), body.intent or body.plan.title, body.plan.model_dump(), body.patch)
            with closing(goals.connect(path())) as db, db:
                intelligence.journal(db, id, 'Layout approved', body.plan.title)
        return finish(body.plan, 'user', 'Layout reviewed and applied.')

    @app.post('/api/evidence', status_code=201)
    def add_evidence(body: EvidenceCreate):
        intelligence.initialize(path())
        with closing(goals.connect(path())) as db, db:
            step = db.execute('SELECT * FROM goal_steps WHERE id=?', (body.step_id,)).fetchone()
            if not step: raise HTTPException(status_code=404, detail='Step not found')
            record = body.model_dump(); record['observed_on'] = body.observed_on.isoformat(); record['goal_id'] = step['goal_id']
            id = db.execute('''INSERT INTO evidence_records(goal_id,step_id,source,metric,period,value,observed_on,note)
                VALUES (:goal_id,:step_id,:source,:metric,:period,:value,:observed_on,:note)''', record).lastrowid
            # Structured evidence also supplies a visible, source-labelled step note.
            note = f"[E{id}] {body.source}: {body.metric} ({body.period}) = {body.value}. {body.note}"
            db.execute('UPDATE goal_steps SET evidence=? WHERE id=?', ((step['evidence'] + '\n' + note).strip(), body.step_id))
            intelligence.journal(db, step['goal_id'], 'Evidence added', note)
        return dict(record, id=id)

    @app.post('/api/goals/{id}/constraints', status_code=201)
    def add_constraint(id: int, body: ConstraintCreate):
        goal(id)
        if not body.name.strip() or not body.value.strip(): raise HTTPException(status_code=400, detail='Constraint fields are required')
        with closing(goals.connect(path())) as db, db:
            db.execute('INSERT INTO goal_constraints(goal_id,name,value) VALUES (?,?,?)', (id, body.name.strip(), body.value.strip()))
            intelligence.journal(db, id, 'Constraint recorded', f'{body.name}: {body.value}')
        return goal(id)

    @app.post('/api/evidence/{id}/withdraw')
    def withdraw(id: int):
        intelligence.initialize(path())
        with closing(goals.connect(path())) as db, db:
            row = db.execute('SELECT * FROM evidence_records WHERE id=?', (id,)).fetchone()
            if not row: raise HTTPException(status_code=404, detail='Evidence not found')
            db.execute('UPDATE evidence_records SET active=0 WHERE id=?', (id,))
            step = db.execute('SELECT evidence FROM goal_steps WHERE id=?', (row['step_id'],)).fetchone()
            if step:
                remaining = '\n'.join(line for line in step['evidence'].splitlines() if not line.startswith(f'[E{id}] '))
                db.execute('UPDATE goal_steps SET evidence=? WHERE id=?', (remaining, row['step_id']))
            intelligence.journal(db, row['goal_id'], 'Evidence withdrawn', f'E{id}: {row["source"]}; retained in audit history')
        return goal(row['goal_id'])

    @app.get('/api/goals/{id}/report')
    def get_report(id: int):
        return {'content': intelligence.report(goal(id))}

    @app.post('/api/constraints/{id}/withdraw')
    def withdraw_constraint(id: int):
        intelligence.initialize(path())
        with closing(goals.connect(path())) as db, db:
            row = db.execute('SELECT * FROM goal_constraints WHERE id=?', (id,)).fetchone()
            if not row: raise HTTPException(status_code=404, detail='Constraint not found')
            db.execute('UPDATE goal_constraints SET active=0 WHERE id=?', (id,))
            intelligence.journal(db, row['goal_id'], 'Constraint withdrawn', f'{row["name"]}: {row["value"]}')
        return goal(row['goal_id'])

    @app.post('/api/goals/{id}/drafts', status_code=201)
    def draft(id: int, body: DraftCreate):
        current = goal(id)
        payload = {'destination': body.destination, 'content': intelligence.report(current), 'kind': body.kind,
                   'effect': 'Save approval locally. No external system is contacted.'}
        with closing(goals.connect(path())) as db, db:
            draft_id = db.execute('INSERT INTO action_drafts(goal_id,kind,payload) VALUES (?,?,?)', (id, body.kind, json.dumps(payload))).lastrowid
            intelligence.journal(db, id, 'Action preview prepared', body.kind)
        return dict(payload, id=draft_id, status='Pending review')

    @app.post('/api/drafts/{id}/decision')
    def decide(id: int, body: DraftDecision):
        intelligence.initialize(path())
        with closing(goals.connect(path())) as db, db:
            row = db.execute('SELECT * FROM action_drafts WHERE id=?', (id,)).fetchone()
            if not row: raise HTTPException(status_code=404, detail='Draft not found')
            if row['status'] != 'Pending review': raise HTTPException(status_code=409, detail='This draft has already been reviewed')
            payload = json.loads(row['payload']); payload['content'] = body.content
            db.execute('UPDATE action_drafts SET status=?,payload=? WHERE id=?', (body.decision, json.dumps(payload), id))
            intelligence.journal(db, row['goal_id'], 'Action ' + body.decision.lower(), row['kind'] + '; saved locally, not sent externally')
        return {'status': body.decision, 'external_execution': False}
