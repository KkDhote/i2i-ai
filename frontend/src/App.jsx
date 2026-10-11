import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api } from './api';
import Widget from './Widgets';
import GoalWorkspace from './GoalWorkspace';
import ReasoningPanel from './ReasoningPanel';
import { preserveCards } from './layout';
import Icon from './Icon';
import './App.css';

const GOALS = [
  { key: 'meeting', icon: 'calendar', label: 'Prepare a client meeting', hint: 'Account, agenda & next steps', text: "Prepare for tomorrow's client meeting" },
  { key: 'usage', icon: 'chart', label: 'Investigate a usage drop', hint: 'Find where the numbers changed', text: 'Investigate why active users dropped' },
  { key: 'overdue', icon: 'clock', label: 'Review overdue work', hint: 'Clear blockers & move work forward', text: 'Review overdue project work' },
];
const EASE = 'cubic-bezier(.25,.8,.25,1)';
const LAYOUT_DURATION = 720;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function App() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('i2i-theme') === 'multicolor' ? 'multicolor' : 'sage'; }
    catch { return 'sage'; }
  });
  const [data, setData] = useState(null);
  const [plan, setPlan] = useState(null);
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [clarification, setClarification] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [source, setSource] = useState('');
  const [summary, setSummary] = useState('');
  const [history, setHistory] = useState([]);
  const [showWhy, setShowWhy] = useState(false);
  const [leaving, setLeaving] = useState([]);
  const [changed, setChanged] = useState([]);
  const [taskForm, setTaskForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [pending, setPending] = useState([]);
  const [retry, setRetry] = useState(0);
  const [proposal, setProposal] = useState(null);
  const [layoutHistory, setLayoutHistory] = useState([]);
  const [pinned, setPinned] = useState(() => { try { const saved = JSON.parse(localStorage.getItem('i2i-pins') || '[]'); return Array.isArray(saved) ? saved.filter(x => typeof x === 'string') : []; } catch { return []; } });
  const [budget, setBudget] = useState(() => { try { const saved = Number(localStorage.getItem('i2i-budget')); return [4, 6, 10].includes(saved) ? saved : 10; } catch { return 10; } });
  const [editedCard, setEditedCard] = useState(null);
  const [assistant, setAssistant] = useState({ question: '', answer: '', error: '', busy: false });
  const grid = useRef(null), elements = useRef(new Map());
  const snapshot = useRef(null), planRef = useRef(null), leaveTimer = useRef(null);
  const requestNumber = useRef(0), requestController = useRef(null);
  const assistantController = useRef(null);
  const animations = useRef([]), formInput = useRef(null);

  useEffect(() => {
    try { localStorage.setItem('i2i-theme', theme); }
    catch { /* The theme still works when browser storage is unavailable. */ }
  }, [theme]);
  useEffect(() => { try { localStorage.setItem('i2i-pins', JSON.stringify(pinned)); localStorage.setItem('i2i-budget', String(budget)); } catch { /* In-memory controls remain available. */ } }, [pinned, budget]);

  function apply(result) {
    const previous = planRef.current, next = result.plan;
    const oldCards = new Map(previous?.components.map(c => [c.id, c]) || []);
    const newCards = new Map(next.components.map(c => [c.id, c]));
    const positions = new Map(), bounds = grid.current?.getBoundingClientRect();
    // Capture current visual positions before cancelling any running animations.
    elements.current.forEach((el, id) => {
      const r = el.getBoundingClientRect();
      positions.set(id, { left: r.left, top: r.top, width: r.width, height: r.height, opacity: getComputedStyle(el).opacity });
    });
    snapshot.current = { positions, height: bounds?.height };
    animations.current.forEach(a => a.cancel());
    clearTimeout(leaveTimer.current);
    const removed = previous?.components.filter(c => !newCards.has(c.id)) || [];
    setLeaving(reducedMotion() || !bounds ? [] : removed.map(card => ({
      card, rect: positions.get(card.id), left: positions.get(card.id)?.left - bounds.left,
      top: positions.get(card.id)?.top - bounds.top,
    })).filter(item => item.rect));
    leaveTimer.current = setTimeout(() => setLeaving([]), 340);
    const additions = next.components.filter(c => !oldCards.has(c.id));
    const updates = next.components.filter(c => oldCards.has(c.id) &&
      (oldCards.get(c.id).span !== c.span || oldCards.get(c.id).reason !== c.reason));
    setChanged([...additions, ...updates].map(c => c.id));
    if (previous) {
      const description = `${additions.length} added · ${removed.length} removed · ${next.components.length - additions.length} retained`;
      setHistory(h => [{ title: next.title, description }, ...h].slice(0, 3));
    }
    planRef.current = next;
    setPlan(next); setSource(result.source); setSummary(result.summary || '');
    setClarification(null); setError('');
  }

  useLayoutEffect(() => {
    if (!plan || !grid.current || reducedMotion()) return;
    const captured = snapshot.current, running = [];
    let entering = 0;
    plan.components.forEach(card => {
      const el = elements.current.get(card.id);
      if (!el) return;
      const old = captured?.positions.get(card.id), rect = el.getBoundingClientRect();
      if (old) {
        const dx = old.left - rect.left, dy = old.top - rect.top;
        const sx = old.width / rect.width, sy = old.height / rect.height;
        if (dx || dy || sx !== 1 || sy !== 1 || Number(old.opacity) < 1) running.push(el.animate([
          { opacity: old.opacity, transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`, transformOrigin: 'top left' },
          { opacity: 1, transform: 'none', transformOrigin: 'top left' },
        ], { duration: LAYOUT_DURATION, easing: EASE }));
      } else running.push(el.animate([
        { opacity: 0, transform: 'translateY(12px) scale(.99)' },
        { opacity: 1, transform: 'none' },
      ], { duration: 560, delay: (captured?.positions.size ? 100 : 0) + Math.min(entering++ * 45, 135), easing: EASE, fill: 'backwards' }));
    });
    const height = grid.current.getBoundingClientRect().height;
    if (captured?.height && captured.height !== height) running.push(grid.current.animate(
      [{ height: `${captured.height}px` }, { height: `${height}px` }], { duration: LAYOUT_DURATION, easing: EASE }));
    animations.current = running;
    return () => running.forEach(a => a.cancel());
  }, [plan]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api('/data', { signal: controller.signal }),
      api('/intent', { method: 'POST', body: JSON.stringify({ pick: 'home' }), signal: controller.signal }),
    ]).then(([workspace, result]) => { setData(workspace); apply(workspace.goal ? { ...result, plan: workspace.goal.layout, summary: 'Resumed your saved goal plan.' } : result); })
      .catch(err => { if (err.name !== 'AbortError') setError('Cannot reach the backend. Start FastAPI, then retry.'); });
    return () => controller.abort();
  }, [retry]);

  useEffect(() => () => {
    requestController.current?.abort(); clearTimeout(leaveTimer.current);
    assistantController.current?.abort();
    animations.current.forEach(a => a.cancel());
  }, []);
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const stop = () => {
      if (preference.matches) {
        animations.current.forEach(a => a.cancel());
        setLeaving([]);
      }
    };
    preference.addEventListener('change', stop);
    return () => preference.removeEventListener('change', stop);
  }, []);
  useEffect(() => { if (taskForm) formInput.current?.focus(); }, [taskForm]);

  async function arrange(body) {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    const number = ++requestNumber.current;
    setBusy(true); setError(''); setClarification(null);
    try {
      const result = await api('/intent?preview=true', { method: 'POST', signal: controller.signal,
        body: JSON.stringify({ ...body, current: planRef.current }) });
      if (number !== requestNumber.current) return;
      if (result.status === 'plan') {
        result.plan = preserveCards(result.plan, planRef.current, [...pinned, editedCard]);
        setProposal({ result, intent: body.text || body.pick || result.plan.title, patch: result.op === 'patch' });
      } else setClarification(result);
    } catch (err) {
      if (err.name !== 'AbortError' && number === requestNumber.current) setError(err.message);
    } finally { if (number === requestNumber.current) setBusy(false); }
  }

  async function commitLayout(next, restoring = false) {
    if (busy) return;
    requestController.current?.abort();
    const number = ++requestNumber.current;
    const previousLayout = planRef.current ? { result: { plan: planRef.current }, goalId: data?.goal?.id, patch: true } : null;
    setBusy(true); setError('');
    try {
      const result = await api('/layout/commit', { method: 'POST', body: JSON.stringify({ plan: next.result.plan, intent: next.intent, patch: next.patch, goal_id: next.goalId || null }) });
      const workspace = await api('/data');
      if (number !== requestNumber.current) return;
      if (!restoring && previousLayout) setLayoutHistory(items => [...items, previousLayout].slice(-10));
      if (restoring) setLayoutHistory(items => items.slice(0, -1));
      setData(workspace); apply(result); setProposal(null);
      setText(value => value === next.intent ? '' : value);
    } catch (err) { setError(err.message); }
    finally { if (number === requestNumber.current) setBusy(false); }
  }
  function moveCard(id, direction) {
    const cards = [...planRef.current.components], index = cards.findIndex(card => card.id === id);
    const target = index + direction;
    if (target < 0 || target >= cards.length) return;
    [cards[index], cards[target]] = [cards[target], cards[index]];
    commitLayout({ result: { plan: { ...planRef.current, components: cards } }, goalId: data?.goal?.id, patch: true });
  }
  function focusProgress() {
    const preferred = data.goal.stage === 'Completion review' ? ['actions', 'meeting', 'assistant'] : data.goal.mode === 'usage' ? ['usage', 'cohorts', 'issues', 'assistant'] : data.goal.mode === 'meeting' ? ['client', 'issues', 'meeting'] : ['overdue', 'tasks', 'blockers'];
    const cards = [...planRef.current.components].sort((a, b) => (preferred.includes(b.id) ? 1 : 0) - (preferred.includes(a.id) ? 1 : 0));
    const next = preserveCards({ ...planRef.current, components: cards }, planRef.current, [...pinned, editedCard]);
    setProposal({ result: { plan: next, summary: `Focus on ${data.goal.stage.toLowerCase()} based on saved goal progress.` }, goalId: data.goal.id, patch: true });
  }

  async function askAssistant(question) {
    question = question.trim();
    if (!question || assistantController.current) return;
    const controller = new AbortController();
    assistantController.current = controller;
    setAssistant(current => ({ ...current, question, error: '', busy: true }));
    try {
      const result = await api('/ai/ask', { method: 'POST', signal: controller.signal,
        body: JSON.stringify({ question, mode: planRef.current.mode }) });
      setAssistant(current => ({ ...current, answer: result.answer,
        question: current.question === question ? '' : current.question }));
    } catch (error) {
      if (error.name !== 'AbortError') setAssistant(current => ({ ...current, error: error.message }));
    } finally {
      assistantController.current = null;
      setAssistant(current => ({ ...current, busy: false }));
    }
  }

  function newTask(title = '', goalStepId = null) { setTaskForm({ title, goalStepId, description: '', priority: 'Medium', owner: '', team: '', due_date: '' }); }
  async function refreshGoal() { setData(await api('/data')); }

  async function createTask(event) {
    event.preventDefault();
    if (saving || !taskForm.title.trim()) return;
    setSaving(true);
    try {
      const task = await api('/tasks', { method: 'POST', body: JSON.stringify({ ...taskForm,
        team: taskForm.team || 'General', owner: taskForm.owner || 'Unassigned', due_date: taskForm.due_date || null }) });
      if (taskForm.goalStepId) await api(`/goal-steps/${taskForm.goalStepId}`, { method: 'PATCH', body: JSON.stringify({ task_id: task.id }) });
      setTaskForm(null); setNotice('Task created.'); setData(await api('/data'));
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }

  async function changeStatus(id, status) {
    if (pending.includes(id)) return;
    setPending(ids => [...ids, id]);
    try {
      await api(`/tasks/${id}?${new URLSearchParams({ status })}`, { method: 'PATCH' });
      setData(await api('/data')); setNotice('Task status updated.');
    } catch (err) { setError(err.message); }
    finally { setPending(ids => ids.filter(item => item !== id)); }
  }

  const sourceLabel = source === 'gemini' ? 'Arranged with Gemini' : source === 'rules' ? 'Arranged with demo rules' : 'Preset workspace';
  const focusLabel = { home: 'Overview', meeting: 'Meeting preparation', usage: 'Product insights', overdue: 'Project follow-up', custom: 'Your focus' }[plan?.mode] || 'Overview';
  const workspaceDate = data?.today && new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'long' }).format(new Date(`${data.today}T12:00:00`));
  const widgetProps = { data, mode: plan?.mode, showWhy, query, onStatus: changeStatus, onNewTask: newTask, pending,
    assistant, onAssistantChange: setAssistant, onAssistantAsk: askAssistant, onRefresh: refreshGoal, pinned,
    onPin: id => setPinned(ids => ids.includes(id) ? ids.filter(item => item !== id) : [...ids, id]), onMove: moveCard };
  const visibleCards = plan?.components.filter((card, index) => index < budget || pinned.includes(card.id) || card.id === editedCard) || [];

  return <div className="app-shell adaptive-template" data-theme={theme}>
    <aside className="sidebar intent-sidebar">
      <a className="brand" href="#workspace" onClick={event => { event.preventDefault(); if (data) arrange({ pick: 'home' }); }}>
        <span className="brand-mark"><Icon name="layers" size={23} /></span><span><strong>I2I<span className="brand-period">.</span></strong><small>Intent to interface</small></span></a>
      <div className="template-intro"><span className="eyebrow">A WORKSPACE THAT LISTENS</span><h2>Start with{' '}<br />what matters.</h2><p>Tell us what you want to get done. We’ll bring the right tools into view.</p></div>
        <section className={`intent-bar ${busy ? 'is-planning' : ''}`} aria-label="Adaptive workspace controls">
          <div className="intent-label"><strong>Your goal</strong><span>01 / INTENT</span></div>
          <form className="goal-form" onSubmit={e => { e.preventDefault(); if (text.trim() && data) arrange({ text }); }}>
            <textarea aria-label="Workspace goal" rows={3} placeholder="I need to prepare for tomorrow’s client meeting…" value={text} onChange={e => setText(e.target.value)} maxLength={2000}
              onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (text.trim() && data) arrange({ text }); } }} />
            <button className="primary-button" disabled={!data || !text.trim()} type="submit"><span>{busy ? 'Update my goal' : 'Shape my workspace'}</span><Icon name="arrow-right" size={17} /></button>
          </form>
          <div className="goal-examples"><span className="section-label">OR START HERE</span><div className="goal-options">{GOALS.map(goal => <button aria-label={goal.label} disabled={!data} className={`goal-option ${plan?.mode === goal.key ? 'selected' : ''}`} key={goal.key} onClick={() => arrange({ text: goal.text })}><span className="goal-icon"><Icon name={goal.icon} /></span><span className="goal-option-copy"><strong>{goal.label}</strong><small>{goal.hint}</small></span><Icon name="arrow-right" size={14} /></button>)}</div></div>
          {plan && plan.mode !== 'home' && <div className="refine-row"><span>Refine this view</span>{['Also show overdue tasks', 'Also show open issues', 'Remove next actions'].map(label => <button className="chip refine-chip" key={label} onClick={() => arrange({ text: label })}>{label}</button>)}</div>}
          <div className="planning-status" role="status" aria-live="polite">{busy ? <><span className="planning-spinner" />Arranging your workspace. You can keep working.</> : <><span className="live-dot" />{sourceLabel}</>}</div>
        </section>
        {clarification && <div className="clarification" role="status"><strong>{clarification.message}</strong><div className="goal-chips">{clarification.options.map(option => <button className="chip" key={option.key} onClick={() => arrange({ pick: option.key })}>{option.label}</button>)}</div></div>}
        {plan && <div className="current-intent"><span className="eyebrow">CURRENT FOCUS</span><strong><span className="live-dot" />{plan.mode === 'home' ? 'The bigger picture' : plan.title}</strong><p>{plan.mode === 'home' ? 'A good place to start. Pick a goal when you’re ready.' : 'Your tools are arranged around this goal.'}</p></div>}
        <div className="sidebar-history"><h2>Recent changes</h2>{history.length ? <ol>{history.map((item, i) => <li key={i}><strong>{item.title}</strong><span>{item.description}</span></li>)}</ol> : <p>A new goal, a fresh arrangement.<br />Your changes will appear here.</p>}</div>
        <div className="template-footer"><span><Icon name="grid" size={16} /> Made for the way you work</span><small>{data?.ai_configured ? 'Gemini configured' : 'Demo rules available'}<span>HACKWAVE 3.0</span></small></div>
    </aside>
    <main className="main-area" id="workspace">
      <div className="dashboard-content">
        <div className="workspace-topline"><span><Icon name="grid" size={16} /> Workspace <span className="breadcrumb-divider">/</span><strong>{focusLabel}</strong></span><div className="workspace-details"><time dateTime={data?.today}>{workspaceDate || 'Your workspace'}</time><div className="theme-picker" role="group" aria-label="Page theme"><button aria-label="Use present green theme" aria-pressed={theme === 'sage'} onClick={() => setTheme('sage')}><span className="theme-swatch sage-swatch" aria-hidden="true" />Green</button><button aria-label="Use dark grey theme" title="Dark grey with red, yellow, green and light-blue accents" aria-pressed={theme === 'multicolor'} onClick={() => setTheme('multicolor')}><span className="theme-swatch combined-swatch" aria-hidden="true"><i /><i /><i /><i /><i /></span>Dark grey</button></div></div></div>
        <div className="welcome-row"><div className="welcome-copy"><div className="eyebrow">{plan?.mode === 'home' ? 'A LITTLE CLARITY FOR YOUR DAY' : 'ONE GOAL. THE RIGHT TOOLS.'}</div>
          <h1>{plan?.mode === 'home' ? 'Your work, in focus.' : plan?.title || 'Your work, in focus.'}</h1><p className="subtitle">{plan?.mode === 'home' ? 'The big picture, the details, and a little help with what comes next.' : plan?.desc || 'Loading your workspace…'}</p></div>
          <div className="canvas-controls">{plan && !plan.components.some(card => card.id === 'assistant') && <button className="cancel-button" onClick={() => arrange({ text: 'Also show AI assistant' })}><Icon name="message" size={16} />Ask I2I AI</button>}<button className="cancel-button" aria-label="Back to dashboard" disabled={!data} onClick={() => arrange({ pick: 'home' })}><Icon name="grid" size={16} />Overview</button><button className="primary-button" disabled={!data} onClick={() => newTask()}><Icon name="plus" size={17} />New task</button></div></div>
        <div className="canvas-toolbar"><label className="search-box"><Icon name="search" size={17} /><input aria-label="Search tasks" placeholder="Find a task…" value={query} onChange={e => setQuery(e.target.value)} /></label>
          <button className="text-button reasons-button" aria-pressed={showWhy} onClick={() => setShowWhy(v => !v)}><Icon name="layers" size={16} />{showWhy ? 'Hide card reasons' : 'Why these cards?'}</button></div>
        <div className="layout-tools"><button className="cancel-button" disabled={busy || !layoutHistory.length} onClick={() => commitLayout(layoutHistory.at(-1), true)}>Undo layout</button><label>Attention budget <select aria-label="Visible card limit" value={budget} onChange={e => setBudget(Number(e.target.value))}><option value={4}>4 cards</option><option value={6}>6 cards</option><option value={10}>All cards</option></select></label>{editedCard && <button className="text-button" onClick={() => setEditedCard(null)}>Release active card</button>}<span className="data-note">Pinned and active cards keep their slots.</span></div>
        {proposal && <section className="panel layout-preview" aria-label="Workspace change preview"><h2>Review workspace changes</h2><p>{proposal.result.summary || 'Apply this arrangement to your current goal.'}</p><ol>{proposal.result.plan.components.map((card, index) => { const old = plan?.components.findIndex(c => c.id === card.id) ?? -1; return <li key={card.id}><strong>{card.id}</strong> · {old < 0 ? 'Add' : old !== index ? `Move from ${old + 1} to ${index + 1}` : 'Keep'} · {card.reason}</li>; })}</ol>{plan?.components.filter(c => !proposal.result.plan.components.some(n => n.id === c.id)).map(c => <p key={c.id}>Remove {c.id}: omitted from the proposed arrangement.</p>)}<div className="review-buttons"><button className="primary-button" disabled={busy} onClick={() => commitLayout(proposal)}>Apply reviewed layout</button><button className="cancel-button" onClick={() => setProposal(null)}>Keep current workspace</button></div></section>}
        {error && <div className="error-notice" role="alert"><span>{error}</span>{!data && <button className="text-button" onClick={() => { setError(''); setRetry(n => n + 1); }}>Retry</button>}<button className="dismiss" aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
        {notice && <div className="notice" role="status"><span>✓ {notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}>×</button></div>}
        {taskForm && <form className="task-form" onSubmit={createTask} aria-label="Create a task"><div className="task-form-heading"><strong>Create a task</strong><p>Give the next step an owner and a date.</p></div>
          <input ref={formInput} aria-label="Task title" placeholder="Task title" required maxLength={200} value={taskForm.title} onChange={e => setTaskForm({ ...taskForm, title: e.target.value })} />
          <input aria-label="Task assignee" placeholder="Assignee" maxLength={80} value={taskForm.owner} onChange={e => setTaskForm({ ...taskForm, owner: e.target.value })} />
          <input aria-label="Task description" placeholder="Description (optional)" maxLength={2000} value={taskForm.description} onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} />
          <label className="date-field">Priority<select aria-label="Task priority" value={taskForm.priority} onChange={e => setTaskForm({ ...taskForm, priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option><option>Critical</option></select></label>
          <input aria-label="Task team" placeholder="Team" maxLength={80} value={taskForm.team} onChange={e => setTaskForm({ ...taskForm, team: e.target.value })} />
          <label className="date-field">Due date<input aria-label="Task due date" type="date" value={taskForm.due_date} onChange={e => setTaskForm({ ...taskForm, due_date: e.target.value })} /></label>
          <button className="primary-button" disabled={saving}>{saving ? 'Saving…' : 'Add task'}</button><button className="cancel-button" type="button" disabled={saving} onClick={() => setTaskForm(null)}>Cancel</button></form>}
        {plan && data && <>
          <div className="layout-context"><span className="context-icon"><Icon name="check" size={14} /></span><p aria-live="polite"><strong>{plan.components.length} cards, one workspace.</strong> {summary}</p></div>
          <GoalWorkspace key={data.goal?.id || 'no-goal'} goal={data.goal} tasks={data.tasks} onRefresh={refreshGoal} onNewTask={newTask} />
          {data.goal && <ReasoningPanel key={data.goal.id} goal={data.goal} onRefresh={refreshGoal} onNewTask={newTask} onFocusProgress={focusProgress} />}
          <div className="adaptive-grid" ref={grid} aria-busy={busy}>
            {visibleCards.map(card => <div key={card.id} data-card={card.id} className={`widget-slot ${changed.includes(card.id) ? 'card-changed' : ''}`} style={{ '--span': card.span }} onFocusCapture={e => { if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) setEditedCard(card.id); }}
              ref={el => { if (el) elements.current.set(card.id, el); else elements.current.delete(card.id); }}><Widget card={card} {...widgetProps} /></div>)}
            {leaving.map(item => <div className="leaving-card" key={`leaving-${item.card.id}`} aria-hidden="true" inert={true}
              style={{ left: item.left, top: item.top, width: item.rect.width, height: item.rect.height }}>
              <Widget card={item.card} {...widgetProps} onStatus={() => {}} onNewTask={() => {}} /></div>)}
          </div>
          <p className="sample-note">A note on the numbers: tasks are live. Client, usage and blocker details are sample data for this demo.</p>
        </>}
        {!data && !error && <div className="loading-workspace" role="status"><span className="planning-spinner" />Loading workspace…</div>}
        <footer className="footer"><span>I2I · Intelligence to Impact</span><span><span className="live-dot" />{data ? 'Workspace loaded' : 'Connecting to workspace'}</span></footer>
      </div>
    </main>
  </div>;
}
