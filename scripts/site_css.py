# -*- coding: utf-8 -*-
"""Design system tokens and styles for StellaSora story knowledge base."""

CSS = """
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  
  --bg: #FAFAF9;
  --bg-gradient: radial-gradient(circle at 50% 0%, #FFFFFF 0%, #F5F5F4 100%);
  --surface: #FFFFFF;
  --text-main: #1C1917;
  --text-muted: #57534E;
  --text-subtle: #858079;
  
  --card-bg: #FFFFFF;
  --card-bg-subtle: #F5F5F4;
  --card-border: rgba(0, 0, 0, 0.08);
  --card-border-subtle: rgba(0, 0, 0, 0.04);
  --card-border-hover: rgba(0, 0, 0, 0.22);
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  --card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.06);
  
  --line-highlight: rgba(0, 0, 0, 0.025);
  --accent: #2563EB;
  
  --story: #0D9488;
  --battle: #E11D48;
  --final: #7C3AED;
  --between: #D97706;
  --locked: #A8A29E;
  
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
}

[data-theme="dark"] {
  --bg: #0C0A09;
  --bg-gradient: radial-gradient(circle at 50% 0%, #1C1917 0%, #0C0A09 100%);
  --surface: #141211;
  --text-main: #F5F5F4;
  --text-muted: #A8A29E;
  --text-subtle: #78716C;
  
  --card-bg: #141211;
  --card-bg-subtle: #1C1917;
  --card-border: rgba(255, 255, 255, 0.09);
  --card-border-subtle: rgba(255, 255, 255, 0.04);
  --card-border-hover: rgba(255, 255, 255, 0.25);
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  --card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.4);
  
  --line-highlight: rgba(255, 255, 255, 0.04);
  --accent: #60A5FA;
  
  --story: #14B8A6;
  --battle: #FB7185;
  --final: #A78BFA;
  --between: #FBBF24;
  --locked: #78716C;
}

* { box-sizing: border-box; }
html {
  font-family: var(--font-sans);
  background: var(--bg);
  background-image: var(--bg-gradient);
  background-attachment: fixed;
  color: var(--text-main);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  min-height: 100%;
}
body {
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Header & Navigation */
.top {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(250, 250, 249, 0.82);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--card-border-subtle);
}
[data-theme="dark"] .top {
  background: rgba(12, 10, 9, 0.82);
}
.top-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text-main);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav {
  display: flex;
  align-items: center;
  gap: 16px;
  overflow-x: auto;
  white-space: nowrap;
  font-size: 13.5px;
}
.nav a {
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.15s ease;
  font-weight: 500;
}
.nav a:hover, .nav a.on {
  color: var(--text-main);
}
.theme-toggle {
  background: transparent;
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  padding: 6px;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.theme-toggle:hover {
  border-color: var(--card-border-hover);
  color: var(--text-main);
}
[data-theme="dark"] .sun-icon { display: block; }
[data-theme="dark"] .moon-icon { display: none; }
[data-theme="light"] .sun-icon { display: none; }
[data-theme="light"] .moon-icon { display: block; }

/* Main Container & Breadcrumbs */
.wrap {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 20px 60px;
}
.crumb {
  font-size: 12.5px;
  color: var(--text-subtle);
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.crumb a {
  color: var(--text-muted);
  text-decoration: none;
}
.crumb a:hover {
  color: var(--text-main);
  text-decoration: underline;
}
h1 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.lede {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 24px;
  line-height: 1.6;
}

/* Bento Grid */
.bento {
  list-style: none;
  padding: 0;
  margin: 0 0 32px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  position: relative;
}
.bento-item { position: relative; }
.span-1 { grid-column: span 1; }
.span-2 { grid-column: span 2; }
.span-4 { grid-column: span 4; }
@media (max-width: 860px) {
  .bento { grid-template-columns: repeat(2, 1fr); }
  .span-1, .span-2 { grid-column: span 1; }
  .span-4 { grid-column: span 2; }
}
@media (max-width: 540px) {
  .bento { grid-template-columns: 1fr; }
  .span-1, .span-2, .span-4 { grid-column: span 1; }
}

.bento-card {
  position: relative;
  height: 100%;
  min-height: 175px;
  padding: 24px 26px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--card-shadow);
  anchor-name: --a;
}
.bento-card:hover {
  border-color: var(--card-border-hover);
}
.bento-card-link {
  position: absolute;
  inset: 0;
  z-index: 2;
  border: 0 !important;
}
.bento-top {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.bento-num {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-subtle);
  letter-spacing: 0.06em;
  opacity: 0.65;
}
.bento-body {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}
.bento-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 8px;
  line-height: 1.3;
}
.bento-desc {
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.55;
  margin: 0 0 16px;
}
.bento-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  color: var(--text-subtle);
  padding-top: 12px;
  border-top: 1px solid var(--card-border-subtle);
}
.bento-count { font-weight: 500; }
.bento-arrow {
  font-size: 15px;
  transition: transform 0.2s ease;
}
.bento-card:hover .bento-arrow {
  transform: translateX(4px);
  color: var(--text-main);
}

/* CSS Anchor Positioning Magnetic Indicator */
.bento-indicator {
  display: none;
}
@supports (anchor-name: --a) {
  .bento-indicator {
    display: block;
    position: absolute;
    position-anchor: --a;
    inset: anchor(inside);
    pointer-events: none;
    border-radius: var(--radius-xl);
    border: 1px solid var(--card-border-hover);
    box-shadow: var(--card-shadow-hover);
    opacity: 0;
    transition: inset 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                opacity 0.2s ease;
    z-index: 1;
  }
  .bento:hover .bento-indicator { opacity: 1; }
}
.bento-indicator.js-fallback {
  display: block;
  position: absolute;
  pointer-events: none;
  border-radius: var(--radius-xl);
  border: 1px solid var(--card-border-hover);
  box-shadow: var(--card-shadow-hover);
  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 1;
  opacity: 0;
}

/* Search Box */
.searchbox {
  margin: 0 0 24px;
  position: relative;
}
.search-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 14px;
  color: var(--text-subtle);
  pointer-events: none;
}
.searchbox input {
  width: 100%;
  padding: 12px 14px 12px 40px;
  font-size: 14px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  color: var(--text-main);
  outline: none;
  transition: all 0.15s ease;
}
.searchbox input:focus {
  border-color: var(--card-border-hover);
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.04);
}
[data-theme="dark"] .searchbox input:focus {
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.05);
}

.results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 6px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--card-shadow-hover);
  z-index: 40;
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
}
.results-header {
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-subtle);
  border-bottom: 1px solid var(--card-border-subtle);
}
.hits { list-style: none; padding: 0; margin: 6px 0; }
.hit-link {
  display: block;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--text-main);
  transition: background 0.1s ease;
}
.hit-link:hover {
  background: var(--card-bg-subtle);
}
.hit-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.hit-title { font-size: 14px; font-weight: 600; }
.hit-group { font-size: 11.5px; color: var(--text-subtle); }
.hit-speakers { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

/* Chapter List & Group Section */
.chaplist {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.chapcard {
  display: block;
  padding: 20px 22px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: var(--text-main);
  transition: all 0.2s ease;
  position: relative;
}
.chapcard:hover {
  border-color: var(--card-border-hover);
  transform: translateY(-2px);
  box-shadow: var(--card-shadow-hover);
}
.chap-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.chapno { font-size: 12.5px; font-weight: 600; color: var(--text-subtle); }
.chapyear { font-size: 12px; color: var(--text-subtle); }
.chaptitle { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.chapinfo { font-size: 12.5px; color: var(--text-muted); }
.chap-arrow {
  position: absolute;
  right: 20px;
  bottom: 20px;
  font-size: 15px;
  color: var(--text-subtle);
  transition: transform 0.2s ease;
}
.chapcard:hover .chap-arrow {
  transform: translateX(4px);
  color: var(--text-main);
}

.grp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.grp {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
}
.grp-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--card-border-subtle);
}
.grp-head-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}
.grp-title { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.35; color: var(--text-main); }
.grp-count { font-size: 12px; color: var(--text-subtle); font-family: var(--font-mono); flex-shrink: 0; }
.grp-topo-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  color: var(--story);
  text-decoration: none;
  transition: all 0.15s ease;
}
.grp-topo-btn:hover {
  border-color: var(--story);
  background: var(--card-bg);
  transform: translateX(2px);
}
.badge.battle {
  display: inline-block;
  font-style: normal;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(225, 29, 72, 0.12);
  color: var(--battle);
  vertical-align: 1px;
  margin-right: 4px;
}
.plain { list-style: none; padding: 0; margin: 0; }
.plain-link {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 7px 8px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--text-main);
  font-size: 13.5px;
  transition: background 0.1s ease;
}
.plain-link:hover {
  background: var(--card-bg-subtle);
}
.plain-link .sub {
  font-size: 12px;
  color: var(--text-subtle);
  font-family: var(--font-mono);
}

/* Node Map (chapter_graph_page) */
.chapsel {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 14px 0 10px;
}
.chapsel a {
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
}
.chapsel a:hover {
  border-color: var(--card-border-hover);
  color: var(--text-main);
}
.chapsel a.on {
  background: var(--text-main);
  color: var(--bg);
  border-color: var(--text-main);
  font-weight: 700;
}
.anchors-wrap {
  overflow-x: auto;
  margin-bottom: 14px;
}
.anchors {
  display: flex;
  gap: 4px;
}
.anchors a {
  padding: 3px 8px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-subtle);
  border: 1px solid var(--card-border);
  border-radius: 4px;
  background: var(--card-bg);
  text-decoration: none;
}
.anchors a:hover {
  border-color: var(--card-border-hover);
  color: var(--text-main);
}
.map {
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid var(--card-border);
  border-radius: var(--radius-xl);
  background: var(--card-bg);
  user-select: none;
  cursor: grab;
}
.map:active {
  cursor: grabbing;
}
.canvas { position: relative; }
.wires { position: absolute; left: 0; top: 0; pointer-events: none; z-index: 1; }
.edge {
  fill: none;
  stroke: var(--card-border);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.edge.story { stroke: var(--story); }
.edge.battle { stroke: var(--battle); }
.edge.final, .edge.memory { stroke: var(--final); }
.edge.between { stroke: var(--between); }
.edge.locked { stroke: var(--locked); }
.edge.dash { stroke-dasharray: 5 4; }

.node {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-left-width: 3px;
  border-radius: var(--radius-md);
  border-bottom: 0 !important;
  color: var(--text-main);
  text-decoration: none;
  transition: border-color 0.15s ease;
  overflow: hidden;
  z-index: 2;
}
.node:hover {
  border-color: var(--card-border-hover);
  z-index: 5;
}
.node.story { border-left-color: var(--story); }
.node.battle { border-left-color: var(--battle); }
.node.between { border-left-color: var(--between); }
.node.final, .node.memory { border-left-color: var(--final); }
.node.locked { border-left-color: var(--locked); border-style: dashed; color: var(--text-muted); }

.node .code {
  font-family: var(--font-mono);
  font-size: 13.5px;
  font-weight: 700;
  line-height: 1.2;
}
.node .t {
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 3px 0;
}
.node .chip {
  font-size: 10px;
  color: var(--text-subtle);
  background: var(--card-bg-subtle);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--card-border);
  align-self: flex-start;
}
.node .state {
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-subtle);
}
.node:hover .state {
  color: var(--text-main);
}
.map-note {
  margin-top: 12px;
}

/* ========================================================= */
/* Special Chapter (linelist) Grid Cards                     */
/* ========================================================= */
.linelist {
  list-style: none;
  padding: 0;
  margin: 20px 0 36px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.linelist li {
  list-style: none;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  background: var(--card-bg);
  border: 1px dashed var(--card-border);
  border-left: 3px dashed var(--locked);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  box-sizing: border-box;
}
.linelist li:has(a) {
  padding: 0;
  border: none;
  background: transparent;
}
.linelist li a {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 16px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-left: 3px solid var(--story);
  border-radius: var(--radius-md);
  color: var(--text-main);
  text-decoration: none;
  box-sizing: border-box;
  transition: all 0.15s ease;
}
.linelist li a:hover {
  border-color: var(--card-border-hover);
  background: var(--bg-hover);
  transform: translateY(-1px);
}
.linelist li:last-child a {
  border-left-color: var(--final);
}
.linelist .code {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  background: var(--bg-hover);
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}
.linelist li:not(:has(a)) .code {
  color: var(--text-subtle);
  background: var(--card-bg-subtle);
}
.linelist .t {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.linelist li:not(:has(a)) .t {
  color: var(--text-muted);
}
.linelist .chip {
  font-size: 11px;
  color: var(--text-subtle);
  background: var(--card-bg-subtle);
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid var(--card-border);
  white-space: nowrap;
  flex-shrink: 0;
}
.linelist .s {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-subtle);
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}
.linelist li a .s {
  color: var(--text-muted);
}
.linelist li a .s::after {
  content: ' ›';
  font-size: 13px;
  margin-left: 2px;
  color: var(--text-subtle);
  transition: all 0.15s ease;
}
.linelist li a:hover .s {
  color: var(--text-main);
}
.linelist li a:hover .s::after {
  color: var(--text-main);
  transform: translateX(2px);
}
@media (max-width: 580px) {
  .linelist {
    grid-template-columns: 1fr;
  }
}

/* ========================================================= */
/* Script Page Reading & Typography Overhaul                 */
/* ========================================================= */
.page {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-xl);
  padding: 32px 36px;
  margin: 18px 0;
}
@media (max-width: 640px) {
  .page { padding: 20px 16px; }
}

/* Section Headings in Script Page */
.page h2 {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-main);
  margin: 28px 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--card-border-subtle);
  display: flex;
  align-items: center;
  gap: 8px;
}
.page h2::before {
  content: attr(data-part);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

/* Stage Information Key-Values */
.page p.meta {
  display: flex;
  align-items: baseline;
  margin: 6px 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-main);
}
.page p.meta b {
  min-width: 82px;
  color: var(--text-muted);
  font-weight: 500;
  flex-shrink: 0;
}
.page p.meta b::after {
  content: "：";
}
.page p.meta code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  border-radius: 4px;
  padding: 1px 6px;
  color: var(--text-main);
}

/* Skip Recap / Official Blockquote */
.page blockquote {
  margin: 14px 0 22px;
  padding: 14px 20px;
  background: var(--card-bg-subtle);
  border-left: 3px solid var(--story);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--text-main);
  font-size: 13.5px;
  line-height: 1.75;
}
.page blockquote p {
  margin: 4px 0;
}

/* In-Game Record Backlog Board (游戏内「紀錄」牌板) */
.backlog-board {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  margin: 20px 0;
  position: relative;
}
.backlog-header {
  background: #00b4b6;
  color: #ffffff;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
  font-size: 13.5px;
  letter-spacing: 0.05em;
  user-select: none;
}
[data-theme="dark"] .backlog-header {
  background: #0f766e;
}
.backlog-title {
  display: flex;
  align-items: center;
  gap: 7px;
}
.backlog-pin {
  display: inline-block;
  vertical-align: middle;
}
.backlog-close {
  font-size: 15px;
  opacity: 0.85;
}
.backlog-body {
  position: relative;
  padding: 12px 14px;
  background: #f1f5f9;
}
[data-theme="dark"] .backlog-body {
  background: #0d131f;
}
.backlog-body::after {
  content: '';
  position: absolute;
  top: 14px;
  bottom: 14px;
  right: 6px;
  width: 3px;
  background: #00b4b6;
  border-radius: 2px;
  opacity: 0.7;
  pointer-events: none;
}
[data-theme="dark"] .backlog-body::after {
  background: #14b8a6;
}

/* Dialogue Lines: Backlog Item Card */
.page .line {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 12px 18px;
  margin: 0 0 8px 0;
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  line-height: 1.65;
  transition: all 0.15s ease;
}
.page .line:last-child {
  margin-bottom: 0;
}
.page .line:hover {
  background: var(--card-bg-subtle);
  border-color: var(--card-border);
}
.page .line .who {
  font-size: 13.5px;
  font-weight: 700;
  color: #4a6b82;
  margin-bottom: 4px;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
[data-theme="dark"] .page .line .who {
  color: #93c5fd;
}
.page .line .who::after {
  display: none;
}
.page .line .say {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-main);
}
.page .line .tag {
  font-style: normal;
  font-size: 10.5px;
  font-weight: 500;
  color: var(--text-muted);
  border: 1px solid var(--card-border);
  background: var(--card-bg-subtle);
  border-radius: 3px;
  padding: 0 4px;
  vertical-align: 1px;
}
.page .line.thought .who {
  color: var(--text-muted);
}
.page .line.chat .who, .page .line.bubble .who {
  color: var(--story);
}
.page .line.sticker .say {
  color: var(--text-muted);
}
.page .line .play-btn {
  display: none !important;
}

/* Narration (旁白) matches Image 1: no speaker label, clean paragraph spacing */
.page .line.narrator {
  padding: 14px 18px;
  margin: 0 0 8px 0;
}
.page .line.narrator .who {
  display: none;
}
.page .line.narrator .play-btn {
  display: none !important;
}
.page .line.narrator .say {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text-main);
}

/* Scene Markers */
.scene {
  margin: 24px 0 14px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  text-align: center;
}
.wave {
  margin: 20px 0 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--battle);
  border-left: 3px solid var(--battle);
  font-weight: 700;
}

/* Dialogue Choices & Major Choices */
.choice {
  margin: 18px 0 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  border-left: 3px solid var(--card-border-hover);
  padding-left: 10px;
}
.choice.major-choice {
  font-size: 14px;
  font-weight: 700;
  color: var(--between);
  border-left-color: var(--between);
}
.options {
  list-style: none;
  padding: 0;
  margin: 8px 0 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.options li {
  padding: 8px 14px;
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  font-size: 13.5px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  transition: border-color 0.15s ease;
}
.options li:hover {
  border-color: var(--card-border-hover);
}
.options b {
  color: var(--text-main);
  font-weight: 600;
}
.major-options li {
  border-left: 3px solid var(--between);
}
.major-options b {
  color: var(--between);
  font-weight: 700;
}
.opt-main {
  flex: 1;
  min-width: 200px;
}
.opt-target {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  text-decoration: none;
  font-size: 12px;
  color: var(--text-main);
  transition: all 0.15s ease;
}
.opt-target:hover {
  border-color: var(--between);
  color: var(--between);
  transform: translateX(2px);
}
.opt-target span {
  color: var(--text-subtle);
  font-size: 11px;
}

/* Branch Sections */
.branch-open {
  margin: 14px 0 6px;
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--story);
  border-left: 3px solid var(--story);
  background: var(--card-bg-subtle);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.merge {
  margin: 14px 0 6px;
  padding: 5px 10px;
  font-size: 11.5px;
  color: var(--text-subtle);
  background: var(--card-bg-subtle);
  border-radius: var(--radius-sm);
  text-align: center;
}

/* Player Response (玩家回应) matches Image 2 & 3: speaker "魔王 选择了" above text */
.player-reply {
  padding: 12px 18px;
  margin: 0 0 8px 0;
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  transition: all 0.15s ease;
}
.player-reply:last-child {
  margin-bottom: 0;
}
.player-reply:hover {
  background: var(--card-bg-subtle);
  border-color: var(--card-border);
}
.player-reply .reply-who {
  font-size: 13.5px;
  font-weight: 700;
  color: #4a6b82;
  margin-bottom: 4px;
}
[data-theme="dark"] .player-reply .reply-who {
  color: #93c5fd;
}
.player-reply .reply-body p {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-main);
}
.player-reply .reply-body b {
  color: var(--text-main);
  font-weight: 600;
}

/* Cast Facets Dropdown */
.cast {
  margin-top: 18px;
  font-size: 13px;
}
.cast summary {
  cursor: pointer;
  color: var(--text-muted);
  font-weight: 600;
  user-select: none;
}
.facets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.facet {
  font-size: 12px;
  padding: 3px 8px;
  background: var(--card-bg-subtle);
  border: 1px solid var(--card-border);
  border-radius: 4px;
  color: var(--text-muted);
  text-decoration: none;
}
.facet:hover {
  border-color: var(--card-border-hover);
  color: var(--text-main);
}

/* Story Flow Prev / Next Navigation */
.story-nav {
  margin: 24px 0 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 600px) {
  .story-nav { grid-template-columns: 1fr; }
}
.story-nav-prev, .story-nav-next, .story-nav-branches {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.15s ease;
}
.story-nav-prev:hover, .story-nav-next:hover, .story-nav-branches:hover {
  border-color: var(--card-border-hover);
  box-shadow: var(--card-shadow-hover);
}
.nav-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-subtle);
  letter-spacing: 0.04em;
}
.nav-link {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-main);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nav-link:hover {
  color: var(--accent);
}
.nav-link b {
  font-family: var(--font-mono);
}
.story-nav-branches {
  grid-column: span 1;
}
.branch-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}
.branch-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 700;
}
.branch-tag.story { background: rgba(13, 148, 136, 0.12); color: var(--story); }
.branch-tag.final { background: rgba(124, 58, 237, 0.12); color: var(--final); }
.branch-tag.battle { background: rgba(225, 29, 72, 0.12); color: var(--battle); }

/* Footer */
.foot {
  margin-top: auto;
  border-top: 1px solid var(--card-border-subtle);
  background: var(--card-bg);
  padding: 24px 20px;
  font-size: 12.5px;
  color: var(--text-subtle);
}
.foot-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.foot-brand { font-weight: 600; color: var(--text-muted); }

/* Back to Top */
.back-to-top {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  opacity: 0;
  pointer-events: none;
  transition: all 0.2s ease;
  z-index: 40;
}
.back-to-top.visible {
  opacity: 1;
  pointer-events: auto;
}
.back-to-top:hover {
  border-color: var(--card-border-hover);
  color: var(--text-main);
  transform: translateY(-2px);
}
"""
