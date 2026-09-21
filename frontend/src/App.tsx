import { useEffect, useMemo, useRef, useState } from 'react';
import '../styles.css';

type Frame = {
  frame?: number;
  timestamp_seconds?: number;
  angles?: Record<string, number>;
  metrics?: Record<string, number>;
};

type Report = {
  frame_count: number;
  fps?: number;
  frames?: Frame[];
  phase_summary?: Record<string, number>;
  coaching_summary?: string[];
  coaching_feedback?: string[];
  reference_baseline?: Record<string, Record<string, number>>;
  reference_comparison?: Record<string, Record<string, number>>;
};

type MetricKey = 'right_elbow' | 'weight_shift_proxy' | 'head_offset_proxy' | 'hip_rotation_proxy';

const demoReport: Report = {
  frame_count: 647,
  fps: 59.972,
  phase_summary: { address: 0, top_of_backswing: 402, downswing: 605, impact: 606, finish: 646 },
  coaching_summary: [
    'Right elbow is compact at the top of the backswing; consider keeping it closer to an approximate 90-degree bend.',
    'Head offset is elevated; monitor lateral head drift during the swing.',
    'Weight shift is progressing through the motion; keep pressure moving toward the lead side at impact.',
  ],
  coaching_feedback: [
    'At address, your weight shift is too far forward compared with the reference baseline.',
    'At top_of_backswing, your weight shift is too far forward compared with the reference baseline.',
    'At impact, your weight shift is too far forward compared with the reference baseline.',
  ],
  reference_baseline: {
    address: { right_elbow: 160.8, weight_shift_proxy: 0.05 },
    top_of_backswing: { right_elbow: 26.5, weight_shift_proxy: 0.28 },
    impact: { right_elbow: 139.9, weight_shift_proxy: 0.82 },
  },
  reference_comparison: {
    address: { right_elbow: -8.9, weight_shift_proxy: 1.96 },
    top_of_backswing: { right_elbow: -0.3, weight_shift_proxy: 2.8 },
    impact: { right_elbow: 6.5, weight_shift_proxy: 1.41 },
  },
};

const phaseNames = ['address', 'top_of_backswing', 'downswing', 'impact', 'finish'];
const phaseLabels: Record<string, string> = { address: 'Address', top_of_backswing: 'Top', downswing: 'Downswing', impact: 'Impact', finish: 'Finish' };
const metricDefinitions: Record<MetricKey, { label: string; unit: string; suffix: string; explanation: string }> = {
  right_elbow: { label: 'Right elbow', unit: 'degrees', suffix: '°', explanation: 'Trail-arm angle in degrees. Lower values mean more bend; higher values mean a straighter elbow.' },
  weight_shift_proxy: { label: 'Weight shift', unit: 'normalized proxy', suffix: '', explanation: 'An ankle-to-hip displacement proxy. Higher values indicate more forward movement in this camera view, not a percentage of body weight.' },
  head_offset_proxy: { label: 'Head offset', unit: 'normalized proxy', suffix: '', explanation: 'Head displacement relative to the shoulder center. Higher values indicate more lateral movement.' },
  hip_rotation_proxy: { label: 'Hip rotation', unit: 'degrees', suffix: '°', explanation: 'A 2D hip-line rotation proxy. Compare its trend within the same camera setup.' },
};

const formatMetric = (value: number | undefined, metric: MetricKey) => value === undefined || Number.isNaN(value) ? '--' : `${value.toFixed(metric === 'right_elbow' ? 1 : 2)}${metricDefinitions[metric].suffix}`;
const metricValue = (frame: Frame | undefined, metric: MetricKey) => metric === 'right_elbow' ? frame?.angles?.right_elbow : frame?.metrics?.[metric];

