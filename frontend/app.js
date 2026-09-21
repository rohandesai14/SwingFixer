const demoReport = {
  frame_count: 647,
  fps: 59.972,
  phase_summary: { address: 0, top_of_backswing: 402, downswing: 605, impact: 606, finish: 646 },
  coaching_summary: [
    'Right elbow is compact at the top of the backswing; consider keeping it closer to an approximate 90-degree bend.',
    'Head offset is elevated; monitor lateral head drift during the swing.',
    'Weight shift is progressing through the motion; keep pressure moving toward the lead side at impact.'
  ],
  coaching_feedback: [
    'At address, your weight shift is too far forward compared with the reference baseline.',
    'At top_of_backswing, your weight shift is too far forward compared with the reference baseline.',
    'At impact, your weight shift is too far forward compared with the reference baseline.'
  ],
  reference_baseline: {
    address: { right_elbow: 160.8, weight_shift_proxy: .05 },
    top_of_backswing: { right_elbow: 26.5, weight_shift_proxy: .28 },
    impact: { right_elbow: 139.9, weight_shift_proxy: .82 }
  },
  reference_comparison: {
    address: { right_elbow: -8.9, weight_shift_proxy: 1.96, head_offset_proxy: .16 },
    top_of_backswing: { right_elbow: -.3, weight_shift_proxy: 2.8, head_offset_proxy: .23 },
    impact: { right_elbow: 6.5, weight_shift_proxy: 1.41, head_offset_proxy: .18 }
  }
};

let report = demoReport;
let selectedVideo;
const $ = (id) => document.getElementById(id);
const phaseNames = ['address', 'top_of_backswing', 'downswing', 'impact', 'finish'];
const phaseLabels = { address: 'Address', top_of_backswing: 'Top', downswing: 'Downswing', impact: 'Impact', finish: 'Finish' };
const metricDefinitions = {
  right_elbow: { label: 'Right elbow', unit: 'degrees', suffix: '°', explanation: 'Trail-arm angle in degrees. Lower values mean more bend; higher values mean a straighter elbow.' },
  weight_shift_proxy: { label: 'Weight shift', unit: 'normalized proxy', suffix: '', explanation: 'An ankle-to-hip displacement proxy. Higher values indicate more forward movement in this camera view, not a percentage of body weight.' },
  head_offset_proxy: { label: 'Head offset', unit: 'normalized proxy', suffix: '', explanation: 'Head displacement relative to the shoulder center. Higher values indicate more lateral movement.' },
  hip_rotation_proxy: { label: 'Hip rotation', unit: 'degrees', suffix: '°', explanation: 'A 2D hip-line rotation proxy. Compare its trend within the same camera setup.' }
};

