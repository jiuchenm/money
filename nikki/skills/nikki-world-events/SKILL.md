---
name: nikki-world-events
description: Build Nikki daily market-relevant world-event timeline from primary sources, preserving occurrence time, publication time, affected assets, and verification status.
---

# Nikki World Events

Search four independent lanes every day: macro/geopolitics, China/Hong Kong, AI/technology/industry, and metric/accounting scrutiny. Prefer central banks, governments, exchanges, regulators, company filings, and direct company disclosures. Use high-quality media to verify private-company information and market reaction. Aggregator headlines are discovery leads only.

Timeliness means a new fact, new verification, new dispute about measurement, or new price reaction was published within 72 hours. The underlying story may be older. Reject duplicated stories and sources without a clear quality basis. Never claim that no major event occurred merely because one feed failed; report coverage failures by lane.

Write for a Chinese investor focused on Hong Kong and A shares. For each event return `chinese_summary`, `occurred_at`, `published_at`, `source_name`, `source_url`, `affected_assets`, `hk_a_impact`, `mechanism`, `priced_in`, `event_kind`, `metric_caveat`, and `evidence_status`. Use `fact`, `metric_methodology`, or `market_reaction` for `event_kind`. Explain in plain Chinese what happened, what expectation changed, the transmission path into Hong Kong/A shares, and whether price may already reflect it. For ARR, revenue run rate, adjusted profit, bookings, backlog, GMV, or annualized figures, compare the headline metric with realized-period revenue, cash flow, and accounting scope. Keep the original foreign-language title only as evidence metadata. Use verified, partial, or unverified. Return at most eight events. Never turn headline direction directly into price direction.

Return one JSON object with an `events` array. Every item must preserve `original_title` and `url` exactly as supplied so the publisher can merge the interpretation back into the collected event. Add `priced_in` to distinguish a new catalyst from an event already reflected in price. Do not return prose outside JSON.
