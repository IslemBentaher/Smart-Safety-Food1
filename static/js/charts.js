"use strict";
/* Tiny SVG chart library (no external libraries, works offline).
   Every function returns an HTML/SVG string. Colors are CSS variables so dark mode works. */
const Charts = (function () {
  const TEXT = 'style="fill:var(--muted)" font-size="10" font-family="inherit"';

  function niceMax(v) {
    if (v <= 0) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  }
  const short = (n) => (n >= 1000 ? (n / 1000).toFixed(n % 1000 ? 1 : 0).replace(/\.0$/, "") + "k" : String(Math.round(n)));

  /* progress ring with HTML in the middle */
  function ring(o) {
    const size = o.size || 120, stroke = o.stroke || 12, r = (size - stroke) / 2, c = 2 * Math.PI * r, h = size / 2;
    const pct = Math.max(0, Math.min(1, o.max > 0 ? o.value / o.max : 0));
    return '<div class="ring" style="width:' + size + "px;height:" + size + 'px">' +
      '<svg viewBox="0 0 ' + size + " " + size + '" width="' + size + '" height="' + size + '" aria-hidden="true">' +
      '<circle cx="' + h + '" cy="' + h + '" r="' + r + '" fill="none" stroke-width="' + stroke + '" style="stroke:var(--track)"/>' +
      '<circle class="ring-fg" cx="' + h + '" cy="' + h + '" r="' + r + '" fill="none" stroke-width="' + stroke +
      '" stroke-linecap="round" stroke-dasharray="' + c + '" transform="rotate(-90 ' + h + " " + h + ')" style="stroke:' +
      o.color + ";--c:" + c + ";stroke-dashoffset:" + c * (1 - pct) + '"/></svg>' +
      '<div class="ring-center">' + (o.center || "") + "</div></div>";
  }

  /* donut: segments = [{value, color}] */
  function donut(segments, o) {
    o = o || {};
    const size = o.size || 140, stroke = o.stroke || 20, r = (size - stroke) / 2, c = 2 * Math.PI * r, h = size / 2;
    const total = segments.reduce((s, x) => s + x.value, 0);
    let out = '<div class="ring" style="width:' + size + "px;height:" + size + 'px"><svg viewBox="0 0 ' + size + " " + size +
      '" width="' + size + '" height="' + size + '" aria-hidden="true"><circle cx="' + h + '" cy="' + h + '" r="' + r +
      '" fill="none" stroke-width="' + stroke + '" style="stroke:var(--track)"/>';
    if (total > 0) {
      let offset = 0;
      segments.forEach((s) => {
        if (s.value <= 0) return;
        const len = s.value / total * c, gap = segments.filter((x) => x.value > 0).length > 1 ? 2 : 0;
        out += '<circle cx="' + h + '" cy="' + h + '" r="' + r + '" fill="none" stroke-width="' + stroke +
          '" stroke-dasharray="' + Math.max(len - gap, 0.1) + " " + c + '" stroke-dashoffset="' + -offset +
          '" transform="rotate(-90 ' + h + " " + h + ')" style="stroke:' + s.color + '"/>';
        offset += len;
      });
    }
    return out + '</svg><div class="ring-center">' + (o.center || "") + "</div></div>";
  }

  /* vertical bars: {labels, values, colors, target, height} */
  function bars(o) {
    const W = 360, H = o.height || 190, pad = { l: 36, r: 6, t: 10, b: 24 };
    const n = o.values.length, top = niceMax(Math.max(o.target || 0, Math.max.apply(null, o.values), 1) * 1.05);
    const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b, step = iw / n, bw = Math.min(30, step * 0.62);
    const y = (v) => pad.t + ih - v / top * ih;
    let s = '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + (o.label || "Bar chart") + '">';
    for (let i = 0; i <= 4; i++) {
      const v = top * i / 4;
      s += '<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + y(v) + '" y2="' + y(v) + '" style="stroke:var(--line)"/>' +
        '<text x="' + (pad.l - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end" ' + TEXT + ">" + short(v) + "</text>";
    }
    o.values.forEach((v, i) => {
      const x = pad.l + step * i + (step - bw) / 2, hgt = Math.max(0, pad.t + ih - y(v));
      s += '<rect x="' + x + '" y="' + y(v) + '" width="' + bw + '" height="' + hgt + '" rx="4" style="fill:' +
        ((o.colors && o.colors[i]) || "var(--accent)") + '"><title>' + o.labels[i] + ": " + Math.round(v) + (o.unit || "") + "</title></rect>" +
        '<text x="' + (x + bw / 2) + '" y="' + (H - 8) + '" text-anchor="middle" ' + TEXT + ">" + o.labels[i] + "</text>";
    });
    if (o.target) {
      s += '<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + y(o.target) + '" y2="' + y(o.target) +
        '" stroke-dasharray="5 4" stroke-width="1.5" style="stroke:var(--ink);opacity:.55"/>' +
        '<text x="' + (W - pad.r) + '" y="' + (y(o.target) - 4) + '" text-anchor="end" ' + TEXT + ">target</text>";
    }
    return s + "</svg>";
  }

  /* line chart: {labels, values (null = no data), color, min, max, height} */
  function line(o) {
    const W = 360, H = o.height || 190, pad = { l: 36, r: 10, t: 12, b: 24 };
    const real = o.values.filter((v) => v != null);
    let lo = o.min != null ? o.min : (real.length ? Math.min.apply(null, real) : 0);
    let hi = o.max != null ? o.max : (real.length ? Math.max.apply(null, real) : 1);
    if (o.min == null) { const padv = (hi - lo || 1) * 0.2; lo -= padv; hi += padv; }
    const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b, n = o.values.length;
    const x = (i) => pad.l + (n === 1 ? iw / 2 : iw * i / (n - 1)), y = (v) => pad.t + ih - (v - lo) / (hi - lo) * ih;
    const color = o.color || "var(--accent)";
    let s = '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + (o.label || "Line chart") + '">';
    for (let i = 0; i <= 4; i++) {
      const v = lo + (hi - lo) * i / 4;
      s += '<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + y(v) + '" y2="' + y(v) + '" style="stroke:var(--line)"/>' +
        '<text x="' + (pad.l - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end" ' + TEXT + ">" + (o.yFmt ? o.yFmt(v) : Math.round(v)) + "</text>";
    }
    const pts = o.values.map((v, i) => (v == null ? null : [x(i), y(v), v, i])).filter(Boolean);
    if (pts.length > 1) {
      s += '<path d="M' + pts.map((p) => p[0] + " " + p[1]).join(" L") + '" fill="none" stroke-width="2.5" stroke-linejoin="round" style="stroke:' + color + '"/>';
    }
    pts.forEach((p) => {
      s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="3.5" style="fill:var(--panel);stroke:' + color + '" stroke-width="2"><title>' +
        o.labels[p[3]] + ": " + (o.yFmt ? o.yFmt(p[2]) : p[2]) + "</title></circle>";
    });
    const every = Math.ceil(n / 8);
    o.labels.forEach((l, i) => {
      if (i === n - 1 || (i % every === 0 && n - 1 - i >= every)) s += '<text x="' + x(i) + '" y="' + (H - 8) + '" text-anchor="middle" ' + TEXT + ">" + l + "</text>";
    });
    return s + "</svg>";
  }

  /* horizontal progress bar row (HTML) */
  function meter(label, value, max, color, right) {
    const pct = max > 0 ? Math.min(value / max, 1) * 100 : 0;
    return '<div class="meter"><div class="meter-top"><span>' + label + "</span><span>" + right + "</span></div>" +
      '<div class="bar"><i style="--w:' + pct + "%;--c:" + color + '"></i></div></div>';
  }

  return { ring: ring, donut: donut, bars: bars, line: line, meter: meter };
})();
