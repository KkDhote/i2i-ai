import { useId, useState } from 'react';
import { api } from './api';
import Icon from './Icon';

const CARD_TITLES = {
  metrics: 'Workspace overview', performance: 'Business performance', assistant: 'I2I AI',
  tasks: 'Team tasks', client: 'Client overview', communications: 'Recent conversations',
  issues: 'Open issues', usage: 'Product usage', cohorts: 'Affected segments',
  meeting: 'Meeting brief', overdue: 'Overdue work', blockers: 'Project blockers', actions: 'Next actions',
};
const LIVE = new Set(['metrics', 'tasks', 'overdue', 'assistant']);
const taskDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

function PriorityFactors({ task, onRefresh }) {
  const [factors, setFactors] = useState({ impact: task.impact, dependency_score: task.dependency_score, delay_risk: task.delay_risk });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  return <details className="priority-factors"><summary>{task.dtps} / 100 · {task.dtps_label}</summary><p>{task.critical_override ? 'Confirmed critical impact or blocker raises this task to the top tier. ' : ''}Urgency {task.factors?.urgency}. P = .35U + .30I + .20D + .15B.</p><p>{task.score_note}</p><form onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await api(`/tasks/${task.id}`, { method: 'PATCH', body: JSON.stringify(factors) }); await onRefresh(); } catch (err) { setError(err.message); } finally { setBusy(false); } }}>
    {[['impact', 'Business impact'], ['dependency_score', 'Confirmed dependency score'], ['delay_risk', 'Delay risk']].map(([key, label]) => <label key={key} className="goal-field">{label}<input aria-label={`${label} for ${task.title}`} required type="number" min={0} max={100} value={factors[key]} onChange={e => setFactors({ ...factors, [key]: Number(e.target.value) })} /></label>)}<button className="cancel-button" disabled={busy}>Save factors</button>{error && <p role="alert">{error}</p>}</form></details>;
}

function TaskTable({ tasks, onStatus, pending, onRefresh }) {
  return <div className="task-table-wrap"><table className="task-table">
    <thead><tr><th scope="col">Task</th><th scope="col">Assignee / team</th><th scope="col">Priority</th><th scope="col">Due date</th><th scope="col">Status</th></tr></thead>
    <tbody>{tasks.map(task => <tr key={task.id}>
      <td><strong>{task.title}</strong>{task.description && <small>{task.description}</small>}</td>
      <td><div className="task-owner"><span className="owner-avatar" aria-hidden="true">{(task.owner || 'Unassigned').split(' ').filter(Boolean).slice(0, 2).map(word => word[0]).join('')}</span>
        <div className="owner-details">{task.owner || 'Unassigned'}<small>{task.team || 'General'}</small></div></div></td>
      <td><span className={`badge ${['High', 'Critical'].includes(task.priority) ? 'warning' : ''}`}>{task.priority || 'Medium'}</span><PriorityFactors task={task} onRefresh={onRefresh} /></td>
      <td className="task-due">{task.due_date ? <time dateTime={task.due_date} title={task.due_date}>{taskDate.format(new Date(`${task.due_date}T12:00:00`))}</time> : <span className="muted">No date</span>}</td>
      <td><select aria-label={`Status for ${task.title}`} className={`status status-${task.status.toLowerCase().replaceAll(' ', '-')}`}
        value={task.status} disabled={pending.includes(task.id)} onChange={event => onStatus(task.id, event.target.value)}>
        <option>Pending</option><option>In Progress</option><option>Completed</option>
      </select></td>
    </tr>)}</tbody>
  </table>{!tasks.length && <div className="empty-state">No matching tasks. Add a task or adjust your search.</div>}</div>;
}

function Trend({ values, comparison, label }) {
  const max = Math.max(...values, ...(comparison || [])) * 1.12;
  const points = items => items.map((v, i) => `${i * 600 / (items.length - 1)},${170 - v / max * 150}`).join(' ');
  const last = values.at(-1), first = comparison ? comparison.at(-1) : values[0];
  const change = Math.round((last - first) / first * 100);
  return <><div className="chart-summary"><strong>{last.toLocaleString()} <small>{label}</small></strong>
    <span className={change < 0 ? 'negative' : 'metric-change'}>{change > 0 ? '+' : ''}{change}%</span></div>
    <svg className="trend-chart" viewBox="0 0 600 190" role="img" aria-label={`${label}: ${values.join(', ')}${comparison ? '. Dashed line shows the previous period.' : ''}`}>
      {[30, 80, 130, 180].map(y => <line key={y} x1="0" x2="600" y1={y} y2={y} stroke="var(--border)" />)}
      <polygon points={`0,180 ${points(values)} 600,180`} fill="var(--accent-soft)" />
      {comparison && <polyline points={points(comparison)} fill="none" stroke="var(--muted)" strokeWidth="2" strokeDasharray="5 6" />}
      <polyline points={points(values)} fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinejoin="round" />
      {values.map((v, i) => <circle key={i} cx={i * 600 / (values.length - 1)} cy={170 - v / max * 150} r="4" fill="var(--accent)" />)}
    </svg><div className="chart-days">{values.map((_, i) => <span key={i}>Day {i + 1}</span>)}</div></>;
}

