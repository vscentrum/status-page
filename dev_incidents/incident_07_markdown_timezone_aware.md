---
title: Markdown incident with timezone-aware timestamps
start_date: 2022-01-20T09:00:00+01:00
end_date: 2022-01-20T11:00:00+01:00
affected: tier2_leuven
level: medium
planned: no
---

**Note: this is a parser robustness test.**

The parser accepts these timezone-aware timestamps, but the renderer compares
them with a timezone-naive current time.
