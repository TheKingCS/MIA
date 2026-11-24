---
id: K-0440
kind: implementation
title: Which products are priced below what they take
status: confirmed
by: claude
created: 2026-11-24T17:23:22+00:00
concerns: core/product_pricing.py, core/assistant_business_voice_actions.py
from: dec:DEC-0125
---
core/product_pricing.py (check_my_prices): a piece's materials and hours are the totals of the Complete jobs that produced the product (a job that made several products shared by count) over all the pieces made; at workshop.labor_rate_per_hour that is the least it should sell for. Underpriced named most first with what it would be at his rate; a product no timed job made is said as not worked out; without a rate the materials and minutes a piece takes are said. Margin and overhead are not in it: it is a floor. Live check: picked twice on qwen2.5:14b.
