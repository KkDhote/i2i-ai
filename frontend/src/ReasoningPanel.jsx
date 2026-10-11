import { useState } from 'react';
import { api } from './api';

export default function ReasoningPanel({ goal, onRefresh, onNewTask, onFocusProgress }) {
  const [record, setRecord] = useState({ step_id: goal.steps[0].id, source: '', metric: '', period: '', value: '', observed_on: '', note: '' });
  const [constraint, setConstraint] = useState({ name: '', value: '' });
  const [kind, setKind] = useState('Report');
  const [destination, setDestination] = useState('');
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function perform(work) {
    setBusy(true); setError('');
    try { await work(); await onRefresh(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  const next = goal.next_action;
  return <section className="p1-panels" aria-label="Evidence and outcome tools">
    <article className="panel"><div className="panel-heading"><h2>Evidence & reasoning</h2><span className="data-badge">{goal.stage}</span></div>
      <p className="data-note">{goal.evidence_status}. Sources below are user supplied. Conflict checks compare exact metric and period labels; freshness uses a 30-day threshold.</p>
      {goal.stalled && <p className="error-notice">This unfinished goal has had no recorded decision or step update for at least 3 days.</p>}
      {next && <div className="next-action"><strong>Next best action: {next.action}</strong><p>{next.title} — {next.reason}</p><p>Supporting records: {next.evidence_ids.length ? next.evidence_ids.map(id => <a key={id} href={`#evidence-${id}`}>E{id} </a>) : 'No sourced evidence yet'}</p><button className="cancel-button" onClick={onFocusProgress}>Focus workspace on this stage</button>{!goal.steps.find(s => s.id === next.step_id)?.task_id && <button className="text-button" onClick={() => onNewTask(next.title, next.step_id)}>Preview follow-up task</button>}</div>}
      {goal.contradictions.map(c => <div className="error-notice" key={`${c.metric}-${c.period}`}><strong>Conflicting evidence: {c.metric} / {c.period}</strong><p>{c.message} Records: {c.evidence_ids.map(id => `E${id}`).join(', ')}.</p></div>)}
      <details className="evidence-form"><summary>Add a sourced observation</summary><form onSubmit={e => { e.preventDefault(); perform(async () => { await api('/evidence', { method: 'POST', body: JSON.stringify(record) }); setRecord({ ...record, source: '', metric: '', value: '', note: '' }); }); }}>
        <label className="goal-field">Goal step<select value={record.step_id} onChange={e => setRecord({ ...record, step_id: Number(e.target.value) })}>{goal.steps.map(s => <option value={s.id} key={s.id}>{s.title}</option>)}</select></label>
        {[['source', 'Source URL or document reference'], ['metric', 'Metric (include cohort and unit)'], ['period', 'Comparison period'], ['value', 'Observed value'], ['note', 'Findings / uncertainty']].map(([key, label]) => <label key={key} className="goal-field">{label}<input required={key !== 'note'} maxLength={key === 'note' ? 2000 : key === 'source' ? 500 : key === 'value' ? 200 : 100} value={record[key]} onChange={e => setRecord({ ...record, [key]: e.target.value })} /></label>)}
        <label className="goal-field">Observation date<input required type="date" value={record.observed_on} onChange={e => setRecord({ ...record, observed_on: e.target.value })} /></label>
        <button className="primary-button" disabled={busy}>Save source record</button></form></details>
      <ul className="gap-list">{goal.evidence_records.map(r => <li id={`evidence-${r.id}`} key={r.id}><strong>[E{r.id}] {r.metric}: {r.value}</strong><p>{/^https?:\/\//i.test(r.source) ? <a href={r.source} target="_blank" rel="noreferrer">{r.source}</a> : r.source} · {r.period} · {r.observed_on}</p><p>{r.note}</p>{r.stale && <span className="badge warning">Older than 30 days — refresh recommended</span>}<button className="text-button" disabled={busy} onClick={() => perform(() => api(`/evidence/${r.id}/withdraw`, { method: 'POST' }))}>Withdraw from analysis</button></li>)}</ul>
      <details><summary>Goal constraints and conflicts</summary><p className="data-note">Record explicit constraints. Different values under the same constraint name are flagged for review.</p><form onSubmit={e => { e.preventDefault(); perform(async () => { await api(`/goals/${goal.id}/constraints`, { method: 'POST', body: JSON.stringify(constraint) }); setConstraint({ name: '', value: '' }); }); }}>
        <label className="goal-field">Constraint name<input required maxLength={100} placeholder="Delivery deadline" value={constraint.name} onChange={e => setConstraint({ ...constraint, name: e.target.value })} /></label><label className="goal-field">Required value<input required maxLength={200} value={constraint.value} onChange={e => setConstraint({ ...constraint, value: e.target.value })} /></label><button className="cancel-button" disabled={busy}>Record constraint</button></form>
        {goal.constraints.map(c => <p key={c.id}>{c.name}: {c.value} <button className="text-button" disabled={busy} onClick={() => perform(() => api(`/constraints/${c.id}/withdraw`, { method: 'POST' }))}>Withdraw constraint</button></p>)}{goal.goal_conflicts.map(c => <p className="error-notice" key={c.name}>Conflicting constraint: {c.name} — {c.values.join(' / ')}</p>)}</details>
    </article>
    <article className="panel"><div className="panel-heading"><h2>Outcome & action preview</h2><span className="data-badge">Review first</span></div>
      <p className="data-note">Prepare an editable, evidence-linked deliverable. Approvals are saved locally. Email, calendar and project tools are not connected, so approved drafts are not sent or executed.</p>
      <label className="goal-field">Deliverable<select value={kind} onChange={e => setKind(e.target.value)}><option>Report</option><option>Email</option><option>Calendar event</option><option>Project update</option></select></label>
      <label className="goal-field">Intended destination<input placeholder="Recipient, calendar or project (optional)" maxLength={300} value={destination} onChange={e => setDestination(e.target.value)} /></label>
      <button className="primary-button" disabled={busy} onClick={() => perform(async () => setDraft(await api(`/goals/${goal.id}/drafts`, { method: 'POST', body: JSON.stringify({ kind, destination }) })))}>Prepare action preview</button>
      {draft && <div className="draft-preview"><p><strong>{draft.kind}</strong> · {draft.destination || 'Local workspace'} · {draft.status}</p><p className="data-note">{draft.effect}</p><label className="goal-field">Review and edit<textarea aria-label="Deliverable draft" maxLength={15000} rows={16} value={draft.content} onChange={e => setDraft({ ...draft, content: e.target.value })} /></label>
        {draft.status === 'Pending review' && <div className="review-buttons"><button className="primary-button" disabled={busy} onClick={() => perform(async () => { await api(`/drafts/${draft.id}/decision`, { method: 'POST', body: JSON.stringify({ decision: 'Approved', content: draft.content }) }); setDraft({ ...draft, status: 'Approved' }); })}>Approve local draft</button><button className="cancel-button" disabled={busy} onClick={() => perform(async () => { await api(`/drafts/${draft.id}/decision`, { method: 'POST', body: JSON.stringify({ decision: 'Rejected', content: draft.content }) }); setDraft({ ...draft, status: 'Rejected' }); })}>Reject</button></div>}
        <button className="text-button" onClick={() => { const url = URL.createObjectURL(new Blob([draft.content], { type: 'text/markdown' })); const a = document.createElement('a'); a.href = url; a.download = 'I2I-outcome.md'; a.click(); URL.revokeObjectURL(url); }}>Download reviewed text</button>
      </div>}
      <details><summary>Saved action previews ({goal.drafts.length})</summary>{goal.drafts.map(d => <p key={d.id}><button className="text-button" onClick={() => setDraft({ ...d.payload, id: d.id, status: d.status })}>{d.kind} · {d.status}</button></p>)}</details>
      <details><summary>Decision journal ({goal.decisions.length})</summary><ul className="gap-list">{goal.decisions.map(d => <li key={d.id}><strong>{d.kind}</strong><p>{d.detail}</p><small>{d.created_at} UTC</small></li>)}</ul></details>
    </article>
    {error && <p className="error-notice" role="alert">{error}</p>}
  </section>;
}
