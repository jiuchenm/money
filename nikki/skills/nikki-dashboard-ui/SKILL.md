---
name: nikki-dashboard-ui
description: Build or review Nikki responsive Docusaurus market dashboard, dated archives, trend views, charts, accessibility, and GitHub Pages behavior.
---

# Nikki Dashboard UI

Keep Nikki as a quiet operational dashboard under /nikki. The latest view prioritizes current signals; /nikki/trends uses stored daily snapshots; /nikki/archive/YYYY-MM-DD preserves immutable evidence.

Use mobile-first CSS Grid. Test 320, 375, 768, and 1440 px plus dark mode and 200% zoom. Do not require hover for meaning. Every chart needs a text value or accessible label, and color must not be the only status signal.

Respect Docusaurus baseUrl, static generation, and GitHub Pages deep links. Prefer lightweight SVG for small series; use Recharts for richer responsive charts and ECharts only when zoom, K-line, heatmap, or large datasets justify it.
