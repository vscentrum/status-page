---
title: Markdown incident with affected services as a YAML sequence
start_date: 2022-01-20 09:00:00
end_date: 2022-01-20 11:00:00
affected:
  - tier2_leuven
  - tier1_compute
level: low
planned: no
---

**Note: this is a parser robustness test.**

The metadata is valid YAML, but the shared validator passes the sequence to
`re.split` instead of reporting a controlled field-type validation error.