function formatPhase(phase) { return phase.replaceAll('_', ' '); }
function updateSummary() {
  $('frame-count').textContent = report.frame_count || 0;
  const top = report.phase_summary?.top_of_backswing || 0;
  $('top-frame').textContent = `${(top / (report.fps || 60)).toFixed(2)}s`;
  $('top-frame').nextElementSibling.textContent = `Frame ${top}`;
  $('reference-count').textContent = report.reference_baseline ? `${report.reference_baseline.reference_count || 30} swings` : '30 swings';
  renderFeedback(); renderTimeline(); renderComparison(); drawChart();
}
function renderFeedback() {
  const messages = report.coaching_feedback || report.coaching_summary || [];
  $('feedback-list').innerHTML = messages.slice(0, 3).map((message, index) => `<div class="feedback"><span class="feedback-index">0${index + 1}</span><span>${message}</span></div>`).join('');
  $('show-all').onclick = () => { $('feedback-list').innerHTML = messages.map((message, index) => `<div class="feedback"><span class="feedback-index">${String(index + 1).padStart(2, '0')}</span><span>${message}</span></div>`).join(''); };
}
function renderTimeline() {
  const summary = report.phase_summary || {};
  $('phase-timeline').innerHTML = phaseNames.map((name, index) => `<div class="phase ${name === 'top_of_backswing' ? 'active' : ''}"><span>${phaseLabels[name]}</span><b>${summary[name] ?? '--'}</b></div>`).join('');
}
function metricValue(frame, metric) {
  if (metric === 'right_elbow') return frame?.angles?.right_elbow ?? frame?.right_elbow;
  return frame?.metrics?.[metric] ?? frame?.[metric];
}
function baselineValue(phase, metric) {
  const values = report.reference_baseline?.[phase] || {};
  return values[metric] ?? (metric === 'weight_shift_proxy' ? values.weight_shift : undefined);
}
function comparisonDelta(phase, metric) {
  const values = report.reference_comparison?.[phase] || {};
  return values[metric] ?? (metric === 'weight_shift_proxy' ? values.weight_shift : undefined);
}
function phaseFrame(phase) {
  const index = report.phase_summary?.[phase];
  if (index === undefined || !report.frames?.length) return undefined;
  return report.frames.find(frame => frame.frame === index) || report.frames[index];
}
function formatMetric(value, metric) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '--';
  return `${Number(value).toFixed(metric === 'right_elbow' ? 1 : 2)}${metricDefinitions[metric].suffix}`;
}
function renderComparison() {
  const metrics = ['right_elbow', 'weight_shift_proxy'];
  const rows = metrics.flatMap(metric => ['address', 'top_of_backswing', 'impact'].map(phase => {
    const reference = baselineValue(phase, metric);
    const delta = comparisonDelta(phase, metric);
    const actual = metricValue(phaseFrame(phase), metric);
    const user = actual ?? (reference !== undefined && delta !== undefined ? reference + delta : undefined);
    return `<div class="comparison-row"><strong>${phaseLabels[phase]}</strong><span>${metricDefinitions[metric].label}</span><span>${formatMetric(user, metric)}</span><span>${formatMetric(reference, metric)}</span><span class="delta ${delta !== undefined && Math.abs(delta) < (metric === 'right_elbow' ? 5 : .25) ? 'good' : ''}">${formatMetric(delta, metric)}</span></div>`;
  }));
  $('comparison-table').innerHTML = `<div class="comparison-row"><span>Phase</span><span>Metric</span><span>Your value</span><span>Reference</span><span>Delta</span></div>${rows.join('')}`;
}
function drawChart() {
  const metric = $('metric-select').value;
  const definition = metricDefinitions[metric];
  $('chart-explanation').textContent = `${definition.explanation} Each blue point is a sampled analyzed frame; orange markers show reference values at detected phases.`;
  const width = 760, height = 210;
  const frames = report.frames || [];
  const source = frames.map((frame, index) => ({ frame: Number(frame.frame ?? index), value: metricValue(frame, metric) })).filter(point => point.value !== undefined);
  const sampled = source.length > 120 ? source.filter((_, index) => index % Math.ceil(source.length / 120) === 0) : source;
  const references = ['address', 'top_of_backswing', 'impact'].map(phase => ({ frame: report.phase_summary?.[phase], value: baselineValue(phase, metric) })).filter(point => point.frame !== undefined && point.value !== undefined);
  const fallback = Array.from({ length: 8 }, (_, index) => ({ frame: index * ((report.frame_count || 647) / 7), value: index === 2 ? 90 : 140 - index * 5 }));
  const points = sampled.length ? sampled : fallback;
  const allValues = points.concat(references).map(point => Number(point.value));
  const max = Math.max(...allValues) + 1, min = Math.min(...allValues) - 1;
  const x = frame => (Number(frame) / (report.frame_count || 647)) * width;
  const y = value => height - ((Number(value) - min) / Math.max(max - min, 1)) * height;
  const path = points.map((point, index) => `${index ? 'L' : 'M'} ${x(point.frame)} ${y(point.value)}`).join(' ');
  const referencePath = references.map((point, index) => `${index ? 'L' : 'M'} ${x(point.frame)} ${y(point.value)}`).join(' ');
  const markers = references.map(point => `<circle cx="${x(point.frame)}" cy="${y(point.value)}" r="4" fill="#f18b58"/>`).join('');
  $('metric-chart').innerHTML = `<path d="${referencePath}" fill="none" stroke="#f18b58" stroke-width="2" stroke-dasharray="6 7" opacity=".75"/><path d="${path}" fill="none" stroke="#5d7cff" stroke-width="3"/>${markers}<text x="12" y="18" fill="#73807a" font-size="10" font-family="DM Mono">${definition.unit.toUpperCase()}</text>`;
}
function setFrame(value) { const frame = Number(value); $('current-frame').textContent = `${frame} / ${report.frame_count || 647}`; $('stage-time').textContent = (frame / (report.fps || 60)).toFixed(2); $('scrubber-fill').style.width = `${frame / (report.frame_count || 647) * 100}%`; }
$('frame-slider').addEventListener('input', event => setFrame(event.target.value));
$('play-button').addEventListener('click', event => { event.currentTarget.textContent = event.currentTarget.textContent === '▶' ? 'Ⅱ' : '▶'; });
$('metric-select').addEventListener('change', drawChart);
$('report-input').addEventListener('change', event => { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { try { report = JSON.parse(reader.result); $('report-status').textContent = file.name; updateSummary(); } catch { $('report-status').textContent = 'Could not read JSON'; } }; reader.readAsText(file); });
$('video-input').addEventListener('change', event => { const file = event.target.files[0]; if (!file) return; const video = $('swing-video'); video.src = URL.createObjectURL(file); document.querySelector('.video-stage').classList.add('has-video'); $('report-status').textContent = `${file.name} loaded`; });
$('video-input').addEventListener('change', event => { selectedVideo = event.target.files[0]; $('analyze-button').disabled = !selectedVideo; });
$('analyze-button').addEventListener('click', async () => { if (!selectedVideo) return; const button = $('analyze-button'); button.disabled = true; button.textContent = 'Analyzing...'; $('report-status').textContent = 'Analysis queued'; try { const form = new FormData(); form.append('file', selectedVideo); const created = await fetch('http://127.0.0.1:8000/api/analysis', { method: 'POST', body: form }); if (!created.ok) throw new Error('Could not create analysis'); const job = await created.json(); let status; do { await new Promise(resolve => setTimeout(resolve, 1000)); const response = await fetch(`http://127.0.0.1:8000/api/analysis/${job.id}/status`); status = await response.json(); $('report-status').textContent = status.status === 'processing' ? 'Analyzing swing...' : status.status; } while (status.status !== 'complete' && status.status !== 'failed'); if (status.status === 'failed') throw new Error(status.error || 'Analysis failed'); report = await fetch(`http://127.0.0.1:8000${status.report_url}`).then(response => response.json()); const video = $('swing-video'); video.src = `http://127.0.0.1:8000${status.video_url}`; document.querySelector('.video-stage').classList.add('has-video'); updateSummary(); $('report-status').textContent = 'Live analysis complete'; } catch (error) { $('report-status').textContent = error.message; } finally { button.disabled = false; button.textContent = 'Analyze video'; } });
updateSummary(); setFrame(402);
