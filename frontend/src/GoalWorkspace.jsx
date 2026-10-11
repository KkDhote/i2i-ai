import { useState } from 'react';
import { api } from './api';

function GoalStep({ step, tasks, onRefresh, onNewTask }) {
  const [evidence, setEvidence] = useState(step.evidence);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function save(body) {
    setBusy(true); setError('');
    try { await api(`/goal-steps/${step.id}`, { method: 'PATCH', body: JSON.stringify(body) }); await onRefresh(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  async function changeStatus(status) {
    setBusy(true); setError('');
    try { await api(`/tasks/${step.task_id}?${new URLSearchParams({ status })}`, { method: 'PATCH' }); await onRefresh(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <li className={`goal-node ${step.status === 'Completed' ? 'goal-complete' : ''}`}>
    <div className="goal-node-heading"><span className="goal-node-number">{step.position + 1}</span><strong>{step.title}</strong><span className="badge">{step.status}</span></div>
    <p className="goal-requirement">Evidence needed: {step.requirement}</p>
    {step.position > 0 && <p className="data-note">Depends on completion of step {step.position}.</p>}
    <label className="goal-field">Linked task<select aria-label={`Linked task for ${step.title}`} value={step.task_id || ''} disabled={busy} onChange={e => save({ task_id: e.target.value ? Number(e.target.value) : null })}>
      <option value="">Choose an existing task</option>{tasks.map(t => <option key={t.id} value={t.id}>{t.title} — {t.status}</option>)}
    </select></label>
    {step.task_id && <label className="goal-field">Task status<select aria-label={`Task status for ${step.title}`} value={step.task_status} disabled={busy} onChange={e => changeStatus(e.target.value)}><option>Pending</option><option>In Progress</option><option>Completed</option></select></label>}
    {!step.task_id && <button className="text-button" onClick={() => onNewTask(step.title, step.id)}>Create a task for this step</button>}
    <form onSubmit={e => { e.preventDefault(); save({ evidence }); }}>
      <label className="goal-field">Source reference and findings<textarea aria-label={`Evidence for ${step.title}`} placeholder="Source or document reference, what it establishes, and any uncertainty…" maxLength={4000} value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
      <button className="cancel-button" disabled={busy || evidence.trim() === step.evidence}>{busy ? 'Saving…' : 'Save evidence'}</button>
    </form>
    {error && <p className="error-notice" role="alert">{error}</p>}
  </li>;
}

export default function GoalWorkspace({ goal, tasks, onRefresh, onNewTask }) {
  if (!goal) return null;
  return <section className="goal-workspace" aria-label="Goal plan and gap radar">
    <article className="panel goal-graph"><div className="panel-heading"><h2>Live Goal Graph</h2><span className="data-badge live">Saved in SQLite</span></div>
      <h3>{goal.intent}</h3><p>{goal.completed} of {goal.steps.length} steps complete · {goal.status}</p>
      <progress aria-label="Goal completion" value={goal.completed} max={goal.steps.length} />
      <p className="data-note">Suggested sequence for this scenario. Completion requires a completed linked task, supplied evidence, and completed preceding steps. Evidence is user-provided, not independently verified.</p>
      <ol className="goal-steps">{goal.steps.map(step => <GoalStep key={step.id} step={step} tasks={tasks} onRefresh={onRefresh} onNewTask={onNewTask} />)}</ol>
    </article>
    <article className="panel gap-radar"><div className="panel-heading"><h2>Proactive Gap Radar</h2><span className="badge warning">{goal.gaps.length} gaps</span></div>
      <p className="data-note">Checks the saved plan against linked tasks and supplied evidence whenever work changes.</p>
      {goal.gaps.length ? <ul className="gap-list">{goal.gaps.map((gap, i) => <li key={`${gap.step_id}-${i}`}><strong>{gap.title}</strong><p>{gap.reason}</p><small>Next: {gap.next_action}</small></li>)}</ul> : <p>No missing evidence or task-link gaps detected. Review the evidence quality before accepting the outcome.</p>}
    </article>
  </section>;
}
