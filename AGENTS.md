# Developer and agent guidance

## Scope

This file applies to the entire repository. It is intended for both human
developers and coding agents.

Follow the user's requested scope and any higher-priority instructions first.
Within that scope, preserve unrelated work and prefer the smallest change that
fully solves the problem.

## Required design context

Before changing configuration, parsing, rendering, templates, styles, site
generation, or publication behavior, read
[`dev-docs/DESIGN.md`](dev-docs/DESIGN.md) in full. It is the normative design
contract for this project.

The central rules are:

- configuration is the source of truth for deployment-specific semantics;
- templates and stylesheets own HTML presentation;
- application code owns parsing, validation, domain behavior, and rendering
  orchestration;
- each concept has one authoritative definition;
- generation is deterministic and fails closed on invalid input;
- published URLs and anchors are stable interfaces.

Do not add a second source of truth or a comment telling maintainers to keep
copies synchronized. Do not construct page-level HTML in Python when structured
data can be passed to a template.

[`dev-docs/DESIGN_REVIEW.md`](dev-docs/DESIGN_REVIEW.md) is an evidence-backed
assessment of a particular repository revision. Use it to understand known
design gaps, but do not treat it as the normative specification or assume that
all findings still apply without checking the current checkout.

## Repository and change discipline

- Inspect the current branch, worktree status, relevant source, configuration,
  templates, and tests before editing.
- Preserve unrelated modified or untracked files. Never discard user work to
  make a task easier.
- Keep changes focused. Avoid opportunistic rewrites, broad formatting, or
  dependency churn unless they are required by the task.
- When an existing design violation is encountered, do not reproduce it in new
  code. Repair it when that is in scope; otherwise report it clearly.
- Treat `docs/` as generated publication output. Change source configuration,
  templates, styles, incidents, or generator code instead of hand-editing
  generated pages. Handle intentionally preserved deployment files such as
  `docs/CNAME` explicitly.
- Do not silently change service-page names, incident anchors, or other public
  links. Plan migrations when compatibility cannot be preserved.
- Avoid adding a dependency when the standard library or an existing
  dependency solves the problem clearly. Document the rationale for any new
  runtime dependency.

If a `.codegraph/` directory exists at the repository root, use CodeGraph before
text search when locating symbols or understanding call paths. If it is absent,
continue with normal repository search; creating an index is a separate user
decision.

## Coding practices

- Write small, cohesive functions with explicit inputs and outputs.
- Keep parsing, validation, domain selection, view-model construction, and
  rendering as separate stages.
- Validate data at boundaries and produce actionable errors that identify the
  relevant file, field, and invalid value.
- Prefer explicit invariants over magic values. In particular, represent an
  open-ended date as open-ended rather than as a distant sentinel date.
- Make time, timezone, ordering, and path-resolution behavior explicit and
  testable. Inject the reference time instead of depending on the wall clock in
  tests.
- Use stable deterministic ordering whenever filesystem, mapping, or dataframe
  iteration could affect generated output.
- Avoid broad exception handling that converts programming errors into partial
  output. Invalid configuration or incidents must prevent publication.
- Keep configuration semantic. Do not place HTML or CSS in configuration when a
  template or stylesheet can own it.
- Pass structured values such as titles, URLs, levels, and rows to templates.
  Do not assemble `<a>`, `<span>`, `<table>`, or similar markup in Python.
- Escape template values by default. Treat rendered Markdown or other trusted
  HTML as an explicit, documented trust boundary.
- Preserve accessibility: meaningful headings, table headers, keyboard access,
  link purpose, alternative text, contrast, and responsive behavior are part
  of correctness.
- Use clear names and comments that explain intent or constraints. Do not add
  comments that merely restate the code.
- Keep source and documentation lines readable and avoid trailing whitespace.

## Testing expectations

Every behavior change or bug fix must have testing proportional to its risk.
The absence of an existing test harness on a branch is not a reason to skip
tests; add the smallest appropriate harness or explain the concrete blocker.

### Unit tests

Unit tests should exercise one behavior with minimal external state. They
should cover, as applicable:

- configuration parsing and validation;
- incident-field validation and normalization;
- aliases, separators, dates, and invalid input types;
- current-versus-planned selection at boundary times;
- deterministic ordering and stable identifiers;
- semantic view-model construction.

Prefer table-driven or parametrized tests for related input cases. Include
normal, boundary, and invalid cases. A bug fix should normally begin with a
focused regression test that fails for the reported reason.

Unit tests must not depend on the network, the real wall clock, filesystem
iteration order, or mutable global state. Use temporary directories and an
injected time where filesystem or time behavior is part of the unit.

### Integration tests

Integration tests should exercise meaningful boundaries between components,
including:

- loading a complete configuration and incident corpus;
- verifying incidents through the supported entry point;
- rendering a complete site into a temporary build directory;
- adding, removing, renaming, or reordering a configured service and checking
  generated pages and navigation;
- checking that every configured impact level is represented correctly;
- resolving generated internal links and copied resources;
- confirming that invalid configuration or incidents stop generation;
- comparing repeated renders while normalizing only explicitly volatile
  metadata.

Use a fixed reference time for rendering tests. Do not write integration-test
output into `docs/` or overwrite a developer's existing build artifacts.

### Test organization and CI

- Keep automated tests under `tests/` and name them by the behavior or boundary
  they protect.
- Use `pytest` for new Python tests unless the project deliberately adopts a
  different documented test runner.
- Separate runtime and development dependencies so production rendering does
  not install test-only packages unnecessarily.
- Keep local commands and CI commands aligned. A check that only works in one
  environment is not reliable evidence.
- Run the full relevant suite on pushes and pull requests that change source,
  configuration, templates, styles, dependencies, or tests.
- Scheduled time-driven renders may skip expensive tests if the same revision
  was already qualified, but they must still validate inputs before publishing.

## Verification before completion

Run the narrowest checks first, then broader checks in proportion to the
change. A typical sequence is:

1. syntax, formatting, and whitespace checks;
2. focused unit tests for the changed behavior;
3. the relevant integration or rendered-output tests;
4. the complete local test suite;
5. production incident verification;
6. a fixed-time site render to a disposable or ignored build directory.

Use the repository's selected Python environment and locked or documented
dependency setup when one is available. Do not install packages into an
unrelated global environment merely to make a check pass.

If a command cannot run because an interpreter, dependency, service, or network
resource is unavailable, report the exact command and failure. Distinguish
static inspection from dependency-backed tests, and local tests from hosted CI
or live-site verification.

## Documentation practices

- Update user documentation when inputs, commands, incident formats, or
  operational behavior change.
- Update `dev-docs/DESIGN.md` only when the intended design principles change,
  not to excuse an implementation that violates them.
- Keep design rationale with the rule it explains so future maintainers can
  assess tradeoffs rather than cargo-cult a constraint.
- Do not silently rewrite `dev-docs/DESIGN_REVIEW.md` as the implementation
  evolves; it identifies its reviewed revision. Create a clearly dated follow-up
  review or an explicitly scoped status update when requested.
- Examples must be valid, safe to copy, and covered by tests when practical.

## Completion checklist

Before handing off a change, confirm that:

- the requested behavior is implemented and no unrelated files were changed;
- the design contract was followed or any necessary exception is documented;
- configuration remains authoritative and presentation remains outside Python;
- invalid inputs fail clearly and cannot produce a partial publication;
- unit and integration coverage protects the change;
- generated links, resources, identifiers, and accessibility semantics remain
  valid;
- exact verification commands, results, skips, and remaining unverified scope
  are reported.