export default function App() {
  const [report, setReport] = useState<Report>(demoReport);
  const [selectedVideo, setSelectedVideo] = useState<File>();
  const [videoUrl, setVideoUrl] = useState<string>();
  const [status, setStatus] = useState('Demo report loaded');
  const [currentFrame, setCurrentFrame] = useState(402);
  const [metric, setMetric] = useState<MetricKey>('right_elbow');
  const [showAllFeedback, setShowAllFeedback] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const phases = report.phase_summary ?? {};
  const fps = report.fps ?? 60;
  const feedback = report.coaching_feedback ?? report.coaching_summary ?? [];
  const frames = report.frames ?? [];
  const definition = metricDefinitions[metric];

  const phaseFrame = (phase: string) => frames.find((frame) => frame.frame === phases[phase]) ?? frames[phases[phase] ?? -1];
  const baselineValue = (phase: string, key: MetricKey) => report.reference_baseline?.[phase]?.[key] ?? (key === 'weight_shift_proxy' ? report.reference_baseline?.[phase]?.weight_shift : undefined);
  const comparisonValue = (phase: string, key: MetricKey) => report.reference_comparison?.[phase]?.[key] ?? (key === 'weight_shift_proxy' ? report.reference_comparison?.[phase]?.weight_shift : undefined);

  const chart = useMemo(() => {
    const source = frames.map((frame, index) => ({ frame: frame.frame ?? index, value: metricValue(frame, metric) })).filter((point): point is { frame: number; value: number } => point.value !== undefined);
    const points = source.length ? source.filter((_, index) => index % Math.max(1, Math.ceil(source.length / 120)) === 0) : Array.from({ length: 8 }, (_, index) => ({ frame: index * (report.frame_count / 7), value: index === 2 ? 90 : 140 - index * 5 }));
    const references = ['address', 'top_of_backswing', 'impact'].map((phase) => ({ frame: phases[phase], value: baselineValue(phase, metric) })).filter((point): point is { frame: number; value: number } => point.frame !== undefined && point.value !== undefined);
    const values = [...points, ...references].map((point) => point.value);
    const min = Math.min(...values) - 1;
    const max = Math.max(...values) + 1;
    const x = (frame: number) => (frame / report.frame_count) * 760;
    const y = (value: number) => 210 - ((value - min) / Math.max(max - min, 1)) * 210;
    const path = points.map((point, index) => `${index ? 'L' : 'M'} ${x(point.frame)} ${y(point.value)}`).join(' ');
    const referencePath = references.map((point, index) => `${index ? 'L' : 'M'} ${x(point.frame)} ${y(point.value)}`).join(' ');
    return { path, referencePath, references, x, y };
  }, [frames, metric, phases, report.frame_count, report.reference_baseline]);

  useEffect(() => {
    setCurrentFrame(Math.min(currentFrame, Math.max(0, report.frame_count - 1)));
  }, [report.frame_count]);

  function loadReport(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try { setReport(JSON.parse(String(reader.result)) as Report); setStatus(file.name); } catch { setStatus('Could not read JSON'); }
    };
    reader.readAsText(file);
  }

  function chooseVideo(file: File) {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    const nextUrl = URL.createObjectURL(file);
    setVideoUrl(nextUrl); setSelectedVideo(file); setStatus(`${file.name} loaded`);
  }

  async function analyzeVideo() {
    if (!selectedVideo) return;
    setStatus('Analysis queued');
    try {
      const form = new FormData(); form.append('file', selectedVideo);
      const created = await fetch('http://127.0.0.1:8000/api/analysis', { method: 'POST', body: form });
      if (!created.ok) throw new Error('Could not create analysis');
      const job = await created.json() as { id: string };
      let result: { status: string; report_url?: string; video_url?: string; error?: string };
      do {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        result = await fetch(`http://127.0.0.1:8000/api/analysis/${job.id}/status`).then((response) => response.json());
        setStatus(result.status === 'processing' ? 'Analyzing swing...' : result.status);
      } while (result.status !== 'complete' && result.status !== 'failed');
      if (result.status === 'failed' || !result.report_url || !result.video_url) throw new Error(result.error ?? 'Analysis failed');
      setReport(await fetch(`http://127.0.0.1:8000${result.report_url}`).then((response) => response.json()));
      setVideoUrl(`http://127.0.0.1:8000${result.video_url}`); setStatus('Live analysis complete');
    } catch (error) { setStatus(error instanceof Error ? error.message : 'Analysis failed'); }
  }

  function updateFrame(value: number) {
    setCurrentFrame(value);
    if (videoRef.current) videoRef.current.currentTime = value / fps;
  }

  return <main className="shell">
    <header className="topbar"><a className="brand" href="."><span className="brand-mark">SF</span><span><strong>SwingFixer</strong><small>Motion lab</small></span></a><div className="topbar-meta"><span className="status-dot" />{status}</div></header>
    <section className="intro"><div><p className="eyebrow">Swing analysis / 01</p><h1>Turn one swing<br /><em>into a better next one.</em></h1><p className="lede">A phase-by-phase view of your motion, grounded in the reference swings you selected.</p></div><div className="upload-area"><div className="upload-actions"><label className="upload-control"><input type="file" accept=".json,application/json" onChange={(event) => event.target.files?.[0] && loadReport(event.target.files[0])} /><span>Load report JSON <b>+</b></span></label><label className="upload-control secondary-upload"><input type="file" accept="video/*,.mp4,.mov" onChange={(event) => event.target.files?.[0] && chooseVideo(event.target.files[0])} /><span>Choose video <b>+</b></span></label><button className="analyze-button" disabled={!selectedVideo} onClick={analyzeVideo}>Analyze video</button></div><small className="upload-help">Load report JSON restores a completed analysis: phases, frame metrics, comparison values, and coaching notes.</small></div></section>
    <section className="summary-grid"><article className="metric-card accent-card"><span className="card-label">Swing status</span><strong>Needs one adjustment</strong><span className="card-note">Weight shift is the clearest gap</span></article><article className="metric-card"><span className="card-label">Frames analyzed</span><strong>{report.frame_count}</strong><span className="card-note">{frames.length ? 'Pose data loaded' : 'Demo report'}</span></article><article className="metric-card"><span className="card-label">Top of backswing</span><strong>{((phases.top_of_backswing ?? 0) / fps).toFixed(2)}s</strong><span className="card-note">Frame {phases.top_of_backswing ?? '--'}</span></article><article className="metric-card"><span className="card-label">Reference set</span><strong>{report.reference_baseline ? '30 swings' : 'Demo set'}</strong><span className="card-note">Local baseline</span></article></section>
    <section className="workspace-grid"><article className="panel video-panel"><div className="panel-heading"><div><span className="section-kicker">Playback</span><h2>Your swing</h2></div><span className="live-chip">ANNOTATED</span></div><div className={`video-stage ${videoUrl ? 'has-video' : ''}`}><video ref={videoRef} src={videoUrl} controls playsInline /><div className="silhouette"><span className="head" /><span className="body" /><span className="club" /></div><div className="stage-copy"><span className="stage-time">{(currentFrame / fps).toFixed(2)}</span><span>Frame {currentFrame}</span></div><div className="stage-grid" /></div><div className="player-controls"><button className="play-button" onClick={() => videoRef.current?.paused ? videoRef.current.play() : videoRef.current?.pause()} aria-label="Play or pause">&#9654;</button><div className="scrubber"><div style={{ width: `${(currentFrame / Math.max(report.frame_count - 1, 1)) * 100}%` }} /><input type="range" min="0" max={Math.max(report.frame_count - 1, 0)} value={currentFrame} onChange={(event) => updateFrame(Number(event.target.value))} /></div><span className="current-frame">{currentFrame} / {report.frame_count}</span></div><div className="phase-timeline">{phaseNames.map((phase) => <button className={`phase ${phase === 'top_of_backswing' ? 'active' : ''}`} key={phase} onClick={() => phases[phase] !== undefined && updateFrame(phases[phase])}><span>{phaseLabels[phase]}</span><b>{phases[phase] ?? '--'}</b></button>)}</div></article><aside className="panel coaching-panel"><div className="panel-heading"><div><span className="section-kicker">Coach notes</span><h2>Start here</h2></div><span className="priority">01</span></div><div className="feedback-list">{feedback.slice(0, showAllFeedback ? feedback.length : 3).map((message, index) => <div className="feedback" key={`${message}-${index}`}><span className="feedback-index">{String(index + 1).padStart(2, '0')}</span><span>{message}</span></div>)}</div><button className="ghost-button" onClick={() => setShowAllFeedback((value) => !value)}>{showAllFeedback ? 'Show priority feedback' : 'View all feedback'} <span>→</span></button></aside></section>
    <section className="lower-grid"><article className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">Motion profile</span><h2>Metric trail</h2></div><select value={metric} onChange={(event) => setMetric(event.target.value as MetricKey)}>{Object.entries(metricDefinitions).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></div><p className="panel-help">{definition.explanation} Each blue point is a sampled analyzed frame; orange markers show reference values at detected phases.</p><div className="chart-wrap"><svg viewBox="0 0 760 210" role="img" aria-label="Metric chart"><path d={chart.referencePath} fill="none" stroke="#f18b58" strokeWidth="2" strokeDasharray="6 7" opacity=".75" /><path d={chart.path} fill="none" stroke="#5d7cff" strokeWidth="3" />{chart.references.map((point) => <circle key={point.frame} cx={chart.x(point.frame)} cy={chart.y(point.value)} r="4" fill="#f18b58" />)}<text x="12" y="18" fill="#73807a" fontSize="10" fontFamily="DM Mono">{definition.unit.toUpperCase()}</text></svg></div><div className="chart-legend"><span><i className="legend-user" />Your swing, frame by frame</span><span><i className="legend-reference" />Reference phase values</span></div></article><article className="panel compare-panel"><div className="panel-heading"><div><span className="section-kicker">Reference comparison</span><h2>Where you diverge</h2></div><span className="units">your - reference</span></div><p className="panel-help">A positive delta means your value is higher than the reference at that phase; a negative delta means it is lower.</p><div className="comparison-table"><div className="comparison-row"><span>Phase</span><span>Metric</span><span>Your value</span><span>Reference</span><span>Delta</span></div>{['right_elbow', 'weight_shift_proxy'].flatMap((key) => ['address', 'top_of_backswing', 'impact'].map((phase) => { const typedKey = key as MetricKey; const reference = baselineValue(phase, typedKey); const delta = comparisonValue(phase, typedKey); const actual = metricValue(phaseFrame(phase), typedKey); const user = actual ?? (reference !== undefined && delta !== undefined ? reference + delta : undefined); return <div className="comparison-row" key={`${phase}-${key}`}><strong>{phaseLabels[phase]}</strong><span>{metricDefinitions[typedKey].label}</span><span>{formatMetric(user, typedKey)}</span><span>{formatMetric(reference, typedKey)}</span><span className={`delta ${delta !== undefined && Math.abs(delta) < (typedKey === 'right_elbow' ? 5 : .25) ? 'good' : ''}`}>{formatMetric(delta, typedKey)}</span></div>; }))}</div><p className="comparison-key"><b>Right elbow</b> is an angle in degrees. <b>Weight shift</b> is a normalized camera proxy, not a percentage of body weight.</p></article></section>
    <footer><span>SwingFixer analysis workspace</span><span>Local processing / no upload required</span></footer>
  </main>;
}
