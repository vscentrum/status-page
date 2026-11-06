# Status page design principles

## Purpose and status

This document describes the intended design of the status page application. It
is primarily a contract for maintainers and coding agents: use it when planning,
implementing, or reviewing changes.

These principles are normative goals, not a claim that every part of the
current implementation already conforms. When existing code conflicts with
them, do not silently copy the conflict into new code. Keep changes within the
requested scope, preserve compatibility where necessary, and record or repair
the discrepancy when that is part of the task.

The words **MUST**, **SHOULD**, and **MAY** indicate requirement strength.

## Why the application is designed this way

The status page is a small static-site generator operated by people who need to
publish accurate incident information quickly. Its operational data and site
identity change more often than its rendering algorithms. Its visual design may
also evolve independently of incident parsing and time-based selection.

The design therefore aims to make common changes declarative and local:

- operators should be able to change site-specific behavior without editing
  Python;
- designers should be able to change markup and styling without changing
  parsing or incident-selection logic;
- maintainers should have one authoritative definition of each concept;
- generated pages should be deterministic, reviewable, and safe to publish;
- mistakes should be detected before a partially valid site is deployed.

This separation reduces synchronization errors, makes reviews smaller, and
allows configuration, presentation, and application behavior to be tested at
their natural boundaries.

## Sources of truth

Every piece of information MUST have one authoritative owner.

| Concern | Authoritative owner | Examples |
| --- | --- | --- |
| Deployment and site policy | Configuration | services, aliases, display names, allowed impact levels, input/output locations, overview columns |
| Visual and document presentation | Templates and stylesheets | page structure, navigation markup, tables, badges, headings, CSS classes and colors |
| Incident data | Incident files | title, affected services, impact level, dates, planned status, description |
| Behavior and validation | Application code | parsing, validation, normalization, time-based selection, sorting, view-model construction |
| Published output | Generator | files under the publication directory; never hand-maintained copies |

A value MUST NOT be repeated in multiple owners with comments instructing
maintainers to keep the copies synchronized. If two layers need the same value,
the authoritative layer supplies it to the other layer.

## Configuration is the deployment contract

Configuration MUST be the source of truth for behavior and content that can
legitimately vary between deployments or installations.

In particular:

- adding, removing, reordering, or renaming a service SHOULD require only a
  configuration change;
- configured services MUST drive page generation, labels, navigation, and
  incident validation consistently;
- impact-level identifiers and user-facing descriptions MUST have one
  authoritative definition; templates and CSS MAY style their semantic
  identifiers;
- aliases, accepted values, overview columns, resource files, and empty-state
  messages MUST be honored everywhere they apply;
- locale, timezone, and user-visible formatting policy SHOULD be configurable
  when they are deployment-specific;
- configuration paths SHOULD have explicit, documented resolution semantics,
  preferably relative to the configuration file rather than the caller's
  working directory.

Configuration values SHOULD describe semantics and content, not contain HTML or
CSS. For example, configuration should provide an empty-state message as text,
while a template decides whether it belongs in a paragraph.

Every supported option MUST be consumed by the application, validated before
rendering, documented, and covered by a focused test. A setting that is ignored
is worse than a missing setting because it creates false confidence.

Configuration is not intended to turn every implementation detail into a
switch. Stable algorithms and invariants belong in code. Add an option when a
real deployment or operational need is expected, not merely to avoid writing a
small amount of code.

## Presentation is separate from behavior

Python code MUST NOT be the primary author of HTML presentation. It should
prepare semantic data and pass that data to templates.

Templates and stylesheets own:

- HTML elements and document structure;
- navigation, links, tables, incident cards, legends, and empty states;
- accessibility attributes and relationships;
- CSS classes, layout, typography, color, and responsive behavior;
- user-facing presentation labels that are not deployment configuration.

Application code owns:

- parsing and validating configuration and incident files;
- converting input into a stable internal model;
- selecting current and planned incidents;
- deterministic sorting and grouping;
- constructing URLs or route identifiers as semantic values;
- invoking the template engine and writing output files.