function Assistant({ state, onChange, onAsk }) {
  const { question, answer, error, busy } = state;
  const questionId = useId();
  const setQuestion = question => onChange(current => ({ ...current, question }));
  return <><div className="ai-intro"><span className="assistant-kicker">A little help with the next step</span>
    <h3>What needs your attention?</h3><p>Check deadlines, understand progress, or talk through what to do next.</p></div>
    <div className="assistant-suggestions">{['What should our team prioritize?', 'Summarize our task progress'].map(q =>
      <button className="suggestion" key={q} disabled={busy} onClick={() => onAsk(q)}><span className="suggestion-label">{q}</span><Icon name="arrow-right" size={16} /></button>)}</div>
    {answer && <div className="ai-answer" aria-live="polite"><strong>AI-generated response</strong><p>{answer.split(/(\*\*[^*\n]+\*\*)/g).map((part, i) =>
      i % 2 ? <strong key={i}>{part.slice(2, -2)}</strong> : part)}</p></div>}
    {error && <div className="error-notice" role="alert">{error} Your question is saved; try sending it again.</div>}
    <div className="assistant-compose"><label className="ai-input-label" htmlFor={questionId}>Your question</label>
      <form className="ai-input" onSubmit={event => { event.preventDefault(); onAsk(question); }}><input id={questionId} aria-label="Ask I2I AI" placeholder="Ask about your tasks…" maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)} />
        <button type="submit" disabled={busy || !question.trim()} aria-label="Submit question">{busy ? <span className="planning-spinner" /> : <Icon name="arrow-up" size={18} />}</button></form></div>
    {busy && <p className="loading-copy" role="status">Reviewing your workspace…</p>}
    <p className="data-note">Uses live tasks. Client and usage details are sample data.</p>
  </>;
}

