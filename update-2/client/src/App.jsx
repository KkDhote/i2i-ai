import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api } from './api';
import Widget from './registry.jsx';

const EXAMPLES = ["Prepare for tomorrow's client meeting", 'Investigate why active users dropped', 'Review overdue project work', 'Client usage'];
const REFINE = ['Also show overdue tasks', 'Also show open issues', 'Remove next actions'];
const sig = c => c.span + '|' + (c.variant || '');
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const EASE = 'cubic-bezier(.2,.8,.2,1)';

export default function App() {
  const [data, setData] = useState(null);
  const [view, setView] = useState(null);       // { plan, comps (with status), delta, summary }
  const [leaving, setLeaving] = useState([]);   // ghosts of removed components, fade out in place
  const [intent, setIntent] = useState(null);
  const [clar, setClar] = useState(null);
  const [log, setLog] = useState([]);
  const [text, setText] = useState('');
  const [whyAll, setWhyAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [toast, setToast] = useState('');
  const viewRef = useRef(null), gridRef = useRef(null), timer = useRef(null);
  const els = useRef(new Map()), oldRects = useRef(new Map());
  const setRef = id => el => { if (el) els.current.set(id, el); else els.current.delete(id); };

  // Positions of every widget relative to the grid (taken BEFORE the layout changes).
  const measure = () => {
    const m = new Map();
    if (!gridRef.current) return m;
    const g = gridRef.current.getBoundingClientRect();
    els.current.forEach((el, id) => { const r = el.getBoundingClientRect(); m.set(id, { x: r.left - g.left, y: r.top - g.top, w: r.width, h: r.height }); });
    return m;
  };

  const apply = (res) => {
    setClar(null); setErr('');
    const old = viewRef.current;
    oldRects.current = old ? measure() : new Map();
    const prev = new Map((old?.comps || []).map(c => [c.id, sig(c)]));
    const comps = res.plan.components.map(c => ({
      ...c, status: !old ? 'first' : !prev.has(c.id) ? 'new' : prev.get(c.id) !== sig(c) ? 'upd' : 'kept' }));
    const removed = old ? old.comps.filter(o => !comps.some(c => c.id === o.id)) : [];
    setLeaving(reduced() ? [] : removed.map(c => ({ c, r: oldRects.current.get(c.id) })).filter(x => x.r));
    clearTimeout(timer.current); timer.current = setTimeout(() => setLeaving([]), 480);
    const n = s => comps.filter(c => c.status === s).length;
    const next = { plan: res.plan, comps, summary: res.summary || '',
      delta: old ? `Rearranged: ${n('new')} new, ${n('upd')} updated, ${n('kept')} unchanged, ${removed.length} removed.` : '' };
    viewRef.current = next; setView(next); setIntent(res.intent);
    if (old) setLog(l => [`${res.op === 'patch' ? 'Refined' : 'To "' + res.intent.name + '"'}: +${comps.filter(c => c.status === 'new').map(c => c.def.title).join(', ') || 'none'}; removed ${removed.map(c => c.def.title).join(', ') || 'none'}`, ...l].slice(0, 4));
  };

  // FLIP: kept widgets glide from their old spot to the new one; new widgets fly in; changed ones glow.
  useLayoutEffect(() => {
    if (!view || !gridRef.current || reduced()) return;
    const g = gridRef.current.getBoundingClientRect();
    view.comps.forEach((c, i) => {
      const el = els.current.get(c.id);
      if (!el || c.status === 'first') return;
      const o = oldRects.current.get(c.id), r = el.getBoundingClientRect();
      if (o && c.status !== 'new') {
        const dx = o.x - (r.left - g.left), dy = o.y - (r.top - g.top);
        if (dx || dy) el.animate([{ transform: `translate(${dx}px,${dy}px)` }, { transform: 'none' }], { duration: 650, easing: EASE });
      } else {
        el.animate([{ opacity: 0, transform: 'translate(-28px,16px) scale(.96)' }, { opacity: 1, transform: 'none' }],
          { duration: 560, delay: i * 70, easing: EASE, fill: 'backwards' });
      }
      if (c.status === 'new' || c.status === 'upd')
        el.animate([{ boxShadow: '0 0 0 3px var(--acc)' }, { boxShadow: '0 0 0 0 transparent' }], { duration: 2600, delay: 300, easing: 'ease-out' });
    });
  }, [view]);

  const ask = async (body) => {
    setBusy(true); setErr('');
    const v = viewRef.current;
    const current = v && { mode: v.plan.mode, title: v.plan.title, desc: v.plan.desc, components: v.comps.map(({ id, span, reason }) => ({ id, span, reason })) };
    try {
      const res = await api.intent({ ...body, current });
      if (res.status === 'clarify' || res.status === 'unsupported') setClar(res); else apply(res);
    } catch (e) { setErr('Could not reach the server: ' + e.message); }
    setBusy(false);
  };

  useEffect(() => { api.data().then(setData).catch(e => setErr(e.message)); ask({ pick: 'home' }); }, []);
  const act = (name) => { setToast(name + ': queued (demo)'); setTimeout(() => setToast(''), 1800); };
  const submit = (e) => { e.preventDefault(); if (text.trim()) { ask({ text }); setText(''); } };
  const run = (t) => { ask({ text: t }); };
  const mode = view?.plan.mode;

  return (
    <div className="app">
      <aside>
        <div><h1>Intent-to-Interface</h1><p className="sub">Say what you need. The workspace rebuilds itself around it.</p></div>
        <form onSubmit={submit}>
          <label htmlFor="q">What are you trying to do?</label>
          <div className="ask">
            <input id="q" value={text} onChange={e => setText(e.target.value)} autoComplete="off" placeholder="e.g. Prepare tomorrow's client meeting" />
            <button className="btn" disabled={busy}>{busy ? '...' : 'Go'}</button>
          </div>
          <div className="chips">{EXAMPLES.map(x => <button type="button" key={x} className="chip" onClick={() => run(x)}>{x}</button>)}</div>
          {mode && mode !== 'home' && <>
            <label style={{ display: 'block', marginTop: 12 }}>Refine this screen</label>
            <div className="chips">{REFINE.map(x => <button type="button" key={x} className="chip" onClick={() => run(x)}>{x}</button>)}</div></>}
        </form>
        {busy && <p className="sub" role="status">AI is arranging your screen...</p>}
        {clar && <div className="clar" role="status"><b>{clar.message}</b>
          <div className="chips">{clar.options.map(o => <button key={o.key} className="chip" onClick={() => ask({ pick: o.key })}>{o.label}</button>)}</div></div>}
        {err && <div className="clar" role="alert">{err}</div>}
        {intent && <div className="intent" role="status">
          <b>{intent.key === 'home' ? 'No task set' : intent.name}</b>
          {intent.key !== 'home' && <><div className="meter" aria-hidden="true"><i style={{ width: Math.round(intent.confidence * 100) + '%' }} /></div>
            <div>Confidence {Math.round(intent.confidence * 100)}%{intent.hits.length ? '. Matched: ' + intent.hits.join(', ') : ''}.
              {' '}Planned by {intent.source === 'llm' ? (intent.cached ? 'AI (instant, cached)' : `AI in ${(intent.ms / 1000).toFixed(1)}s`) : intent.source === 'user-pick' ? 'your choice' : 'rules'}.</div></>}
        </div>}
        {view && <details><summary>View plan JSON</summary>
          <pre>{JSON.stringify(view.comps.map(({ id, span, reason, variant }) => ({ id, span, reason, variant })), null, 1)}</pre></details>}
        <div><h2 className="small">What changed</h2><ol className="log">{log.map((x, i) => <li key={i}>{x}</li>)}</ol></div>
      </aside>
      <main>
        {view && data && <>
          <div className="head">
            <div><h2 className="big">{view.plan.title}</h2><p className="sub">{view.plan.desc}</p></div>
            <div className="tools">
              <button className="btn ghost sm" aria-pressed={whyAll} onClick={() => setWhyAll(v => !v)}>{whyAll ? 'Hide all reasons' : 'Show all reasons'}</button>
              <button className="btn ghost sm" onClick={() => ask({ pick: 'home' })}>Back to dashboard</button>
            </div>
          </div>
          {view.summary && <p className="note" role="status"><b>AI note:</b> {view.summary}</p>}
          <div className="delta" role="status">{view.delta}</div>
          <div className="grid" ref={gridRef}>
            {view.comps.map((c, i) => <Widget key={c.id} c={c} index={i} data={data} showWhy={whyAll} onAct={act} refCb={setRef(c.id)} />)}
            {leaving.map(({ c, r }) => (
              <div key={'g-' + c.id} className="ghost" aria-hidden="true" style={{ left: r.x, top: r.y, width: r.w, height: r.h }}>
                <Widget c={{ ...c, status: 'kept' }} index={0} data={data} showWhy={false} onAct={() => {}} refCb={null} />
              </div>))}
          </div>
        </>}
        {!data && !err && <p className="sub">Loading workspace...</p>}
      </main>
      {toast && <div className="toast on" role="status">{toast}</div>}
    </div>
  );
}