Code SHOULD pass values such as `href`, `level`, `title`, and structured rows to
templates. It SHOULD NOT construct `<a>`, `<span>`, `<table>`, or other HTML
fragments. Templates SHOULD escape interpolated text by default. Any trusted
HTML, including rendered Markdown, MUST cross an explicit and documented trust
boundary.

Shared page elements such as headers, footers, metadata, and service navigation
SHOULD use template inheritance, includes, macros, or another reusable template
mechanism. Copying them between page templates creates avoidable drift.

## Semantic model before rendering

Parsing, domain decisions, and presentation MUST remain distinct stages:

1. Read and validate configuration.
2. Parse and validate incident files.
3. Normalize values into a semantic incident model.
4. Select, sort, and group incidents using an injected reference time.
5. Build template-facing view models.
6. Render templates and copy declared resources.

Templates MUST NOT decide whether an incident is current or planned. Parsers
MUST NOT emit presentation markup. Rendering helpers MUST NOT silently repair
invalid domain data.

Open-ended dates SHOULD remain explicitly open-ended in the semantic model.
They SHOULD NOT be represented by a magic future date, because a sentinel can
leak into sorting, display, and time comparisons.

## Deterministic and fail-closed generation

Given the same configuration, incident files, reference time, templates, and
source metadata, generation SHOULD produce equivalent output.

Therefore:

- ordering MUST be explicit and stable;
- identifiers and URLs MUST be stable across unrelated incident additions;
- the current time MUST be injectable for tests;
- timezone handling MUST be explicit and consistent;
- generated timestamps SHOULD be isolated so meaningful output can be compared;
- invalid configuration or incidents MUST fail verification before publication;
- the publisher MUST NOT deploy a site produced from a partially accepted input
  set unless that degraded behavior is explicitly designed and visible.

## Stable public interface

Published page names, incident anchors, and externally shared links form a
public interface. Changes to their derivation require migration consideration.

Configuration refactors MUST preserve existing URLs unless a deliberate
migration is approved. Renaming an internal label must not accidentally rename
an incident anchor or service page. Generated output directories may be
replaced during publication, but manually maintained files such as deployment
metadata MUST be handled explicitly.

## Accessibility and minimal client complexity

The generated site SHOULD remain usable without client-side JavaScript. Native
HTML semantics are preferred over custom interactive behavior.

Templates MUST preserve keyboard navigation, meaningful heading order, table
headers, link purpose, alternative text, adequate contrast, and responsive
layouts. Accessibility is part of presentation correctness and SHOULD be
covered by rendered-output checks where practical.

## Verification expectations

Tests SHOULD protect the boundaries described above rather than only checking
that the renderer exits successfully.

At minimum, the test suite should demonstrate that:

- adding a service in configuration creates its page and adds it to all
  appropriate navigation;
- removing or renaming a service cannot leave stale links or labels;
- aliases and configurable separators affect parsing as documented;
- configured overview columns and empty states render correctly;
- every configured impact level has a usable presentation hook;
- templates can change page markup without requiring Python changes;
- generated internal links, resources, and identifiers resolve;
- invalid configuration and invalid incidents prevent publication;
- two equivalent renders differ only in explicitly volatile metadata.

Push and pull-request workflows SHOULD run these tests when configuration,
application code, templates, styles, dependencies, or tests change. Scheduled
renders MAY use a cheaper path when their purpose is only to advance
time-dependent status, provided the same revision was already qualified by the
full checks.

## Guidance for changes and reviews

Before completing a change, check the following:

- Is each new concept defined in exactly one authoritative place?
- Could an operator make the expected deployment-specific change through
  configuration alone?
- Does configuration contain semantics rather than markup?
- Does Python return structured data rather than HTML fragments?
- Is shared presentation implemented once?
- Are configuration options actually wired through and validated?
- Are time, ordering, path resolution, and output deterministic?
- Do invalid inputs stop publication?
- Are existing public URLs and anchors preserved?
- Do focused tests prove the intended layer boundary?

When a requested change exposes an existing violation, agents SHOULD call it
out explicitly. They SHOULD prefer a small repair that moves the implementation
toward these principles, but MUST NOT expand a narrowly scoped task into an
unrequested redesign.
