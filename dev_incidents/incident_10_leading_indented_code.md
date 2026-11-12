---
title: Markdown incident starting with an indented code block
start_date: 2022-01-20 09:00:00
end_date: 2022-01-20 11:00:00
affected: tier2_leuven
level: low
planned: no
---
    first line should remain indented
    second line should remain indented

The two lines above should render as one Markdown code block.  The current
reader strips the indentation from the first line.
