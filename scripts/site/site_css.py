# -*- coding: utf-8 -*-
"""Design system tokens and styles for StellaSora story knowledge base."""

CSS = """
:root {
  --font-sans: "MiSans", "MiSansLatin", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  
  --bg: #EEF2F6;
  --bg-gradient: 
    linear-gradient(118deg, 
      transparent 0%, 
      transparent 35%, 
      rgba(255, 255, 255, 0.35) 35%, 
      rgba(255, 255, 255, 0.35) 48%, 
      transparent 48%, 
      transparent 70%, 
      rgba(255, 255, 255, 0.22) 70%, 
      rgba(255, 255, 255, 0.22) 82%, 
      transparent 82%
    ),
    radial-gradient(ellipse 70% 500px at 10% -40px, rgba(186, 230, 253, 0.35) 0%, transparent 70%),
    radial-gradient(ellipse 65% 540px at 90% -50px, rgba(233, 213, 255, 0.30) 0%, transparent 70%),
    linear-gradient(135deg, #F8FAFC 0%, #EEF2F6 45%, #E2E8F0 85%, #E5EBF2 100%);
  --surface: #FFFFFF;
  --text-main: #0F172A;
  --text-muted: #475569;
  --text-subtle: #64748B;
  
  --card-bg: #FFFFFF;
  --card-bg-subtle: #F8FAFC;
  --card-border: rgba(30, 58, 138, 0.09);
  --card-border-subtle: rgba(30, 58, 138, 0.05);
  --card-border-hover: rgba(30, 58, 138, 0.22);
  --card-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
  --card-shadow-hover: 0 8px 24px rgba(15, 23, 42, 0.08);
  
  --line-highlight: rgba(30, 58, 138, 0.03);
  --accent: #2563EB;
  
  --story: #0D9488;
  --battle: #E11D48;
  --final: #7C3AED;
  --between: #D97706;
  --locked: #94A3B8;
  
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
}

[data-theme="dark"] {
  --bg: #0A0E17;
  --bg-gradient: 
    linear-gradient(118deg, 
      transparent 0%, 
      transparent 35%, 
      rgba(255, 255, 255, 0.02) 35%, 
      rgba(255, 255, 255, 0.02) 48%, 
      transparent 48%, 
      transparent 70%, 
      rgba(255, 255, 255, 0.015) 70%, 
      rgba(255, 255, 255, 0.015) 82%, 
      transparent 82%
    ),
    radial-gradient(ellipse 70% 500px at 10% -40px, rgba(14, 116, 144, 0.16) 0%, transparent 70%),
    radial-gradient(ellipse 65% 540px at 90% -50px, rgba(109, 40, 217, 0.14) 0%, transparent 70%),
    linear-gradient(135deg, #0A0E17 0%, #0F1522 50%, #090D15 100%);
  --surface: #121824;
  --text-main: #F1F5F9;
  --text-muted: #94A3B8;
  --text-subtle: #64748B;
  
  --card-bg: #121824;
  --card-bg-subtle: #172030;
  --card-border: rgba(255, 255, 255, 0.08);
  --card-border-subtle: rgba(255, 255, 255, 0.04);
  --card-border-hover: rgba(255, 255, 255, 0.22);
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  --card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.45);
  
  --line-highlight: rgba(255, 255, 255, 0.04);
  --accent: #60A5FA;
  
  --story: #14B8A6;
  --battle: #FB7185;
  --final: #A78BFA;
  --between: #FBBF24;
  --locked: #64748B;
}

* { box-sizing: border-box; }
html {
  font-family: var(--font-sans);
  background-color: var(--bg);
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
  background: rgba(255, 255, 255, 0.90);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--card-border-subtle);
}
.top::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, rgba(236, 72, 153, 0.45) 0%, rgba(168, 85, 247, 0.40) 28%, rgba(59, 130, 246, 0.40) 55%, rgba(6, 182, 212, 0.45) 80%, rgba(16, 185, 129, 0.40) 100%);
  z-index: 51;
}
[data-theme="dark"] .top {
  background: rgba(18, 24, 36, 0.90);
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
.brand-icon {
  width: 22px;
  height: 28px;
  object-fit: contain;
  flex-shrink: 0;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.15));
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.brand:hover .brand-icon {
  transform: scale(1.08) rotate(-4deg);
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
.hero-badge-wrap {
  margin: -14px 0 22px;
}
.hero-update-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 12px;
  font-size: 12.5px;
  color: var(--text-muted);
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  border-radius: 999px;
  text-decoration: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  transition: all 0.2s ease;
}
.hero-update-pill:hover {
  color: var(--text-main);
  border-color: var(--card-border-hover);
  background: var(--card-bg-subtle);
  transform: translateY(-1px);
}
.hero-update-pill .pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--story);
}
.hero-update-pill .pill-date {
  font-weight: 600;
  color: var(--text-main);
}
.hero-update-pill .pill-sep {
  opacity: 0.4;
}
.hero-update-pill .pill-arrow {
  color: var(--story);
  font-weight: 700;
}

/* Hero Notice Banner (Spoiler & Scope) */
.hero-notice-banner {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 0 20px;
  max-width: 680px;
}
.notice-pill {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 14px;
  font-size: 13px;
  line-height: 1.55;
  border-radius: var(--radius-md);
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.notice-pill.notice-spoiler {
  background: rgba(245, 158, 11, 0.06);
  border-color: rgba(245, 158, 11, 0.25);
}
.notice-pill.notice-scope {
  background: rgba(20, 184, 166, 0.06);
  border-color: rgba(20, 184, 166, 0.22);
}
.notice-tag {
  display: inline-block;
  flex-shrink: 0;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
  letter-spacing: 0.02em;
}
.tag-spoiler {
  background: rgba(245, 158, 11, 0.16);
  color: #D97706;
}
[data-theme="dark"] .tag-spoiler {
  background: rgba(245, 158, 11, 0.25);
  color: #FBBF24;
}
.tag-scope {
  background: rgba(20, 184, 166, 0.16);
  color: #0D9488;
}
[data-theme="dark"] .tag-scope {
  background: rgba(20, 184, 166, 0.25);
  color: #2DD4BF;
}
.notice-msg {
  color: var(--text-muted);
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
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.2s ease,
              box-shadow 0.2s ease;
  box-shadow: var(--card-shadow);
}
.bento-card:hover {
  transform: translateY(-2px);
  border-color: var(--card-border-hover);
  box-shadow: var(--card-shadow-hover);
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

/* Update Section (最近更新板块) */
.update-section {
  max-width: 1100px;
  margin: 10px auto 36px;
}
.update-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  border-radius: var(--radius-lg);
  padding: 22px 26px;
  position: relative;
  box-shadow: var(--card-shadow);
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.update-card:hover {
  border-color: var(--card-border-hover);
  box-shadow: var(--card-shadow-hover);
}
.update-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--card-border-subtle);
}
.update-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}
.update-icon {
  color: var(--story);
}
.update-date-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--story);
  background: rgba(13, 148, 136, 0.08);
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid rgba(13, 148, 136, 0.2);
}
.update-date-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--story);
}
.update-summary {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 12px;
}
.update-list {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.65;
}
.update-list li strong {
  color: var(--text-main);
}
@media (max-width: 640px) {
  .update-card {
    padding: 18px 18px;
  }
  .update-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
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
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
  line-height: 1.65;
  transition: all 0.15s ease;
}
.page .line:last-child {
  margin-bottom: 0;
}
.page .line:hover {
  background: var(--card-bg-subtle);
  border-color: var(--card-border-hover);
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
  scroll-margin-top: 80px;
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
  transition: all 0.15s ease;
}
.options li.has-jump {
  padding: 0;
  cursor: pointer;
}
.options li:hover {
  border-color: var(--card-border-hover);
}
.options li.has-jump:hover {
  border-color: rgba(13, 148, 136, 0.45);
  box-shadow: 0 2px 10px rgba(13, 148, 136, 0.08);
}
.opt-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 8px 14px;
  text-decoration: none;
  color: inherit;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}
.opt-link:hover {
  background: var(--line-highlight);
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
.opt-jump-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(13, 148, 136, 0.08);
  color: var(--story);
  border: 1px solid rgba(13, 148, 136, 0.22);
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.opt-jump-badge.is-merge {
  background: rgba(100, 116, 139, 0.08);
  color: var(--text-subtle);
  border-color: rgba(100, 116, 139, 0.2);
}
.options li.has-jump:hover .opt-jump-badge {
  background: var(--story);
  color: #FFFFFF;
  border-color: var(--story);
  transform: translateY(1px);
}
.options li.has-jump:hover .opt-jump-badge.is-merge {
  background: var(--text-subtle);
  color: #FFFFFF;
  border-color: var(--text-subtle);
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
  margin-right: 8px;
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
  scroll-margin-top: 80px;
  transition: background-color 0.3s ease;
}
.merge {
  margin: 14px 0 6px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text-subtle);
  background: var(--card-bg-subtle);
  border-radius: var(--radius-sm);
  text-align: center;
  scroll-margin-top: 80px;
  transition: background-color 0.3s ease;
}

/* Branch End Navigation (Return to Choice / Jump to Merge) */
.branch-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0 16px;
  padding: 4px 0 6px 4px;
  flex-wrap: wrap;
}
.branch-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 13px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 18px;
  text-decoration: none;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  color: var(--text-muted);
  box-shadow: var(--card-shadow);
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}
.branch-nav-btn svg {
  flex-shrink: 0;
  transition: transform 0.18s ease;
}
.branch-nav-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}
.branch-nav-btn.to-choice:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.branch-nav-btn.to-choice:hover svg {
  transform: translateY(-2px);
}
.branch-nav-btn.to-merge:hover {
  border-color: var(--story);
  color: var(--story);
}
.branch-nav-btn.to-merge:hover svg {
  transform: translateY(2px);
}

/* Target Arrival Highlight Animation */
:target,
.target-flash {
  animation: target-flash 1.6s ease-out;
}
@keyframes target-flash {
  0% {
    background-color: rgba(37, 99, 235, 0.16);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.20);
  }
  100% {
    background-color: transparent;
    box-shadow: none;
  }
}

[data-theme="dark"] .branch-nav-btn {
  background: var(--card-bg-subtle);
  border-color: var(--card-border);
  color: var(--text-muted);
}
[data-theme="dark"] .branch-nav-btn:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
[data-theme="dark"] .opt-jump-badge {
  background: rgba(20, 184, 166, 0.15);
  border-color: rgba(20, 184, 166, 0.3);
  color: var(--story);
}
[data-theme="dark"] .opt-jump-badge.is-merge {
  background: rgba(148, 163, 184, 0.12);
  border-color: rgba(148, 163, 184, 0.25);
  color: var(--text-muted);
}

/* Player Response (玩家回应) matches Image 2 & 3: speaker "魔王 选择了" above text */
.player-reply {
  padding: 12px 18px;
  margin: 0 0 8px 0;
  background: var(--card-bg);
  border: 1px solid var(--card-border-subtle);
  border-radius: var(--radius-sm);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
  display: flex;
  flex-direction: column;
  transition: all 0.15s ease;
}
.player-reply:last-child {
  margin-bottom: 0;
}
.player-reply:hover {
  background: var(--card-bg-subtle);
  border-color: var(--card-border-hover);
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
.foot-brand { font-weight: 600; color: var(--text-muted); display: inline-flex; align-items: center; }
.foot-icon {
  width: 16px;
  height: 20px;
  object-fit: contain;
  vertical-align: -4px;
  margin-right: 6px;
  opacity: 0.9;
}
.foot-disclaimer {
  max-width: 1100px;
  margin: 14px auto 0;
  padding-top: 12px;
  border-top: 1px dashed var(--card-border-subtle);
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-subtle);
  opacity: 0.85;
}
.foot-disclaimer p {
  margin: 0;
}
.foot-disclaimer .foot-font {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.8;
}

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
