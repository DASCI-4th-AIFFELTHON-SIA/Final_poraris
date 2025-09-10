// keywords_bubble.js — D3.js bubble (packed circles) renderer as an ES module
// Usage (ESM):
//   <script type="module">
//     import { renderKeywordBubbles } from './keywords_bubble.js';
//     const data = { keywords: [ { phrase:'예시', score: 12.3 }, ... ] };
//     renderKeywordBubbles(document.getElementById('viz'), data, { width: 1000, height: 1000 });
//   </script>

import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';

// ---- Defaults ----
const DEFAULTS = {
  scale: 2.6,          // radius scale
  margin: 0.06,        // min gap between circles
  ticks: 600,          // force ticks
  labelScale: 13,      // px per radius unit
  minFont: 9,          // min font size
  fillerMax: 450,      // filler bubbles count
  fillerR: 0.8,        // filler radius
  candidates: 8000,    // filler candidate samples
  innerKeepPct: 70,    // inner keep ring (% of main radius)
  outerPct: 110,       // outer ring (% of main radius)
  color: d3.interpolateBlues,
  background: '#ffffff',
  fillerColor: '#eeeeee',
  stroke: '#ffffff',
};

// ---- Helpers ----
function normalizeItems(raw, scale) {
  const arr = raw?.keywords ?? [];
  const items = arr
    .map(d => ({ phrase: d.phrase, score: +d.score }))
    .filter(d => d.phrase && Number.isFinite(d.score) && d.score > 0);
  if (!items.length) throw new Error('키워드 데이터가 비어 있거나 score>0 항목이 없습니다.');
  const smax = d3.max(items, d => d.score);
  items.forEach(d => { d.r = scale * Math.sqrt(d.score / smax); });
  items.sort((a, b) => d3.descending(a.r, b.r));
  return items;
}

function layoutBubbles(items, { margin, ticks }) {
  const nodes = items.map(d => ({ id: d.phrase, r: d.r, score: d.score, x: (Math.random() - 0.5) * 4, y: (Math.random() - 0.5) * 4 }));
  const sim = d3.forceSimulation(nodes)
    .force('center', d3.forceCenter(0, 0))
    .force('collide', d3.forceCollide().radius(d => d.r + margin).iterations(2))
    .alpha(1).alphaDecay(1 - Math.pow(0.001, 1 / ticks))
    .stop();
  for (let i = 0; i < ticks; i++) sim.tick();
  return nodes;
}

function boundingRadius(nodes) {
  return nodes.length ? d3.max(nodes, n => Math.hypot(n.x, n.y) + n.r) : 0;
}

function placeFillers(main, { margin, fillerMax, fillerR, candidates, innerKeepPct, outerPct }) {
  const fillers = [];
  const R = boundingRadius(main);
  const inner = (innerKeepPct / 100) * R;
  const outer = (outerPct / 100) * R;

  function overlaps(x, y, r, arr) {
    for (const c of arr) {
      const dx = x - c.x, dy = y - c.y;
      const minD = r + c.r + margin;
      if (dx * dx + dy * dy < minD * minD) return true;
    }
    return false;
  }

  const all = main.map(d => ({ x: d.x, y: d.y, r: d.r, fill: false }));
  for (let i = 0; i < candidates; i++) {
    const ang = Math.random() * Math.PI * 2;
    const rr = Math.sqrt(Math.random()) * (outer - inner) + inner;
    const cx = rr * Math.cos(ang), cy = rr * Math.sin(ang);
    if (!overlaps(cx, cy, fillerR, all)) {
      all.push({ x: cx, y: cy, r: fillerR, fill: true });
      fillers.push({ x: cx, y: cy, r: fillerR });
      if (fillers.length >= fillerMax) break;
    }
  }
  return fillers;
}

function colorScale(nodes, interpolator) {
  const svals = nodes.map(d => d.score);
  const sMin = d3.min(svals), sMax = d3.max(svals);
  const t = d3.scaleLinear().domain([sMin, sMax]).clamp(true);
  const cmap = v => interpolator(t(v));
  return cmap;
}

// ---- Main render function ----
export function renderKeywordBubbles(container, rawData, opts = {}) {
  const cfg = { ...DEFAULTS, ...opts };
  const items = normalizeItems(rawData, cfg.scale);
  const nodes = layoutBubbles(items, { margin: cfg.margin, ticks: cfg.ticks });
  const fillers = placeFillers(nodes, cfg);
  const cmap = colorScale(nodes, cfg.color);

  const width = cfg.width ?? 1200;
  const height = cfg.height ?? 1200;

  // Root SVG
  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', '-600 -600 1200 1200')
    .attr('width', width)
    .attr('height', height)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .attr('aria-label', '키워드 버블 차트')
    .style('background', cfg.background);

  // Defs (shadow)
  const defs = svg.append('defs');
  const shadow = defs.append('filter').attr('id', 'kb-shadow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
  shadow.append('feDropShadow').attr('dx', 0).attr('dy', 0).attr('stdDeviation', 1).attr('flood-color', '#000').attr('flood-opacity', 0.04);

  // Groups
  const gFill = svg.append('g').attr('data-layer', 'fillers');
  const gMain = svg.append('g').attr('data-layer', 'main');
  const gLabel = svg.append('g').attr('data-layer', 'labels');

  // Zoom/pan
  svg.call(d3.zoom().scaleExtent([0.4, 4]).on('zoom', ev => {
    const { transform } = ev; gFill.attr('transform', transform); gMain.attr('transform', transform); gLabel.attr('transform', transform);
  }));

  // Fillers
  gFill.selectAll('circle').data(fillers).join('circle')
    .attr('cx', d => d.x).attr('cy', d => d.y).attr('r', d => d.r)
    .attr('fill', cfg.fillerColor)
    .attr('stroke', cfg.stroke).attr('stroke-width', 1)
    .attr('filter', 'url(#kb-shadow)');

  // Main bubbles
  gMain.selectAll('circle').data(nodes, d => d.id).join('circle')
    .attr('cx', d => d.x).attr('cy', d => d.y).attr('r', d => d.r)
    .attr('fill', d => cmap(d.score))
    .attr('stroke', cfg.stroke).attr('stroke-width', 1.5)
    .attr('filter', 'url(#kb-shadow)')
    .append('title').text(d => `${d.id}: ${d.score}`);

  // Labels (quantile threshold if you want to filter small)
  const radiiSorted = nodes.map(d => d.r).sort(d3.ascending);
  const labelThreshold = d3.quantile(radiiSorted, cfg.labelQuantile ?? 0.00); // adjust in opts
  const labelSel = nodes.filter(d => d.r >= labelThreshold);

  gLabel.selectAll('text').data(labelSel, d => d.id).join('text')
    .attr('x', d => d.x).attr('y', d => d.y)
    .text(d => d.id)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('paint-order', 'stroke')
    .attr('stroke', cfg.stroke).attr('stroke-width', 3)
    .attr('fill', '#111')
    .style('font-weight', 800)
    .style('font-family', `Noto Sans KR, Nanum Gothic, Apple SD Gothic Neo, system-ui, -apple-system, Segoe UI, Roboto, sans-serif`)
    .style('font-size', d => `${Math.max(cfg.minFont, Math.round(d.r * cfg.labelScale))}px`);

  return { svg, nodes, fillers };
}

// Convenience loader: fetch JSON from URL then render.
export async function renderFromUrl(container, url, opts = {}) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch JSON: ${url}`);
  const json = await res.json();
  return renderKeywordBubbles(container, json, opts);
}
