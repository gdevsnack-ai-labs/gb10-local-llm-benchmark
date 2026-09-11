import React, { useEffect, useState, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API = import.meta.env.VITE_API_BASE_URL || '/api';

type Run = { id: string; suite: string; status: string; created_at: string; started_at?: string; finished_at?: string; recipe?: string; config: any; summary: any; error?: string };
type Recipe = { name: string; suite: string; config: any; raw: any };
type Variant = { path: string; family: string; quant: string; tags: string };

function BarChart({ data, valueKey = 'value', labelKey = 'label', unit = '' }: { data: any[]; valueKey?: string; labelKey?: string; unit?: string }) {
  if (!data || data.length === 0) return <p style={{ color: '#8f9bad' }}>No data</p>;
  const max = Math.max(...data.map(d => d[valueKey] || 0)) || 1;
  const w = 520, h = 14 * data.length + 30, barH = 18, gap = 8;
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ background: '#0d1117', borderRadius: 8, padding: 8 }}>
      {data.map((d, i) => {
        const v = d[valueKey] || 0;
        const bw = Math.max(4, (v / max) * (w - 140));
        const y = 10 + i * (barH + gap);
        return (
          <g key={i}>
            <text x={0} y={y + 13} fontSize={11} fill="#b9c8da">{String(d[labelKey]).slice(0, 18)}</text>
            <rect x={120} y={y} width={bw} height={barH} rx={4} fill={d.suite === 'failed' ? '#ff6b6b' : '#4cc38a'} />
            <text x={120 + bw + 6} y={y + 13} fontSize={11} fill="#edf2f7">{Math.round(v * 10) / 10} {unit}</text>
          </g>
        );
      })}
    </svg>
  );
}

function TelemetryChart({ points }: { points: any[] }) {
  if (points.length < 2) return <p style={{ color: '#8f9bad', fontSize: 12 }}>Telemetry 1s sampler (cpu/mem/gpu)</p>;
  const w = 520, h = 120, pad = 20;
  const maxCpu = Math.max(100, ...points.map(p => p.cpu_pct || 0));
  const maxMem = Math.max(...points.map(p => p.mem_pct || 0), 10);
  const xs = (i: number) => pad + (i / Math.max(1, points.length - 1)) * (w - pad * 2);
  const ysCpu = (v: number) => h - pad - (v / maxCpu) * (h - pad * 2);
  const ysMem = (v: number) => h - pad - (v / maxMem) * (h - pad * 2);
  const cpuPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xs(i)} ${ysCpu(p.cpu_pct || 0)}`).join(' ');
  const memPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xs(i)} ${ysMem(p.mem_pct || 0)}`).join(' ');
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ background: '#0d1117', borderRadius: 8 }}>
      <text x={pad} y={14} fontSize={10} fill="#4cc38a">CPU %</text>
      <text x={w - 60} y={14} fontSize={10} fill="#6ea8ff">MEM %</text>
      <path d={cpuPath} fill="none" stroke="#4cc38a" strokeWidth={1.6} />
      <path d={memPath} fill="none" stroke="#6ea8ff" strokeWidth={1.4} strokeDasharray="4 3" />
      {points.slice(-1).map(p => (
        <text key="lbl" x={pad} y={h - 4} fontSize={10} fill="#8f9bad">cpu {p.cpu_pct}% · mem {p.mem_pct}% · gpu {p.gpu_util_pct ?? '-' }%</text>
      ))}
    </svg>
  );
}

