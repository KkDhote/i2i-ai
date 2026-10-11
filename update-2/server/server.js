import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import mongoose from 'mongoose';
import { layouts } from './catalog.js';
import { decide, patchByRules } from './intent.js';
import { curated, patchPlan } from './plan.js';
import { planWithLLM } from './llm.js';
import { loadData } from './store.js';

const app = express();
app.use(cors());
app.use(express.json());

mongoose.connect(process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/intent_workspace', { serverSelectionTimeoutMS: 2000 })
  .then(() => console.log('MongoDB connected'))
  .catch(() => console.log('MongoDB not available: using seed file'));

app.get('/api/health', (_, res) => res.json({ ok: true, llm: !!process.env.ANTHROPIC_API_KEY }));
app.get('/api/data', async (_, res) => res.json(await loadData()));

const WARM = ["Prepare for tomorrow's client meeting", 'Investigate why active users dropped', 'Review overdue project work'];

app.post('/api/intent', async (req, res) => {
  const { text = '', pick, current } = req.body || {};
  if (pick && layouts[pick]) return res.json(curated(pick, { confidence: 0.8, source: 'user-pick' }));
  if (!text.trim()) return res.status(400).json({ error: 'text is required' });

  if (process.env.ANTHROPIC_API_KEY) {
    try { return res.json(await planWithLLM(text, WARM.includes(text.trim()) ? null : current)); }
    catch (e) { console.warn('LLM failed, using rules:', e.message); }
  }
  // Rules fallback: refinement first, then new intent
  const patch = patchByRules(text, current?.components);
  if (patch) return res.json(patchPlan(current, patch, { source: 'rules' }));
  const d = decide(text);
  if (d.type === 'clarify') return res.json({ status: 'clarify', message: d.message, options: d.keys.map(k => ({ key: k, label: layouts[k].name })) });
  res.json(curated(d.key, { hits: d.hits, confidence: d.confidence, source: 'rules' }));
});

const port = process.env.PORT || 5001;
app.listen(port, () => {
  console.log('Server on http://localhost:' + port);
  if (process.env.ANTHROPIC_API_KEY) WARM.forEach(t => planWithLLM(t, null).catch(() => {}));  // pre-warm: demo prompts answer instantly
});