export default function Widget({ card, data, mode, showWhy, query, onStatus, onNewTask, pending, assistant, onAssistantChange, onAssistantAsk, onRefresh, pinned = [], onPin, onMove }) {
  const demo = data.demo;
  const filtered = data.tasks.filter(t => `${t.title} ${t.team} ${t.owner} ${t.status}`.toLowerCase().includes(query.toLowerCase())).sort((a, b) => (a.status === 'Completed') - (b.status === 'Completed') || Number(b.critical_override) - Number(a.critical_override) || b.dtps - a.dtps || a.id - b.id);
  const overdue = filtered.filter(t => t.due_date && t.due_date < data.today && t.status !== 'Completed');
  let content;
  switch (card.id) {
    case 'metrics': {
      const o = data.overview;
      content = <div className="metrics-grid">{[
        ['Total tasks', o.total_tasks, 'grid', 'In this workspace'], ['Completed', o.completed_tasks, 'check', 'Finished by the team'],
        ['Remaining', o.pending_tasks, 'clock', 'Still to complete'], ['Completion rate', `${o.total_tasks ? Math.round(o.completed_tasks / o.total_tasks * 100) : 0}%`, 'chart', 'Tasks completed'],
      ].map(([label, value, icon, note]) => <div className="metric" key={label}><div className="metric-top">{label}<span className="metric-icon"><Icon name={icon} size={16} /></span></div>
        <div className="metric-value">{value}</div><small>{note}</small></div>)}</div>;
      break;
    }
    case 'tasks':
    case 'overdue': content = <><p className="data-note">Incomplete tasks ranked by critical override, then DTPS. Completed work appears last. Priority badges are manually assigned; DTPS is calculated separately.</p><TaskTable tasks={card.id === 'overdue' ? overdue : filtered} onStatus={onStatus} pending={pending} onRefresh={onRefresh} />
      <button className="text-button" onClick={() => onNewTask()}><Icon name="plus" size={14} /> Create a task</button></>; break;
    case 'assistant': content = <Assistant state={assistant} onChange={onAssistantChange} onAsk={onAssistantAsk} />; break;
    case 'performance': content = <><Trend values={[48, 59, 54, 68, 64, 73, 78]} label="activity score" />
      <p className="data-note">Illustrative activity score; not calculated from live task data.</p></>; break;
    case 'client': content = <><div className="client-identity"><div className="client-logo">N</div><div><h3 className="client-name">{demo.client.name}</h3>
      <p className="muted">{demo.client.contact} · {demo.client.role}</p></div></div><dl className="details-list">
        <div><dt>Plan</dt><dd>{demo.client.plan} · {demo.client.seats} seats</dd></div>
        <div><dt>Health</dt><dd className="negative">{demo.client.health}</dd></div>
        <div><dt>Renewal</dt><dd>{demo.client.renewal}</dd></div>
        <div><dt>Meeting</dt><dd>{demo.client.meeting}</dd></div></dl></>; break;
    case 'communications': content = <div className="item-list">{demo.communications.map(item => <div className="list-item" key={item.from}>
      <div className="item-meta"><strong>{item.from}</strong><small>{item.when}</small></div><p>{item.text}</p></div>)}</div>; break;
    case 'issues': content = <div className="item-list">{demo.issues.map(item => <div className="list-item" key={item.title}>
      <div className="item-meta"><strong>{item.title}</strong><span className={`badge ${item.priority === 'High' ? 'warning' : ''}`}>{item.priority}</span></div>
      <p>{item.owner} · {item.status}</p></div>)}</div>; break;
    case 'usage': content = <><Trend values={demo.usage.after} comparison={demo.usage.before} label="active users" />
      <div className="trend-legend"><span><i className="legend-line" />Current week</span><span><i className="legend-line previous" />Previous week</span></div>
      <p className="event-note">{demo.usage.event}</p><p className="data-note">{demo.usage.note}</p></>; break;
    case 'cohorts': content = <div className="item-list">{demo.cohorts.map(item => <div className="list-item" key={item.name}>
      <div className="item-meta"><strong>{item.name}</strong><span className="negative">{Math.round((item.after - item.before) / item.before * 100)}%</span></div>
      <div className="cohort-bar"><i style={{ width: `${item.after / item.before * 100}%` }} /></div><p className="cohort-values">{item.before} <Icon name="arrow-right" size={13} /> {item.after} active users</p></div>)}</div>; break;
    case 'meeting': content = <><p className="meeting-goal">{demo.client.goal}</p><ol className="agenda">{demo.meeting.map((item, i) => <li key={item}>
      <span>{String(i + 1).padStart(2, '0')}</span><p>{item}</p></li>)}</ol></>; break;
    case 'blockers': content = <div className="item-list">{demo.blockers.map(item => <div className="list-item" key={item.title}>
      <strong>{item.title}</strong><p>{item.impact}</p><small>{item.owner}</small></div>)}</div>; break;
    case 'actions': content = <div className="action-list">{(demo.actions[mode] || demo.actions.custom).map((item, i) => <div key={item}>
      <span className="action-number">{i + 1}</span><p>{item}</p>
      <button className="text-button" onClick={() => onNewTask(item)} aria-label={`Create task: ${item}`}><Icon name="plus" size={13} /> Task</button></div>)}</div>; break;
    default: return null;
  }
  return <article className={`panel widget widget-${card.id}`}>
    <div className="panel-heading"><h2>{CARD_TITLES[card.id]}</h2><span className={`data-badge ${LIVE.has(card.id) ? 'live' : ''}`}>
      {card.id === 'assistant' ? 'Gemini' : LIVE.has(card.id) ? 'Live' : card.id === 'actions' ? 'Suggested' : 'Sample'}</span></div>
    {onPin && <div className="card-controls"><button className="text-button" aria-label={`Pin ${CARD_TITLES[card.id]}`} aria-pressed={pinned.includes(card.id)} onClick={() => onPin(card.id)}>{pinned.includes(card.id) ? 'Pinned' : 'Pin'}</button><button className="text-button" aria-label={`Move ${CARD_TITLES[card.id]} earlier`} onClick={() => onMove(card.id, -1)}>←</button><button className="text-button" aria-label={`Move ${CARD_TITLES[card.id]} later`} onClick={() => onMove(card.id, 1)}>→</button></div>}
    <div className="widget-body">{content}</div>
    <details className="why-card" open={showWhy || undefined}><summary>Why this card?</summary><p>{card.reason}</p></details>
  </article>;
}