function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [system, setSystem] = useState<any>(null);
  const [suite, setSuite] = useState('performance');
  const [recipe, setRecipe] = useState('');
  const [model, setModel] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [concurrency, setConcurrency] = useState(4);
  const [managed, setManaged] = useState(true);
  const [thinkingMode, setThinkingMode] = useState<'auto' | 'think' | 'no-think'>('auto');
  const [thinkingBudget, setThinkingBudget] = useState(-1);
  const [maxTokens, setMaxTokens] = useState(512);
  const [requestTimeout, setRequestTimeout] = useState(300);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareRes, setCompareRes] = useState<any>(null);
  const [active, setActive] = useState<Run | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [telemetry, setTelemetry] = useState<any[]>([]);
  const [slots, setSlots] = useState<any>(null);
  const [detail, setDetail] = useState<Run | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [env, setEnv] = useState<any>(null);
  const [tab, setTab] = useState('metrics');
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const refresh = async () => {
    try { const r = await fetch(`${API}/runs`); setRuns(await r.json()); } catch {}
    try { const r = await fetch(`${API}/queue`); const j = await r.json(); setQueue(j.queued || []); } catch {}
  };
  const refreshRecipes = async () => { try { const r = await fetch(`${API}/recipes`); if (r.ok) setRecipes(await r.json()); } catch {} };
  const refreshSystem = async () => { try { const r = await fetch(`${API}/system`); if (r.ok) setSystem(await r.json()); } catch {} };
  const refreshVariants = async () => { try { const r = await fetch(`${API}/models`); if (r.ok) setVariants(await r.json()); } catch {} };
  const scanModels = async () => { try { const r = await fetch(`${API}/models/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); const j = await r.json(); alert(`scan: found ${j.found} upserted ${j.upserted}`); refreshVariants(); } catch (e:any){ alert(String(e)); } };

  useEffect(() => { refresh(); refreshRecipes(); refreshSystem(); refreshVariants(); const id = setInterval(refresh, 4000); return () => clearInterval(id); }, []);

  const openDetail = async (run: Run) => {
    setDetail(run); setMetrics(null); setEnv(null); setArtifacts([]);
    try {
      const [m, e, a] = await Promise.all([
        fetch(`${API}/runs/${run.id}/metrics`).then(r => r.json()).catch(() => null),
        fetch(`${API}/runs/${run.id}/environment`).then(r => r.json()).catch(() => null),
        fetch(`${API}/runs/${run.id}/artifacts`).then(r => r.json()).catch(() => null),
      ]);
      if (m) setMetrics(m);
      if (e && !e.detail) setEnv(e);
      if (a) setArtifacts(a.files || []);
    } catch {}
  };

  const launch = async () => {
    const config: any = {
      thinking_mode: thinkingMode,
      thinking_budget: thinkingMode === 'no-think' ? 0 : thinkingBudget,
      request_timeout_s: requestTimeout,
      max_tokens: maxTokens,
    };
    if (suite === 'performance') {
      Object.assign(config, { model_path: model, prompt_tokens: [512, 2048, 8192], gen_tokens: [maxTokens], repetitions: 3, n_gpu_layers: 99, flash_attn: true });
    } else if (suite === 'server-performance') {
      if (managed) Object.assign(config, { managed: true, model_path: model, concurrency, requests: concurrency * 4, gen_tokens: maxTokens });
      else Object.assign(config, { server_url: serverUrl, concurrency, requests: concurrency * 2, gen_tokens: maxTokens });
    } else if (['knowledge','coding','tool-call','agent-single','agent-multi'].includes(suite)) {
      Object.assign(config, { managed, model_path: model });
      if (!managed && serverUrl) config.server_url = serverUrl;
    }
    const body: any = { suite, recipe: recipe || null, config };
    try {
      const r = await fetch(`${API}/runs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!r.ok) { const t = await r.text(); alert(`Launch failed: ${t}`); return; }
      const run = await r.json();
      setActive(run); setEvents([]); setTelemetry([]); setSlots(null); setDetail(run); refresh();
      if (esRef.current) esRef.current.close();
      const es = new EventSource(`${API}/runs/${run.id}/events`);
      esRef.current = es;
      es.onmessage = e => {
        const ev = JSON.parse(e.data);
        setEvents(v => [...v.slice(-200), ev]);
        if (ev.type === 'telemetry') setTelemetry(v => [...v.slice(-60), ev.data]);
        if (ev.type === 'slots') setSlots(ev.data.slots || ev.data);
        if (ev.type === 'status' && ['completed', 'failed', 'cancelled'].includes(ev.data?.status)) {
          es.close(); refresh(); openDetail({ ...run, status: ev.data.status, summary: ev.data.summary || {} } as Run);
        }
      };
    } catch (e: any) { alert(String(e)); }
  };

  const doCompare = async () => {
    if (compareIds.length < 2) { alert('select at least 2 runs (checkbox)'); return; }
    try {
      const r = await fetch(`${API}/compare`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_ids: compareIds.slice(0,4) }) });
      const j = await r.json();
      if (!r.ok) { alert(JSON.stringify(j)); return; }
      setCompareRes(j);
    } catch (e:any){ alert(String(e)); }
  };

  const cancel = async () => {
    if (!active) return;
    try { const r = await fetch(`${API}/runs/${active.id}/cancel`, { method: 'POST' }); if (!r.ok) alert(await r.text()); else refresh(); } catch (e: any) { alert(String(e)); }
  };

  const perfChartData = (() => {
    if (!metrics) return [];
    const db = metrics.db || [];
    return db.filter((m: any) => m.name.includes('tps')).map((m: any) => ({ label: `${m.extra?.test || m.name} ${m.extra?.n_prompt || ''}/${m.extra?.n_gen || ''}`, value: m.value }));
  })();
  const serverLatency = detail?.summary?.latency_mean_s ? [
    { label: 'mean', value: (detail.summary.latency_mean_s * 1000) },
    { label: 'p50', value: (detail.summary.latency_p50_s || 0) * 1000 },
    { label: 'p95', value: (detail.summary.latency_p95_s || 0) * 1000 },
    { label: 'p99', value: (detail.summary.latency_p99_s || 0) * 1000 },
  ] : [];

  const summaryLine = (r: Run) => {
    const s: any = r.summary || {};
    const mode = r.config?.thinking_mode && r.config.thinking_mode !== 'auto' ? `[${r.config.thinking_mode}] ` : '';
    if (r.suite === 'knowledge') return `${mode}${s.correct}/${s.total} acc ${(s.pass_rate*100||0).toFixed(0)}%`;
    if (r.suite === 'coding') return `${mode}${s.passed}/${s.total} ${(s.pass_rate*100||0).toFixed(0)}%`;
    if (r.suite === 'tool-call') return `${mode}tool ${(s.tool_rate*100||0).toFixed(0)}% exec ${(s.exec_rate*100||0).toFixed(0)}%`;
    if (r.suite === 'agent-single') return `${mode}${s.correct}/${s.total} ${(s.pass_rate*100||0).toFixed(0)}% steps ${s.avg_steps?.toFixed(1)}`;
    if (r.suite === 'agent-multi') return `${mode}${s.correct}/${s.total} ${(s.pass_rate*100||0).toFixed(0)}% handoffs ${s.handoffs}`;
    if (r.suite === 'performance' && s.metrics_normalized) return `${mode}${s.metrics_normalized} metrics`;
    if (r.suite === 'server-performance' && s.aggregate_predicted_tps) return `${mode}${Math.round(s.aggregate_predicted_tps)} t/s`;
    return `${mode}${JSON.stringify(s).slice(0,60)}`;
  };

  return (
    <main>
      <header>
        <div><h1>GB10 LLM Bench</h1><p>Launcher · Live Monitor · Results · Queue · Compare · Phase 8</p></div>
        <span className="badge">llama.cpp · {system?.nvidia ? system.nvidia.slice(0, 28) : 'GB10 128GB'} · {variants.length} variants</span>
      </header>

      <section className="grid">
        <article className="card">
          <h2>Launcher</h2>
          <label>Suite</label>
          <select value={suite} onChange={e => setSuite(e.target.value)} style={{ width: '100%', padding: 10, background: '#090d13', color: '#fff', border: '1px solid #2b3747', borderRadius: 8 }}>
            <option value="performance">performance (llama-bench)</option>
            <option value="server-performance">server-performance (/completion)</option>
            <option value="knowledge">knowledge (QA)</option>
            <option value="coding">coding (sandbox pytest)</option>
            <option value="tool-call">tool-call (simulator)</option>
            <option value="agent-single">agent-single (ReAct 2-step)</option>
            <option value="agent-multi">agent-multi (2-agent)</option>
          </select>
          <label>Recipe (optional)</label>
          <select value={recipe} onChange={e => setRecipe(e.target.value)} style={{ width: '100%', padding: 10, background: '#090d13', color: '#fff', border: '1px solid #2b3747', borderRadius: 8 }}>
            <option value="">(no recipe) use config below</option>
            {recipes.map(r => <option key={r.name} value={r.name}>{r.name} — {r.suite}</option>)}
          </select>
          <label>Model (managed)</label>
          <div style={{ display:'flex', gap:6 }}>
            <select value={model} onChange={e => setModel(e.target.value)} style={{ flex:1, padding: 10, background: '#090d13', color: '#fff', border: '1px solid #2b3747', borderRadius: 8 }}>
              {variants.slice(0,30).map(v => <option key={v.path} value={v.path}>{v.path.split('/').slice(-2).join('/')} ({v.quant})</option>)}
              <option value={model}>custom: {model.slice(-40)}</option>
            </select>
            <button onClick={scanModels} style={{ padding:'8px 10px', background:'#2b3747', color:'#fff' }}>scan</button>
          </div>
          <input value={model} onChange={e => setModel(e.target.value)} placeholder="/models/model.gguf" style={{ marginTop:6, fontSize:12 }} />
          <label style={{ display:'flex', alignItems:'center', gap:8, marginTop:8 }}><input type="checkbox" checked={managed} onChange={e => setManaged(e.target.checked)} /> managed server</label>
          <label>Thinking mode</label>
          <select value={thinkingMode} onChange={e => setThinkingMode(e.target.value as 'auto' | 'think' | 'no-think')} style={{ width: '100%', padding: 10, background: '#090d13', color: '#fff', border: '1px solid #2b3747', borderRadius: 8 }}>
            <option value="auto">auto (model/template default)</option>
            <option value="think">think (reasoning on)</option>
            <option value="no-think">no-think (reasoning off)</option>
          </select>
          <label>Thinking budget (tokens, -1 = unlimited)</label>
          <input type="number" value={thinkingMode === 'no-think' ? 0 : thinkingBudget} disabled={thinkingMode === 'no-think'} onChange={e => setThinkingBudget(parseInt(e.target.value, 10) || 0)} />
          <label>Max output tokens</label>
          <input type="number" min="1" value={maxTokens} onChange={e => setMaxTokens(Math.max(1, parseInt(e.target.value, 10) || 1))} />
          <label>Request timeout (seconds)</label>
          <input type="number" min="1" value={requestTimeout} onChange={e => setRequestTimeout(Math.max(1, parseInt(e.target.value, 10) || 1))} />
          <p style={{ fontSize: 11, color: '#8f9bad', margin: '6px 0 0' }}>think 모드는 thinking budget와 max output을 따로 조절해 장시간 reasoning 모델을 수용합니다.</p>
          {suite === 'server-performance' && !managed && <>
            <label>llama-server URL</label>
            <input value={serverUrl} onChange={e => setServerUrl(e.target.value)} />
          </>}
          {['knowledge','coding','tool-call','agent-single','agent-multi'].includes(suite) && !managed && <>
            <label>External server URL</label>
            <input value={serverUrl} onChange={e => setServerUrl(e.target.value)} />
          </>}
          {suite === 'server-performance' && <>
            <label>Concurrency</label>
            <input type="number" value={concurrency} onChange={e => setConcurrency(parseInt(e.target.value) || 1)} />
          </>}
          <button onClick={launch} style={{ background: '#4cc38a', color: '#0a0d12', width: '100%', marginTop: 12 }}>Run Benchmark</button>
          <p style={{ fontSize: 11, color: '#8f9bad', marginTop: 8 }}>Queue: {queue.length} running/queued · model_lock serializes GB10 · artifacts in runs/&#123;id&#125;/</p>
        </article>

        <article className="card">
          <h2>Live Monitor {active && <span style={{ fontSize: 12, color: '#8f9bad' }}>· {active.id.slice(0,16)}</span>}</h2>
          {active ? <>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <span className={'status ' + active.status}>{active?.status}</span>
              {['running', 'queued'].includes(active.status) && <button onClick={cancel} style={{ background: '#ff6b6b', color: '#fff', padding: '6px 10px' }}>Cancel</button>}
            </div>
            <TelemetryChart points={telemetry} />
            {slots && <pre style={{ height: 90, marginTop: 8 }}>{JSON.stringify(slots, null, 2).slice(0, 800)}</pre>}
            <pre style={{ height: 140 }}>{events.slice(-12).map(e => `${e.type} ${JSON.stringify(e.data).slice(0, 140)}`).join('\n')}</pre>
          </> : <p style={{ color: '#8f9bad' }}>No active run. Launch or click a row.</p>}
          {queue.length > 0 && <><h3 style={{ marginTop:10, fontSize:13 }}>Queue</h3><ul style={{ fontSize:12, lineHeight:'18px' }}>{queue.map((q:any)=><li key={q.id}>{q.id.slice(0,16)} {q.suite} {q.status}</li>)}</ul></>}
        </article>
      </section>

      <section className="card">
        <h2>Recent Runs {compareIds.length>0 && <button onClick={doCompare} style={{ marginLeft:8, background:'#6ea8ff', color:'#fff', padding:'6px 10px', fontSize:12 }}>Compare {compareIds.length}</button>}</h2>
        <table>
          <thead><tr><th></th><th>Run</th><th>Suite</th><th>Status</th><th>Summary</th><th>Created</th></tr></thead>
          <tbody>
            {runs.map(r => (
              <tr key={r.id} onClick={() => { setActive(r); openDetail(r); setEvents([]); }} style={{ background: detail?.id === r.id ? '#18202c' : undefined }}>
                <td onClick={e=>e.stopPropagation()}><input type="checkbox" checked={compareIds.includes(r.id)} onChange={e=> setCompareIds(v=> e.target.checked? [...v.slice(0,3), r.id] : v.filter(x=>x!==r.id))} /></td>
                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.id.slice(0, 20)}</td>
                <td>{r.suite}</td>
                <td><span className={'status ' + r.status}>{r.status}</span></td>
                <td style={{ fontSize: 11, color: '#b9c8da', maxWidth:260, overflow:'hidden', textOverflow:'ellipsis' }}>{summaryLine(r)}</td>
                <td style={{ fontSize: 12 }}>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {compareRes && <pre style={{ height:'auto', maxHeight:260, marginTop:8 }}>{JSON.stringify(compareRes.table || compareRes, null, 2).slice(0, 3000)}</pre>}
      </section>

      {detail && (
        <section className="card" style={{ marginTop: 18 }}>
          <h2>Run Detail · {detail.id}</h2>
          <p style={{ fontSize: 12, color: '#8f9bad' }}>thinking: {detail.config?.thinking_mode || 'auto'} · budget: {detail.config?.thinking_budget ?? '-'} · timeout: {detail.config?.request_timeout_s ?? '-'}s · max output: {detail.config?.max_tokens ?? detail.config?.gen_tokens ?? '-'}</p>
          <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
            {['metrics', 'samples', 'environment', 'events', 'artifacts'].map(t => (
              <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#2b3747' : '#18202c', color: '#fff', padding: '7px 12px' }}>{t}</button>
            ))}
            <span className={'status ' + detail.status} style={{ marginLeft: 'auto' }}>{detail.status}</span>
          </div>
          <div style={{ display:'flex', gap:6, marginBottom:12, flexWrap:'wrap' }}>
            <a href={`${API}/runs/${detail.id}/export?format=json`} target="_blank" rel="noreferrer" style={{ background:'#1a2332', color:'#6ea8ff', padding:'6px 10px', borderRadius:6, fontSize:12, textDecoration:'none' }}>Export JSON</a>
            <a href={`${API}/runs/${detail.id}/export?format=csv`} target="_blank" rel="noreferrer" style={{ background:'#1a2332', color:'#6ea8ff', padding:'6px 10px', borderRadius:6, fontSize:12, textDecoration:'none' }}>CSV</a>
            <a href={`${API}/runs/${detail.id}/export?format=markdown`} target="_blank" rel="noreferrer" style={{ background:'#1a2332', color:'#6ea8ff', padding:'6px 10px', borderRadius:6, fontSize:12, textDecoration:'none' }}>Markdown</a>
            <a href={`${API}/runs/${detail.id}/export?format=zip`} target="_blank" rel="noreferrer" style={{ background:'#4cc38a', color:'#0a0d12', padding:'6px 10px', borderRadius:6, fontSize:12, textDecoration:'none' }}>ZIP bundle</a>
            <a href={`${API}/runs/${detail.id}/methodology`} target="_blank" rel="noreferrer" style={{ background:'#2b3747', color:'#fff', padding:'6px 10px', borderRadius:6, fontSize:12, textDecoration:'none' }}>Methodology</a>
          </div>

          {tab === 'metrics' && (
            <>
              <h3>Normalized Metrics / Summary</h3>
              {metrics?.db?.length ? (
                <>
                  <table>
                    <thead><tr><th>Name</th><th>Value</th><th>Unit</th><th>Extra</th></tr></thead>
                    <tbody>
                      {metrics.db.map((m: any, i: number) => (
                        <tr key={i}><td style={{ fontFamily: 'monospace', fontSize: 12 }}>{m.name}</td><td>{typeof m.value === 'number' ? Math.round(m.value * 100) / 100 : String(m.value)}</td><td>{m.unit}</td><td style={{ fontSize: 11, color: '#8f9bad', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>{JSON.stringify(m.extra).slice(0, 120)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  {perfChartData.length > 0 && <><h3 style={{ marginTop: 14 }}>Throughput (tokens/s)</h3><BarChart data={perfChartData} unit="t/s" /></>}
                  {serverLatency.length > 0 && <><h3>Latency (ms)</h3><BarChart data={serverLatency} unit="ms" /></>}
                  {detail.summary?.aggregate_predicted_tps && <p style={{ marginTop: 10, fontSize: 13, color: '#b9c8da' }}>Aggregate decode: <b>{Math.round(detail.summary.aggregate_predicted_tps)}</b> t/s · mean latency {(detail.summary.latency_mean_s * 1000).toFixed(1)} ms · failed {detail.summary.failed || 0}/{detail.summary.requests}</p>}
                </>
              ) : <pre style={{ height: 'auto', maxHeight: 320 }}>{JSON.stringify(detail.summary, null, 2).slice(0, 4000)}</pre>}
            </>
          )}

          {tab === 'samples' && (
            <pre style={{ height: 'auto', maxHeight: 600 }}>{JSON.stringify(detail.summary?.samples || detail.summary?.rows || detail.summary, null, 2).slice(0, 8000)}</pre>
          )}

          {tab === 'environment' && (
            env ? <pre style={{ height: 'auto', maxHeight: 500 }}>{JSON.stringify(env, null, 2)}</pre> : <p style={{ color: '#8f9bad' }}>No environment.json (old run)</p>
          )}

          {tab === 'events' && (
            <pre style={{ height: 'auto', maxHeight: 400 }}>{events.length ? events.map(e => `${new Date(e.ts).toLocaleTimeString()} [${e.type}] ${JSON.stringify(e.data).slice(0, 220)}`).join('\n') : 'Live events appear during run; history via /api/runs/<id>/events/history'}</pre>
          )}

          {tab === 'artifacts' && (
            <>
              <p style={{ fontSize: 12, color: '#8f9bad' }}>{artifacts.length} files in runs/{detail.id}/</p>
              <ul style={{ fontSize: 13, lineHeight: '22px' }}>
                {artifacts.map((f: any) => <li key={f.path}><a href={`${API}/runs/${detail.id}/artifacts/${f.path}`} target="_blank" rel="noreferrer" style={{ color: '#6ea8ff' }}>{f.path}</a> <span style={{ color: '#8f9bad' }}>({f.size} B)</span></li>)}
              </ul>
              {!artifacts.length && <p style={{ color: '#8f9bad' }}>No artifacts</p>}
            </>
          )}
        </section>
      )}

      <p style={{ textAlign: 'center', color: '#5a6b80', fontSize: 11, marginTop: 18 }}>Phase 8 · performance · server-performance · knowledge · coding · tool-call · agent-single · agent-multi · queue · compare · artifacts · managed server</p>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
