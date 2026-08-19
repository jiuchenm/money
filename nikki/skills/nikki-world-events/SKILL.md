---
name: nikki-world-events
description: Build Nikki daily market-relevant world-event timeline from primary sources, preserving occurrence time, publication time, affected assets, and verification status.
---

# Nikki World Events

Prefer central banks, governments, exchanges, regulators, EIA, OPEC, and company filings. Aggregator headlines are discovery leads only. Reject events older than 72 hours, duplicated stories, and sources without a clear quality basis. If no timely evidence survives, return an empty event list and state that old news cannot explain today's market.

Write for a Chinese investor focused on Hong Kong and A shares. For each event return `chinese_summary`, `occurred_at`, `published_at`, `source_name`, `source_url`, `affected_assets`, `hk_a_impact`, `mechanism`, and `evidence_status`. Explain in plain Chinese what happened, what expectation changed, the transmission path into Hong Kong/A shares, and whether price may already reflect it. Keep the original foreign-language title only as evidence metadata. Use verified, partial, or unverified. Return at most eight events. Never turn headline direction directly into price direction.

Return one JSON object with an `events` array. Every item must preserve `original_title` and `url` exactly as supplied so the publisher can merge the interpretation back into the collected event. Add `priced_in` to distinguish a new catalyst from an event already reflected in price. Do not return prose outside JSON.
