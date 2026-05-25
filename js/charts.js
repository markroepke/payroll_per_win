/* ============================================================
 * Front Office Scorecard — chart rendering
 * Reads CSVs from /data and renders inline SVG into [data-chart] divs.
 * Palette and typography match the report shell.
 * ============================================================ */

(function () {
  const THEME = {
    paper:    "#f4ede0",
    paper2:   "#ece3d2",
    ink:      "#1a1612",
    ink2:     "#3a342c",
    ink3:     "#6b6357",
    rule:     "#d9cfba",
    rule2:    "#c6b99e",
    accent:   "#8a2422",
    accentDp: "#5e1815",
    good:     "#355c3f",
    goodLt:   "#a8b693",
    bad:      "#8a2422",
    badLt:    "#c39286",
    neutral:  "#a89a82",
    serif:    '"Newsreader", Georgia, serif',
    sans:     '"IBM Plex Sans", system-ui, sans-serif',
    mono:     '"IBM Plex Mono", ui-monospace, monospace',
  };

  // ---------- CSV ----------
  function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = lines[0].split(",");
    return lines.slice(1).map(line => {
      const cells = line.split(",");
      const row = {};
      headers.forEach((h, i) => {
        const v = cells[i];
        const n = Number(v);
        row[h] = (v === "" || v === undefined) ? null
              : (!isNaN(n) && v !== "True" && v !== "False") ? n
              : (v === "True") ? true : (v === "False") ? false : v;
      });
      return row;
    });
  }

  async function loadCSV(path) {
    const res = await fetch(path);
    const txt = await res.text();
    return parseCSV(txt);
  }

  // ---------- SVG helpers ----------
  const svgNS = "http://www.w3.org/2000/svg";
  function el(tag, attrs = {}, children = []) {
    const e = document.createElementNS(svgNS, tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null) continue;
      e.setAttribute(k, v);
    }
    for (const c of [].concat(children)) {
      if (c == null) continue;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  }

  function mountSVG(target, w, h) {
    const root = el("svg", {
      viewBox: `0 0 ${w} ${h}`,
      xmlns: svgNS,
      width: "100%",
      height: "auto",
      style: `display:block; background:${THEME.paper}; font-family:${THEME.sans}`,
      "data-w": w, "data-h": h,
    });
    while (target.firstChild) target.removeChild(target.firstChild);
    target.appendChild(root);
    return root;
  }

  // Linear scale
  function scale(domain, range) {
    const [d0, d1] = domain, [r0, r1] = range;
    const k = (r1 - r0) / (d1 - d0);
    const f = (v) => r0 + (v - d0) * k;
    f.invert = (v) => d0 + (v - r0) / k;
    f.domain = domain; f.range = range;
    return f;
  }

  // ---------- Title block (scorecard style) ----------
  function chartTitle(parent, x, y, w, idx, eyebrow, title, subtitle) {
    // Top rule
    parent.appendChild(el("line", { x1:x, y1:y, x2:x+w, y2:y, stroke:THEME.ink, "stroke-width":1.2 }));
    // Fig number box (scorecard-style cell)
    parent.appendChild(el("rect", { x:x, y:y, width:64, height:30, fill:THEME.ink }));
    parent.appendChild(el("text", {
      x:x+32, y:y+20, "text-anchor":"middle",
      "font-family":THEME.mono, "font-size":11, "font-weight":700,
      "letter-spacing":"0.12em", fill:THEME.paper
    }, `FIG·${idx}`));
    // Eyebrow
    parent.appendChild(el("text", {
      x:x+76, y:y+20,
      "font-family":THEME.mono, "font-size":10, "font-weight":600,
      "letter-spacing":"0.18em", fill:THEME.accent
    }, eyebrow.toUpperCase()));
    // Title (serif)
    parent.appendChild(el("text", {
      x:x, y:y+58,
      "font-family":THEME.serif, "font-size":24, "font-weight":600,
      fill:THEME.ink, "letter-spacing":"-0.005em"
    }, title));
    if (subtitle) {
      parent.appendChild(el("text", {
        x:x, y:y+82,
        "font-family":THEME.serif, "font-size":15, "font-weight":400, "font-style":"italic",
        fill:THEME.ink3
      }, subtitle));
    }
    // Thin bottom rule
    parent.appendChild(el("line", {
      x1:x, y1:y+96, x2:x+w, y2:y+96,
      stroke:THEME.rule2, "stroke-width":1
    }));
  }

  function axisLabel(parent, x, y, text, opts = {}) {
    parent.appendChild(el("text", Object.assign({
      x, y,
      "font-family": THEME.mono,
      "font-size": 10,
      "font-weight": 600,
      "letter-spacing": "0.14em",
      fill: THEME.ink3,
      "text-anchor": "start",
    }, opts), text.toUpperCase()));
  }

  function gridX(parent, x, y, w, h, sx, ticks, fmt = String) {
    // vertical gridlines
    for (const t of ticks) {
      const X = sx(t);
      parent.appendChild(el("line", { x1:X, y1:y, x2:X, y2:y+h, stroke:THEME.rule, "stroke-width":0.6 }));
    }
    // x-axis line
    parent.appendChild(el("line", { x1:x, y1:y+h, x2:x+w, y2:y+h, stroke:THEME.ink, "stroke-width":1 }));
    // tick labels
    for (const t of ticks) {
      const X = sx(t);
      parent.appendChild(el("line", { x1:X, y1:y+h, x2:X, y2:y+h+5, stroke:THEME.ink, "stroke-width":1 }));
      parent.appendChild(el("text", {
        x:X, y:y+h+18, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink2,
        "font-variant-numeric":"tabular-nums"
      }, fmt(t)));
    }
  }

  function gridY(parent, x, y, w, h, sy, ticks, fmt = String) {
    for (const t of ticks) {
      const Y = sy(t);
      parent.appendChild(el("line", { x1:x, y1:Y, x2:x+w, y2:Y, stroke:THEME.rule, "stroke-width":0.6 }));
    }
    parent.appendChild(el("line", { x1:x, y1:y, x2:x, y2:y+h, stroke:THEME.ink, "stroke-width":1 }));
    for (const t of ticks) {
      const Y = sy(t);
      parent.appendChild(el("line", { x1:x-5, y1:Y, x2:x, y2:Y, stroke:THEME.ink, "stroke-width":1 }));
      parent.appendChild(el("text", {
        x:x-10, y:Y+4, "text-anchor":"end",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink2,
        "font-variant-numeric":"tabular-nums"
      }, fmt(t)));
    }
  }

  function ticksLinear(min, max, n=6) {
    const step = niceStep((max-min)/n);
    const out = [];
    const start = Math.ceil(min/step)*step;
    for (let v = start; v <= max + 1e-9; v += step) out.push(Math.round(v*1e6)/1e6);
    return out;
  }
  function niceStep(raw) {
    const e = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw/e;
    let nf;
    if (f < 1.5) nf = 1; else if (f < 3) nf = 2; else if (f < 7) nf = 5; else nf = 10;
    return nf*e;
  }
  function ticksLog(min, max) {
    const out = [];
    const lo = Math.floor(Math.log10(min));
    const hi = Math.ceil(Math.log10(max));
    for (let p = lo; p <= hi; p++) {
      for (const m of [1,2,5]) {
        const v = m * Math.pow(10,p);
        if (v >= min*0.95 && v <= max*1.05) out.push(v);
      }
    }
    return out;
  }

  // ============================================================
  // CHART 1: Payroll vs Pythagorean Wins (scatter + fit)
  // ============================================================
  function chartScatterPayrollWins(target, data) {
    const W=1240, H=720;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "01",
      "League shape · 2000—2025 · 780 team-seasons",
      "Payroll buys wins, with diminishing returns",
      "Each additional dollar buys fewer wins as payroll grows"
    );

    const M = { l: 100, r: 40, t: 160, b: 80 };
    const plotW = W - M.l - M.r, plotH = H - M.t - M.b;
    const px = (v) => v;

    const xDomain = [0, 350];
    const yDomain = [40, 110];
    const sx = scale(xDomain, [M.l, M.l + plotW]);
    const sy = scale(yDomain, [M.t + plotH, M.t]);

    // Plot frame
    svg.appendChild(el("rect", { x:M.l, y:M.t, width:plotW, height:plotH, fill:THEME.paper2, opacity:0.5 }));

    // Grid + axes
    const xT = [0, 50, 100, 150, 200, 250, 300];
    const yT = [50,60,70,80,90,100];
    gridX(svg, M.l, M.t, plotW, plotH, (v)=>sx(px(v)), xT, v => "$"+v+"M");
    gridY(svg, M.l, M.t, plotW, plotH, sy, yT);

    // Axis titles
    axisLabel(svg, M.l, H-30, "Opening Day Payroll  ($M, nominal)");
    svg.appendChild(el("g", { transform:`translate(30,${M.t+plotH/2}) rotate(-90)` }, [
      el("text", {
        "font-family":THEME.mono, "font-size":10, "font-weight":600,
        "letter-spacing":"0.14em", fill:THEME.ink3, "text-anchor":"middle",
      }, "PYTHAGOREAN WINS  (162-GAME BASIS)")
    ]));

    // Fit (log of payroll → linear in wins). Compute coefficients.
    let n=0, sxx=0, sxy=0, sxsum=0, sysum=0;
    let payMin = Infinity, payMax = -Infinity;
    for (const r of data) {
      const payM = r.opening_day_payroll_usd/1e6;
      const x = Math.log(payM);
      const y = r.pyth_wins_162;
      sxsum += x; sysum += y; sxx += x*x; sxy += x*y; n++;
      if (payM < payMin) payMin = payM;
      if (payM > payMax) payMax = payM;
    }
    const slope = (n*sxy - sxsum*sysum) / (n*sxx - sxsum*sxsum);
    const intercept = (sysum - slope*sxsum) / n;

    // Fit curve drawn on a linear x-axis. The model is still log in payroll,
    // so the curve visibly bends — that bend IS the diminishing returns.
    const curvePts = [];
    const step = (payMax - payMin) / 400;
    for (let pay = payMin; pay <= payMax; pay += step) {
      const yFit = slope*Math.log(pay) + intercept;
      curvePts.push(`${sx(pay)},${sy(yFit)}`);
    }

    // Scatter points
    const ptsG = el("g", { opacity: 0.55 });
    for (const r of data) {
      const x = sx(px(r.opening_day_payroll_usd/1e6));
      const y = sy(r.pyth_wins_162);
      const t = (r.season - 2000) / 25;
      // Color: warm sepia → cooler indigo across time (subtle)
      const col = lerpColor("#a8835c", "#3a486b", t);
      ptsG.appendChild(el("circle", {
        cx:x, cy:y, r:3.4, fill:col, stroke:"#000", "stroke-opacity":0.25, "stroke-width":0.4
      }));
    }
    svg.appendChild(ptsG);

    // Fit curve
    svg.appendChild(el("polyline", {
      points: curvePts.join(" "), fill:"none",
      stroke: THEME.accent, "stroke-width": 2.4
    }));

    // Annotation: equation
    const eqY = M.t + 22;
    const eqBoxW = 400;
    svg.appendChild(el("rect", {
      x: W - M.r - eqBoxW, y: eqY - 18, width: eqBoxW, height: 56,
      fill: THEME.paper, stroke: THEME.rule2, "stroke-width": 1
    }));
    svg.appendChild(el("text", {
      x: W - M.r - eqBoxW + 12, y: eqY,
      "font-family":THEME.mono, "font-size":10, "font-weight":700,
      "letter-spacing":"0.14em", fill:THEME.accent
    }, "LEAGUE FIT"));
    svg.appendChild(el("text", {
      x: W - M.r - eqBoxW + 12, y: eqY + 22,
      "font-family":THEME.mono, "font-size":13, "font-weight":500, fill: THEME.ink
    }, `pyth wins = ${slope.toFixed(2)} · ln(payroll$M) + ${intercept.toFixed(1)}`));

    // Decorative scorecard mark — small diamond
    drawDiamondGlyph(svg, W - 80, H - 50, 16);
  }

  // ============================================================
  // CHART 1b: Per-season log fits (robustness for FIG·01)
  // ============================================================
  function chartScatterPerSeasonFits(target, teamSeason, seasonFits) {
    const W=1240, H=720;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "1b",
      "Robustness · 26 per-season fits",
      "The concave shape holds in every season",
      "Within-year slopes are steeper than the pooled fit — payroll inflation flattens the across-year view"
    );

    const M = { l: 100, r: 40, t: 160, b: 80 };
    const plotW = W - M.l - M.r, plotH = H - M.t - M.b;
    const xDomain = [0, 350];
    const yDomain = [50, 110];
    const sx = scale(xDomain, [M.l, M.l + plotW]);
    const sy = scale(yDomain, [M.t + plotH, M.t]);

    svg.appendChild(el("rect", { x:M.l, y:M.t, width:plotW, height:plotH, fill:THEME.paper2, opacity:0.5 }));

    const xT = [0, 50, 100, 150, 200, 250, 300];
    const yT = [50, 60, 70, 80, 90, 100, 110];
    gridX(svg, M.l, M.t, plotW, plotH, sx, xT, v => "$"+v+"M");
    gridY(svg, M.l, M.t, plotW, plotH, sy, yT);

    axisLabel(svg, M.l, H-30, "Opening Day Payroll  ($M, nominal)");
    svg.appendChild(el("g", { transform:`translate(30,${M.t+plotH/2}) rotate(-90)` }, [
      el("text", {
        "font-family":THEME.mono, "font-size":10, "font-weight":600,
        "letter-spacing":"0.14em", fill:THEME.ink3, "text-anchor":"middle",
      }, "PYTHAGOREAN WINS  (162-GAME BASIS)")
    ]));

    // Per-season payroll range ($M) — used to clip each curve to its data
    const seasonRange = new Map();
    for (const r of teamSeason) {
      const s = +r.season;
      const payM = r.opening_day_payroll_usd / 1e6;
      const rec = seasonRange.get(s);
      if (!rec) seasonRange.set(s, { min: payM, max: payM });
      else { if (payM < rec.min) rec.min = payM; if (payM > rec.max) rec.max = payM; }
    }

    const fits = seasonFits.slice().sort((a,b) => +a.season - +b.season);
    const minSeason = +fits[0].season;
    const maxSeason = +fits[fits.length-1].season;
    const colorFor = (s) => lerpColor("#a8835c", "#3a486b", (s - minSeason) / (maxSeason - minSeason));

    // 26 per-season curves
    for (const row of fits) {
      const s = +row.season;
      const slope = +row.slope_pyth_wins_per_log_dollarM;
      const intercept = +row.intercept;
      const rng = seasonRange.get(s);
      if (!rng) continue;
      const col = colorFor(s);

      const pts = [];
      const step = (rng.max - rng.min) / 80;
      for (let pay = rng.min; pay <= rng.max + 1e-9; pay += step) {
        const yFit = slope * Math.log(pay) + intercept;
        pts.push(`${sx(pay)},${sy(yFit)}`);
      }
      svg.appendChild(el("polyline", {
        points: pts.join(" "), fill:"none",
        stroke: col, "stroke-width": 1.3, opacity: 0.55
      }));
    }

    // Pooled fit (computed here so it stays honest to the loaded data)
    let n=0, sxx=0, sxy=0, sxsum=0, sysum=0;
    let payMinAll = Infinity, payMaxAll = -Infinity;
    for (const r of teamSeason) {
      const payM = r.opening_day_payroll_usd / 1e6;
      const lx = Math.log(payM), y = +r.pyth_wins_162;
      sxsum += lx; sysum += y; sxx += lx*lx; sxy += lx*y; n++;
      if (payM < payMinAll) payMinAll = payM;
      if (payM > payMaxAll) payMaxAll = payM;
    }
    const pSlope = (n*sxy - sxsum*sysum) / (n*sxx - sxsum*sxsum);
    const pIntercept = (sysum - pSlope*sxsum) / n;
    const poolPts = [];
    const pStep = (payMaxAll - payMinAll) / 400;
    for (let pay = payMinAll; pay <= payMaxAll + 1e-9; pay += pStep) {
      poolPts.push(`${sx(pay)},${sy(pSlope * Math.log(pay) + pIntercept)}`);
    }
    svg.appendChild(el("polyline", {
      points: poolPts.join(" "), fill:"none",
      stroke: THEME.accent, "stroke-width": 3.2
    }));

    // Annotation: pooled fit + per-season slope range (upper-right of plot)
    const slopes = fits.map(f => +f.slope_pyth_wins_per_log_dollarM).sort((a,b) => a-b);
    const mid = slopes.length >>> 1;
    const median = slopes.length % 2 ? slopes[mid] : (slopes[mid-1] + slopes[mid]) / 2;
    const minS = slopes[0], maxS = slopes[slopes.length-1];

    const annW = 400, annH = 78;
    const annX = W - M.r - annW;
    const annY = M.t + 12;
    svg.appendChild(el("rect", {
      x: annX, y: annY, width: annW, height: annH,
      fill: THEME.paper, stroke: THEME.rule2, "stroke-width": 1
    }));
    svg.appendChild(el("text", {
      x: annX+14, y: annY+22,
      "font-family":THEME.mono, "font-size":10, "font-weight":700,
      "letter-spacing":"0.14em", fill:THEME.accent
    }, "POOLED FIT (RED) vs. PER-SEASON FITS"));
    svg.appendChild(el("text", {
      x: annX+14, y: annY+44,
      "font-family":THEME.mono, "font-size":13, "font-weight":500, fill: THEME.ink
    }, `pooled slope = ${pSlope.toFixed(2)} · ln($M)`));
    svg.appendChild(el("text", {
      x: annX+14, y: annY+64,
      "font-family":THEME.mono, "font-size":11, "font-weight":500, fill: THEME.ink3
    }, `per-season slopes ${minS.toFixed(1)}–${maxS.toFixed(1)}, median ${median.toFixed(1)}`));

    // Year color key (horizontal strip below annotation, inside plot)
    const keyW = 180, keyH = 8;
    const keyX0 = W - M.r - keyW - 14;
    const keyY = annY + annH + 14;
    const nYears = maxSeason - minSeason + 1;
    for (let i = 0; i < nYears; i++) {
      const t = nYears === 1 ? 0 : i / (nYears - 1);
      svg.appendChild(el("rect", {
        x: keyX0 + (keyW/nYears)*i, y: keyY,
        width: keyW/nYears + 0.5, height: keyH,
        fill: lerpColor("#a8835c", "#3a486b", t)
      }));
    }
    svg.appendChild(el("text", {
      x: keyX0, y: keyY - 4, "text-anchor":"start",
      "font-family":THEME.mono, "font-size":9, "font-weight":600,
      "letter-spacing":"0.1em", fill: THEME.ink3
    }, String(minSeason)));
    svg.appendChild(el("text", {
      x: keyX0 + keyW, y: keyY - 4, "text-anchor":"end",
      "font-family":THEME.mono, "font-size":9, "font-weight":600,
      "letter-spacing":"0.1em", fill: THEME.ink3
    }, String(maxSeason)));
  }

  function lerpColor(a, b, t) {
    const pa = hex(a), pb = hex(b);
    const r = Math.round(pa[0]+(pb[0]-pa[0])*t);
    const g = Math.round(pa[1]+(pb[1]-pa[1])*t);
    const bl = Math.round(pa[2]+(pb[2]-pa[2])*t);
    return `rgb(${r},${g},${bl})`;
  }
  function hex(h){const x=h.replace("#","");return [parseInt(x.slice(0,2),16),parseInt(x.slice(2,4),16),parseInt(x.slice(4,6),16)];}

  function drawDiamondGlyph(parent, cx, cy, r) {
    const ink = THEME.ink3;
    // Diamond outline
    parent.appendChild(el("polygon", {
      points: `${cx},${cy-r} ${cx+r},${cy} ${cx},${cy+r} ${cx-r},${cy}`,
      fill: "none", stroke: ink, "stroke-width": 1
    }));
    // Bases
    for (const [bx,by] of [[cx,cy-r],[cx+r,cy],[cx,cy+r],[cx-r,cy]]) {
      parent.appendChild(el("rect", { x: bx-2.5, y: by-2.5, width:5, height:5,
        fill: THEME.paper, stroke: ink, "stroke-width": 1, transform:`rotate(45 ${bx} ${by})` }));
    }
  }

  // ============================================================
  // CHART 2: What money buys (3-panel)
  // ============================================================
  function chartWhatMoneyBuys(target, teamSeason, playoffs, wsWinners) {
    const W=1240, H=720;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "02",
      "Payroll quintile · 2000—2025",
      "What MLB payroll buys (and doesn't)",
      "Money buys regular-season wins reliably, playoff trips often, championships almost exclusively"
    );

    // Compute quintiles per season
    const bySeason = {};
    for (const r of teamSeason) {
      (bySeason[r.season] = bySeason[r.season] || []).push(r);
    }
    const labels = ["Top 20%", "Q2", "Q3", "Q4", "Bottom 20%"];
    const buckets = [[],[],[],[],[]];
    for (const yr of Object.values(bySeason)) {
      const sorted = yr.slice().sort((a,b)=>b.opening_day_payroll_usd-a.opening_day_payroll_usd);
      sorted.forEach((r, i) => {
        const q = Math.min(4, Math.floor(i/6));
        buckets[q].push(r);
      });
    }
    const poSet = new Set(playoffs.map(p => `${p.season}|${p.team}`));
    const wsSet = new Set(wsWinners.map(p => `${p.season}|${p.team}`));

    const stats = buckets.map(rows => ({
      meanW: rows.reduce((a,r)=>a+r.prorated_wins,0)/rows.length,
      poRate: rows.filter(r=>poSet.has(`${r.season}|${r.team}`)).length / rows.length,
      titles: rows.filter(r=>wsSet.has(`${r.season}|${r.team}`)).length,
    }));

    // Panel layout
    const panelTitles = [
      ["WINS",         "Mean wins",        v => v.toFixed(1),         "meanW",  [60, 95],  THEME.ink],
      ["PLAYOFFS",     "Playoff rate",     v => Math.round(v*100)+"%","poRate", [0, 0.7],  THEME.good],
      ["WORLD SERIES", "Titles 2000—25",  v => String(v),            "titles", [0, 14],   THEME.accent],
    ];
    const panelW = (W - 120 - 80) / 3;
    const panelH = 380;
    const panelY = 200;

    panelTitles.forEach((p, pi) => {
      const [code, sub, fmt, key, ydom, col] = p;
      const x0 = 60 + pi * (panelW + 40);
      // Panel header (scorecard cell)
      svg.appendChild(el("rect", { x:x0, y:panelY-50, width:panelW, height:32,
        fill:"none", stroke:THEME.ink, "stroke-width":1 }));
      // Width of the colored badge sized to fit the label
      const badgeW = code === "WORLD SERIES" ? 130 : 92;
      svg.appendChild(el("rect", { x:x0, y:panelY-50, width:badgeW, height:32, fill: col }));
      svg.appendChild(el("text", {
        x:x0 + badgeW/2, y:panelY-30, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, "font-weight":700, "letter-spacing":"0.14em",
        fill: THEME.paper
      }, code));
      svg.appendChild(el("text", {
        x: x0 + badgeW + 12, y: panelY-30,
        "font-family":THEME.serif, "font-size":14, "font-weight":500, fill: THEME.ink2,
        "font-style":"italic"
      }, sub));

      // Plot
      const px0 = x0+24, py0 = panelY, pw = panelW-24-12, ph = panelH-80;
      const sx = scale([0, 5], [px0, px0+pw]);
      const sy = scale(ydom, [py0+ph, py0]);

      // Y gridlines
      const yTicks = key==="meanW" ? [60,70,80,90] :
                     key==="poRate" ? [0,0.2,0.4,0.6] :
                     [0,5,10];
      for (const t of yTicks) {
        const Y = sy(t);
        svg.appendChild(el("line", { x1:px0, y1:Y, x2:px0+pw, y2:Y, stroke:THEME.rule, "stroke-width":0.5 }));
        svg.appendChild(el("text", {
          x:px0-8, y:Y+4, "text-anchor":"end",
          "font-family":THEME.mono, "font-size":10, fill:THEME.ink3
        }, fmt(t)));
      }
      // Baseline
      svg.appendChild(el("line", { x1:px0, y1:py0+ph, x2:px0+pw, y2:py0+ph, stroke:THEME.ink, "stroke-width":1 }));

      // Bars
      const bw = pw/5 * 0.62;
      stats.forEach((s, i) => {
        const v = s[key];
        const cx = sx(i+0.5);
        const yT = sy(v);
        const yB = sy(ydom[0]);
        svg.appendChild(el("rect", {
          x: cx-bw/2, y: yT, width: bw, height: yB-yT,
          fill: col, opacity: 0.85
        }));
        // Value label above bar
        svg.appendChild(el("text", {
          x: cx, y: yT-8, "text-anchor":"middle",
          "font-family":THEME.mono, "font-size":13, "font-weight":700, fill: THEME.ink
        }, fmt(v)));
        // Quintile label below
        svg.appendChild(el("text", {
          x: cx, y: py0+ph+18, "text-anchor":"middle",
          "font-family":THEME.mono, "font-size":10, "font-weight":600,
          "letter-spacing":"0.06em", fill: THEME.ink3
        }, labels[i].toUpperCase()));
      });
    });

    // Note at bottom
    svg.appendChild(el("text", {
      x: 60, y: H - 30,
      "font-family": THEME.serif, "font-style":"italic", "font-size":13, fill: THEME.ink3
    }, "Each quintile contains 156 team-seasons (6 teams × 26 years). Win counts are 2020-prorated."));
  }

  // ============================================================
  // CHART 3: Franchise skill bar (with 95% CI)
  // ============================================================
  function chartFranchiseSkill(target, ranking, teamSeasonSkill) {
    // Compute SE per team from team_season_skill residuals
    const grouped = {};
    for (const r of teamSeasonSkill) {
      (grouped[r.team] = grouped[r.team] || []).push(r.wins_above_expected);
    }
    const merged = ranking.map(r => {
      const arr = grouped[r.team] || [];
      const n = arr.length;
      const mean = arr.reduce((a,b)=>a+b,0)/n;
      const sd = Math.sqrt(arr.reduce((a,b)=>a+(b-mean)*(b-mean),0)/(n-1));
      const se = sd / Math.sqrt(n);
      return {
        team: r.team,
        mean: r.mean_wins_above_expected,
        ciLo: r.mean_wins_above_expected - 1.96*se,
        ciHi: r.mean_wins_above_expected + 1.96*se,
        se,
      };
    });
    merged.sort((a,b) => a.mean - b.mean);

    const W=1240, H=940;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "03",
      "Skill ranking · all 30 franchises",
      "Pythagorean wins above payroll-expected, per season",
      "Bars colored when 95% CI clears zero; gray when the interval crosses it"
    );

    const M = { l: 140, r: 260, t: 170, b: 70 };
    const plotW = W - M.l - M.r;
    const plotH = H - M.t - M.b;
    const xDomain = [-13, 13];
    const sx = scale(xDomain, [M.l, M.l+plotW]);
    const rowH = plotH / merged.length;

    // Plot frame
    svg.appendChild(el("rect", { x:M.l, y:M.t, width:plotW, height:plotH, fill: THEME.paper2, opacity: 0.4 }));

    // Gridlines
    const xT = [-12,-9,-6,-3,0,3,6,9,12];
    for (const t of xT) {
      const X = sx(t);
      svg.appendChild(el("line", { x1:X, y1:M.t, x2:X, y2:M.t+plotH,
        stroke: t===0 ? THEME.ink : THEME.rule,
        "stroke-width": t===0 ? 1.2 : 0.5
      }));
    }
    // X axis labels (top + bottom)
    for (const t of xT) {
      const X = sx(t);
      svg.appendChild(el("text", { x:X, y:M.t-10, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3,
        "font-variant-numeric":"tabular-nums"
      }, t>0?`+${t}`:String(t)));
      svg.appendChild(el("text", { x:X, y:M.t+plotH+22, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3,
        "font-variant-numeric":"tabular-nums"
      }, t>0?`+${t}`:String(t)));
    }
    axisLabel(svg, M.l, H-30, "Mean Wins Above Expected, per Season  (Pythagorean, 162-game basis)");

    // Bars
    merged.forEach((r, i) => {
      const y = M.t + i*rowH;
      const cy = y + rowH/2;
      const x0 = sx(0);
      const xv = sx(r.mean);
      let color = THEME.neutral;
      let lbl = "noise";
      if (r.ciLo > 0) { color = THEME.good; lbl = "skilled"; }
      else if (r.ciHi < 0) { color = THEME.bad; lbl = "unskilled"; }

      const bx = Math.min(x0, xv);
      const bw = Math.abs(xv - x0);

      // Subtle row stripe
      if (i % 2 === 0) {
        svg.appendChild(el("rect", {
          x:M.l, y:y, width:plotW, height:rowH, fill: THEME.ink, opacity: 0.025
        }));
      }

      svg.appendChild(el("rect", {
        x: bx, y: cy - rowH*0.35, width: bw, height: rowH*0.70,
        fill: color, opacity: 0.92
      }));

      // 95% CI bar
      svg.appendChild(el("line", {
        x1: sx(r.ciLo), x2: sx(r.ciHi), y1: cy, y2: cy,
        stroke: THEME.ink, "stroke-width": 1.4
      }));
      // Caps
      for (const v of [r.ciLo, r.ciHi]) {
        svg.appendChild(el("line", {
          x1: sx(v), x2: sx(v), y1: cy-5, y2: cy+5, stroke: THEME.ink, "stroke-width": 1.4
        }));
      }

      // Team name (left, ranked from worst→best)
      svg.appendChild(el("text", {
        x: M.l - 14, y: cy+4, "text-anchor":"end",
        "font-family":THEME.serif, "font-size":14, "font-weight":500, fill: THEME.ink
      }, teamShort(r.team)));

      // Rank number
      svg.appendChild(el("text", {
        x: M.l - 14, y: cy - 9, "text-anchor":"end",
        "font-family":THEME.mono, "font-size":9, "font-weight":600, fill: THEME.ink3,
        "letter-spacing":"0.1em"
      }, `#${merged.length - i}`));

      // Right side: value + CI
      svg.appendChild(el("text", {
        x: M.l + plotW + 14, y: cy+4,
        "font-family":THEME.mono, "font-size":13, "font-weight":700,
        fill: color, "font-variant-numeric":"tabular-nums"
      }, `${r.mean>=0?"+":""}${r.mean.toFixed(1)}`));
      svg.appendChild(el("text", {
        x: M.l + plotW + 70, y: cy+4,
        "font-family":THEME.mono, "font-size":10, fill: THEME.ink3,
        "font-variant-numeric":"tabular-nums"
      }, `[${r.ciLo>=0?"+":""}${r.ciLo.toFixed(1)}, ${r.ciHi>=0?"+":""}${r.ciHi.toFixed(1)}]`));
    });

    // Legend
    const lgY = M.t - 50;
    const lgItems = [
      { col: THEME.bad,     lbl: "Unskilled  (CI < 0)" },
      { col: THEME.neutral, lbl: "Noise  (CI crosses 0)" },
      { col: THEME.good,    lbl: "Skilled  (CI > 0)" },
    ];
    lgItems.forEach((it, i) => {
      const x = W - M.r - 60 - (lgItems.length-1-i)*180;
      svg.appendChild(el("rect", { x:x, y:lgY-10, width:14, height:14, fill: it.col }));
      svg.appendChild(el("text", {
        x:x+22, y:lgY+2,
        "font-family":THEME.mono, "font-size":10, "font-weight":600, "letter-spacing":"0.08em",
        fill: THEME.ink2
      }, it.lbl.toUpperCase()));
    });
  }

  // ============================================================
  // CHART 4: Cumulative dollars per win
  // ============================================================
  function chartDollarsPerWin(target, ranked) {
    const W=1240, H=880;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "04",
      "Naive efficiency · for reference",
      "Cumulative dollars per win, 2000—2025",
      "Why a low number isn't the same as a smart front office"
    );

    const data = ranked.slice().sort((a,b) => a.cumulative_dollars_per_win - b.cumulative_dollars_per_win);

    const M = { l: 210, r: 130, t: 170, b: 70 };
    const plotW = W - M.l - M.r;
    const plotH = H - M.t - M.b;
    const xMax = Math.ceil(data[data.length-1].cumulative_dollars_per_win/1e6 * 1.1);
    const sx = scale([0, xMax], [M.l, M.l+plotW]);
    const rowH = plotH / data.length;

    svg.appendChild(el("rect", { x:M.l, y:M.t, width:plotW, height:plotH, fill:THEME.paper2, opacity:0.4 }));

    // grid
    const xT = ticksLinear(0, xMax, 5);
    for (const t of xT) {
      const X = sx(t);
      svg.appendChild(el("line", { x1:X, y1:M.t, x2:X, y2:M.t+plotH, stroke:THEME.rule, "stroke-width":0.5 }));
      svg.appendChild(el("text", { x:X, y:M.t-10, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3
      }, "$"+t.toFixed(1)+"M"));
      svg.appendChild(el("text", { x:X, y:M.t+plotH+22, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3
      }, "$"+t.toFixed(1)+"M"));
    }
    axisLabel(svg, M.l, H-30, "Cumulative $ per Win  ($M, nominal · lower = cheaper)");

    data.forEach((r,i) => {
      const v = r.cumulative_dollars_per_win/1e6;
      const y = M.t + i*rowH;
      const cy = y + rowH/2;
      // alt stripe
      if (i % 2 === 0) svg.appendChild(el("rect", { x:M.l, y:y, width:plotW, height:rowH, fill:THEME.ink, opacity:0.025 }));
      svg.appendChild(el("rect", {
        x: sx(0), y: cy-rowH*0.32, width: sx(v)-sx(0), height: rowH*0.64,
        fill: THEME.ink2
      }));
      svg.appendChild(el("text", {
        x: M.l-14, y: cy+4, "text-anchor":"end",
        "font-family":THEME.serif, "font-size":14, "font-weight":500, fill: THEME.ink
      }, teamShort(r.team)));
      svg.appendChild(el("text", {
        x: M.l-14, y: cy-9, "text-anchor":"end",
        "font-family":THEME.mono, "font-size":9, fill: THEME.ink3, "letter-spacing":"0.1em"
      }, `#${i+1}`));
      svg.appendChild(el("text", {
        x: sx(v)+8, y: cy+4,
        "font-family":THEME.mono, "font-size":12, "font-weight":600, fill: THEME.ink,
        "font-variant-numeric":"tabular-nums"
      }, "$"+v.toFixed(2)+"M"));
    });
  }

  // ============================================================
  // CHART 5: Franchise quadrants (payroll percentile × WAE)
  // ============================================================
  function chartQuadrants(target, teamSeason, ranking) {
    const W=1240, H=820;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "05",
      "Where each franchise lives · 2000—2025",
      "Payroll percentile vs. front-office skill",
      "The Dodgers occupy a quadrant no other big spender reaches"
    );

    // Compute mean payroll percentile per team
    const byTeam = {};
    const bySeason = {};
    for (const r of teamSeason) {
      (bySeason[r.season] = bySeason[r.season] || []).push(r);
    }
    for (const [, rows] of Object.entries(bySeason)) {
      const sorted = rows.slice().sort((a,b)=>a.opening_day_payroll_usd-b.opening_day_payroll_usd);
      sorted.forEach((r,i) => {
        const pct = i/(sorted.length-1)*100;
        (byTeam[r.team] = byTeam[r.team] || []).push(pct);
      });
    }
    const meanPct = Object.fromEntries(
      Object.entries(byTeam).map(([t,arr]) => [t, arr.reduce((a,b)=>a+b,0)/arr.length])
    );
    const points = ranking.map(r => ({
      team: r.team,
      x: meanPct[r.team],
      y: r.mean_wins_above_expected,
    }));

    const M = { l: 100, r: 40, t: 170, b: 80 };
    const plotW = W-M.l-M.r, plotH = H-M.t-M.b;
    const sx = scale([0, 100], [M.l, M.l+plotW]);
    const sy = scale([-9, 9], [M.t+plotH, M.t]);

    // Quadrant fills
    svg.appendChild(el("rect", { x:sx(50), y:M.t, width:sx(100)-sx(50), height:sy(0)-M.t,
      fill: THEME.good, opacity: 0.08 }));
    svg.appendChild(el("rect", { x:M.l, y:M.t, width:sx(50)-M.l, height:sy(0)-M.t,
      fill: THEME.good, opacity: 0.04 }));
    svg.appendChild(el("rect", { x:sx(50), y:sy(0), width:sx(100)-sx(50), height:M.t+plotH-sy(0),
      fill: THEME.bad, opacity: 0.08 }));
    svg.appendChild(el("rect", { x:M.l, y:sy(0), width:sx(50)-M.l, height:M.t+plotH-sy(0),
      fill: THEME.bad, opacity: 0.04 }));

    // Quadrant axes
    svg.appendChild(el("line", { x1:M.l, y1:sy(0), x2:M.l+plotW, y2:sy(0), stroke:THEME.ink, "stroke-width":1 }));
    svg.appendChild(el("line", { x1:sx(50), y1:M.t, x2:sx(50), y2:M.t+plotH, stroke:THEME.ink, "stroke-width":0.8, "stroke-dasharray":"4 4" }));

    // Ticks
    for (const t of [0,25,50,75,100]) {
      const X = sx(t);
      svg.appendChild(el("line", { x1:X, y1:M.t+plotH, x2:X, y2:M.t+plotH+5, stroke:THEME.ink }));
      svg.appendChild(el("text", { x:X, y:M.t+plotH+20, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3 }, t==0?"Cheap":t==100?"Pricey":String(t)));
    }
    for (const t of [-9,-6,-3,0,3,6,9]) {
      const Y = sy(t);
      svg.appendChild(el("line", { x1:M.l-5, y1:Y, x2:M.l, y2:Y, stroke:THEME.ink }));
      svg.appendChild(el("text", { x:M.l-10, y:Y+4, "text-anchor":"end",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3
      }, t>0?`+${t}`:String(t)));
    }
    axisLabel(svg, M.l, H-30, "Mean Payroll Percentile  ·  0 = cheapest in league, 100 = most expensive");
    svg.appendChild(el("g", { transform:`translate(28,${M.t+plotH/2}) rotate(-90)` }, [
      el("text", {
        "font-family":THEME.mono, "font-size":10, "font-weight":600,
        "letter-spacing":"0.14em", fill:THEME.ink3, "text-anchor":"middle"
      }, "MEAN WINS ABOVE EXPECTED")
    ]));

    // Quadrant labels
    svg.appendChild(el("text", { x: M.l+plotW-12, y: M.t+24, "text-anchor":"end",
      "font-family":THEME.serif, "font-style":"italic", "font-size":13, fill: THEME.good
    }, "Pricey · Skilled"));
    svg.appendChild(el("text", { x: M.l+12, y: M.t+24,
      "font-family":THEME.serif, "font-style":"italic", "font-size":13, fill: THEME.good
    }, "Cheap · Skilled"));
    svg.appendChild(el("text", { x: M.l+plotW-12, y: M.t+plotH-12, "text-anchor":"end",
      "font-family":THEME.serif, "font-style":"italic", "font-size":13, fill: THEME.bad
    }, "Pricey · Unskilled"));
    svg.appendChild(el("text", { x: M.l+12, y: M.t+plotH-12,
      "font-family":THEME.serif, "font-style":"italic", "font-size":13, fill: THEME.bad
    }, "Cheap · Unskilled"));

    // Dots
    const featured = new Set([
      "Oakland Athletics","Tampa Bay Rays","Cleveland Guardians","Los Angeles Dodgers",
      "New York Yankees","St. Louis Cardinals","Atlanta Braves",
      "Colorado Rockies","Detroit Tigers","Kansas City Royals","Pittsburgh Pirates",
      "New York Mets","Baltimore Orioles","Boston Red Sox","Houston Astros",
    ]);

    // Label collision avoidance: simple offset by index
    const placed = [];
    points.forEach(p => {
      const cx = sx(p.x), cy = sy(p.y);
      const isFeatured = featured.has(p.team);
      const col = p.y > 0 ? THEME.good : THEME.bad;
      svg.appendChild(el("circle", {
        cx, cy, r: isFeatured ? 6.5 : 4,
        fill: isFeatured ? col : THEME.neutral,
        stroke: THEME.ink, "stroke-width": isFeatured ? 0.9 : 0.5,
        opacity: isFeatured ? 1 : 0.55
      }));
      // Place label
      const label = teamShort(p.team);
      const fontSize = isFeatured ? 11.5 : 10;
      // Try several positions
      const candidates = [
        [12, 4, "start"], [-12, 4, "end"],
        [12, -8, "start"], [-12, -8, "end"],
        [12, 14, "start"], [-12, 14, "end"],
      ];
      let chosen = candidates[0];
      for (const c of candidates) {
        const lx = cx + c[0], ly = cy + c[1];
        // approx label box
        const approxW = label.length * fontSize * 0.55;
        const box = { x: c[2]==="end"? lx-approxW : lx, y: ly-fontSize, w: approxW, h: fontSize+2 };
        let ok = true;
        for (const b of placed) if (overlap(box, b)) { ok = false; break; }
        if (lx < M.l+4 || lx > M.l+plotW-4 || ly < M.t+8 || ly > M.t+plotH-4) ok = false;
        if (ok) { chosen = c; placed.push(box); break; }
      }
      svg.appendChild(el("text", {
        x: cx+chosen[0], y: cy+chosen[1], "text-anchor": chosen[2],
        "font-family": isFeatured ? THEME.sans : THEME.mono,
        "font-size": fontSize,
        "font-weight": isFeatured ? 600 : 400,
        fill: isFeatured ? THEME.ink : THEME.ink3
      }, label));
    });
  }
  function overlap(a, b) {
    return !(a.x+a.w < b.x || b.x+b.w < a.x || a.y+a.h < b.y || b.y+b.h < a.y);
  }
  function teamShort(name) {
    const map = {
      "Arizona Diamondbacks":"Diamondbacks", "Atlanta Braves":"Braves",
      "Baltimore Orioles":"Orioles", "Boston Red Sox":"Red Sox",
      "Chicago Cubs":"Cubs", "Chicago White Sox":"White Sox",
      "Cincinnati Reds":"Reds", "Cleveland Guardians":"Guardians",
      "Colorado Rockies":"Rockies", "Detroit Tigers":"Tigers",
      "Houston Astros":"Astros", "Kansas City Royals":"Royals",
      "Los Angeles Angels":"Angels", "Los Angeles Dodgers":"Dodgers",
      "Miami Marlins":"Marlins", "Milwaukee Brewers":"Brewers",
      "Minnesota Twins":"Twins", "New York Mets":"Mets",
      "New York Yankees":"Yankees", "Oakland Athletics":"Athletics",
      "Philadelphia Phillies":"Phillies", "Pittsburgh Pirates":"Pirates",
      "San Diego Padres":"Padres", "San Francisco Giants":"Giants",
      "Seattle Mariners":"Mariners", "St. Louis Cardinals":"Cardinals",
      "Tampa Bay Rays":"Rays", "Texas Rangers":"Rangers",
      "Toronto Blue Jays":"Blue Jays", "Washington Nationals":"Nationals",
    };
    return map[name] || name;
  }

  // ============================================================
  // CHART 6: Top/bottom team-seasons by WAE
  // ============================================================
  function chartExtremeSeasons(target, teamSeasonSkill, n=5) {
    const W=1240, H=620;
    const svg = mountSVG(target, W, H);
    chartTitle(svg, 60, 30, W-120, "06",
      "Single-season extremes · 2000—2025 · 2020 excluded",
      `The ${n} best and ${n} worst team-seasons by WAE`,
      "Highest peaks come from skilled franchises; deepest troughs from the unskilled ones"
    );

    const filtered = teamSeasonSkill.filter(r => r.season !== 2020);
    const sorted = filtered.slice().sort((a,b)=>b.wins_above_expected-a.wins_above_expected);
    const top = sorted.slice(0, n);
    const bot = sorted.slice(-n).reverse();
    const all = top.concat(bot).sort((a,b) => a.wins_above_expected - b.wins_above_expected);

    const M = { l: 240, r: 240, t: 170, b: 70 };
    const plotW = W-M.l-M.r, plotH = H-M.t-M.b;
    const ext = Math.max(
      Math.abs(all[0].wins_above_expected),
      Math.abs(all[all.length-1].wins_above_expected)
    );
    const xDomain = [-Math.ceil(ext/5)*5 - 5, Math.ceil(ext/5)*5 + 5];
    const sx = scale(xDomain, [M.l, M.l+plotW]);
    const rowH = plotH / all.length;

    svg.appendChild(el("rect", { x:M.l, y:M.t, width:plotW, height:plotH, fill:THEME.paper2, opacity:0.4 }));
    // grid
    for (let t = xDomain[0]; t <= xDomain[1]; t += 10) {
      const X = sx(t);
      svg.appendChild(el("line", { x1:X, y1:M.t, x2:X, y2:M.t+plotH,
        stroke: t===0 ? THEME.ink : THEME.rule,
        "stroke-width": t===0 ? 1.2 : 0.5
      }));
      svg.appendChild(el("text", { x:X, y:M.t+plotH+20, "text-anchor":"middle",
        "font-family":THEME.mono, "font-size":11, fill:THEME.ink3
      }, t>0?`+${t}`:String(t)));
    }
    axisLabel(svg, M.l, H-30, "Pythagorean Wins Above Payroll-Expected");

    all.forEach((r,i) => {
      const y = M.t + i*rowH;
      const cy = y + rowH/2;
      const v = r.wins_above_expected;
      const x0 = sx(0), xv = sx(v);
      const col = v > 0 ? THEME.good : THEME.bad;

      if (i % 2 === 0) svg.appendChild(el("rect", { x:M.l, y:y, width:plotW, height:rowH, fill:THEME.ink, opacity:0.025 }));
      svg.appendChild(el("rect", {
        x: Math.min(x0, xv), y: cy-rowH*0.32,
        width: Math.abs(xv-x0), height: rowH*0.64,
        fill: col, opacity: 0.92
      }));

      // Label left
      svg.appendChild(el("text", {
        x: M.l-14, y: cy-4, "text-anchor":"end",
        "font-family":THEME.serif, "font-size":15, "font-weight":600, fill: THEME.ink
      }, `${r.season} ${teamShort(r.team)}`));
      svg.appendChild(el("text", {
        x: M.l-14, y: cy+12, "text-anchor":"end",
        "font-family":THEME.mono, "font-size":10, fill: THEME.ink3
      }, `${Math.round(r.wins)} W · $${Math.round(r.opening_day_payroll_usd/1e6)}M`));

      // WAE value to the right
      svg.appendChild(el("text", {
        x: M.l+plotW+14, y: cy+5,
        "font-family":THEME.mono, "font-size":16, "font-weight":700, fill: col,
        "font-variant-numeric":"tabular-nums"
      }, `${v>=0?"+":""}${v.toFixed(1)}`));
    });
  }

  // ============================================================
  // Boot
  // ============================================================
  async function init() {
    try {
      const [teamSeason, teamSeasonSkill, ranking, ranked, playoffs, wsWinners, seasonFits] = await Promise.all([
        loadCSV("data/team_season.csv"),
        loadCSV("data/team_season_skill.csv"),
        loadCSV("data/franchise_skill_ranking.csv"),
        loadCSV("data/ranked_efficiency.csv"),
        loadCSV("data/playoff_teams.csv"),
        loadCSV("data/world_series_winners.csv"),
        loadCSV("data/season_fits.csv"),
      ]);

      const targets = {
        "scatter":     (t) => chartScatterPayrollWins(t, teamSeason),
        "seasonfits":  (t) => chartScatterPerSeasonFits(t, teamSeason, seasonFits),
        "money":       (t) => chartWhatMoneyBuys(t, teamSeason, playoffs, wsWinners),
        "skill":       (t) => chartFranchiseSkill(t, ranking, teamSeasonSkill),
        "dpw":         (t) => chartDollarsPerWin(t, ranked),
        "quadrants":   (t) => chartQuadrants(t, teamSeason, ranking),
        "extremes":    (t) => chartExtremeSeasons(t, teamSeasonSkill),
      };
      for (const div of document.querySelectorAll("[data-chart]")) {
        const k = div.getAttribute("data-chart");
        if (targets[k]) targets[k](div);
      }
    } catch (e) {
      console.error("Chart init failed:", e);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
