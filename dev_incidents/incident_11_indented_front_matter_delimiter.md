---
title: |
  Markdown front matter containing
  ---
  an indented delimiter-like line
start_date: 2022-01-20 09:00:00
end_date: 2022-01-20 11:00:00
affected: tier2_leuven
level: low
planned: no
---

**Note: this is a parser robustness test.**

The indented `---` is part of the YAML block scalar and is not the closing
front matter delimiter.
