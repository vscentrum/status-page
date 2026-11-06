# Design conformance review

## Review metadata

- Review date: 2026-11-06
- Reviewed commit: `07940ea361`
- Scope: configuration ownership, separation of presentation from code, and
  the safeguards that preserve those boundaries
- Method: read-only inspection of configuration, application code, templates,
  stylesheets, workflow configuration, tracked files, and generated output
- CodeGraph: not used because the repository had no `.codegraph/` directory

This report assesses the implementation against the principles in
[DESIGN.md](DESIGN.md). It records the state of the reviewed commit; it is not a
design proposal or evidence that later commits have the same properties.

## Executive summary

The intended architecture remains visible, but both principal goals are only
partially met.

- Configuration controls most operational inputs, but it is not the sole
  source of truth for services and impact levels. Some apparent options are
  also ignored or have undocumented constraints.
- CSS and most page structure are external to Python, which is a sound base.
  However, the renderer still creates important HTML fragments and table
  markup in code.
- The production configuration and templates are synchronized at the reviewed
  commit, so these issues do not by themselves establish a current visible-site
  failure. They make future configuration and presentation changes unreliable.
- No tracked automated test suite currently enforces the intended boundaries.

The overall verdict is **partial conformance**. The repository has not become a
fully code-defined site, but configuration and presentation cannot yet be
changed independently with confidence.

## Findings

### F1. Services have competing sources of truth

**Importance: high for configurability**

Services, aliases, and display names are declared in
[`config/config.yml`](../config/config.yml#L31-L55). Page generation correctly
iterates over configured services in
[`scripts/render_site.py`](../scripts/render_site.py#L94-L97).

Navigation does not use that data. The same service identifiers and labels are
written manually in both
[`templates/index.html`](../templates/index.html#L62-L78) and
[`templates/service_tmpl.html`](../templates/service_tmpl.html#L37-L54). Both
templates contain a comment telling maintainers to keep the navigation labels
synchronized with configuration.

Consequences:

- adding a service can generate a page that users cannot reach through site
  navigation;
- removing a service can leave a broken navigation link;
- reordering or renaming a configured service does not update navigation;
- production and development configuration must be kept synchronized with two
  additional copies in presentation files.

This directly conflicts with the rule that configuration is authoritative for
deployment-specific services and that values should not be duplicated with a
manual synchronization instruction.

### F2. Impact-level semantics and presentation can drift

**Importance: high for configurability and user interpretation**

The accepted level identifiers are declared in
[`config/config.yml`](../config/config.yml#L56-L59), and incident validation
uses that list. The descriptions of those levels are hard-coded separately in
[`templates/index.html`](../templates/index.html#L40-L59), while their visual
treatment is hard-coded by identifier in
[`templates/style.css`](../templates/style.css#L211-L240).

A newly configured level can therefore pass validation and render with a
generated CSS class, but it will have no legend entry and no level-specific
style. Removing or renaming a level can leave stale explanatory text and CSS.

The semantic identifiers may reasonably map to CSS hooks, but the set of
levels and their user-facing meaning need one authoritative definition. A
template should render the configured set rather than repeat it.

### F3. Python still owns significant HTML presentation

**Importance: medium**

Most page structure and all CSS are externalized, and no inline styles were
found in the templates. However,
[`scripts/utils.py`](../scripts/utils.py#L7-L9) stores an HTML link as a table
heading, and the same module constructs:

- impact-level `<span>` elements
  ([lines 33-34](../scripts/utils.py#L33-L34));
- incident-title `<a>` elements
  ([lines 36-41](../scripts/utils.py#L36-L41));
- complete overview tables through `DataFrame.to_html(escape=False)`
  ([lines 51-68](../scripts/utils.py#L51-L68)).

It also chooses the user-facing values `planned` and `unplanned` while preparing
incident output ([lines 70-83](../scripts/utils.py#L70-L83)).

Consequences:

- changing overview markup, link structure, accessibility attributes, or CSS
  classes requires Python changes;
- templates cannot control the markup of individual overview rows or cells;
- data preparation and presentation cannot be tested independently;
- `escape=False` makes the boundary between trusted generated markup and
  untrusted incident values difficult to reason about.

Markdown conversion is legitimately an application concern, but the resulting
trusted-HTML boundary should be explicit and confined to the template-facing
model.

### F4. Presentation also leaks into configuration

**Importance: low to medium**

The two empty-state messages in
[`config/config.yml`](../config/config.yml#L5-L6) contain `<p>` elements. This
keeps the markup out of Python but still places presentation in a semantic
configuration file.

It also requires configuration authors to understand HTML and makes the values
less reusable for other output formats or contexts. Configuration should
normally supply plain text, with templates deciding how to wrap it.

### F5. Some configuration options are ineffective or narrower than they look

**Importance: medium**

The configuration exposes several values that are not dependable as general
configuration controls:

1. `sep` is declared in
   [`config/config.yml`](../config/config.yml#L60), and `IncidentParser`
   supports a separator argument
   ([`scripts/incident_parser.py`](../scripts/incident_parser.py#L93-L106)).
   Neither the renderer nor the verifier passes the configured value when
   constructing the parser
   ([`render_site.py`](../scripts/render_site.py#L69-L75),
   [`verify_incidents.py`](../scripts/verify_incidents.py#L21-L28)). Changing
   the configuration therefore has no effect.
2. The overview column lists appear freely configurable, but the HTML helper
   always reads and sorts by `end_date`
   ([`scripts/utils.py`](../scripts/utils.py#L51-L66)). Removing that column
   from an overview would fail even though the configuration shape permits it.
3. `meta_data_fields` is configurable, but validation and rendering directly
   assume fields such as `affected`, `start_date`, `end_date`, and `planned`.
   Their required status is an application invariant, not a genuinely dynamic
   schema.
4. The incident and service template filenames are configurable, while the
   overview template and its output name are fixed as `index.html`
   ([`scripts/render_site.py`](../scripts/render_site.py#L15-L23)).
5. [`scripts/config_reader.py`](../scripts/config_reader.py#L5-L15) converts
   path-looking values to `Path` objects but does not resolve them relative to
   the configuration file or validate the complete configuration. Successful
   path resolution consequently depends on the caller's working directory.

Sixteen of the seventeen top-level keys in `config/config.yml` are referenced
by application code; `sep` is the unused key. Reference alone is not sufficient
for options whose valid combinations and required invariants are not checked.

### F6. Shared presentation is duplicated across templates

**Importance: medium for maintenance**

The overview and service templates duplicate document metadata, branding,
header content, footer content, generated-at output, and the complete service
navigation. The current use of `str.format` in
[`scripts/utils.py`](../scripts/utils.py#L87-L94) offers no inheritance,
includes, macros, or loops.

This duplication has already forced explicit synchronization comments. It also
makes global presentation changes larger and easier to apply inconsistently.
A template mechanism supporting shared layouts and iteration would preserve the
presentation boundary while eliminating those copies.

### F7. The design boundaries have no tracked regression tests

**Importance: high for preserving the design**

At the reviewed commit:

- `git ls-files 'tests/**' 'requirements-dev.txt'` returned no paths;
- only ignored Python bytecode remained under the local `tests/` directory;
- the workflow installs runtime requirements, verifies incident files, and
  renders the site, but does not run a test suite
  ([`.github/workflows/render_site.yml`](../.github/workflows/render_site.yml#L47-L57)).

Rendering successfully with the current configuration cannot detect whether a
configuration option is ignored or whether repeated service and level lists
have drifted. These require focused mutation-style tests using synthetic
configuration.

## Areas that conform well

The review also found useful foundations that should be retained:

- Configuration already controls incident directories, template and build
  locations, resource copying, overview columns, allowed services and levels,
  aliases, display names, and the open-ended-date display string.
- The renderer uses configured services to determine which service pages to
  create.
- Page shells and detailed incident markup live in template files rather than
  large Python string literals.
- Styling is concentrated in `templates/style.css`, with no inline style
  attributes found in application code or templates.
- Incident descriptions are authored as content and converted from Markdown;
  they are not embedded in Python.
- Resource copying is driven by the configured resource list.
- Incident files, application behavior, templates, and generated publication
  output occupy distinct repository directories.

These choices make incremental alignment practical; a wholesale rewrite is not
required merely to restore the intended boundaries.

## Recommended remediation sequence

### Priority 1: restore authoritative configuration

1. Represent services as ordered structured records containing at least their
   stable identifier and display name. Add any navigation grouping as semantic
   data only if the site needs it.
2. Represent impact levels as structured records with a stable identifier and
   user-facing explanation. Keep visual styling in CSS.
3. Render navigation and the impact legend by iterating over those structures.
4. Wire `sep` through both application entry points, or remove it from public
   configuration if it is not intended to vary.
5. Validate required keys, types, identifiers, uniqueness, references, and
   incompatible combinations before parsing incidents.

### Priority 2: restore the presentation boundary

1. Introduce a template mechanism that supports iteration and reusable
   layouts. Jinja or an equivalent engine would provide the required
   facilities; the engine choice should be made explicitly rather than by
   moving more HTML into Python.
2. Pass structured table rows and incident view models to templates.
3. Move overview links, badges, headers, and table markup out of `utils.py`.
4. Make auto-escaping the default and mark only the reviewed Markdown output as
   trusted HTML.
5. Replace configured HTML empty states with semantic text and template-owned
   markup.

### Priority 3: protect the contract

Add focused tests proving that:

- a synthetic configured service appears in generated navigation and receives
  a page;
- removing or renaming a service leaves no stale links or labels;
- every configured impact level appears in the legend and receives a semantic
  styling hook;
- changing `sep` changes parser behavior;
- supported overview-column combinations render, while invalid ones fail with
  a clear configuration error;
- templates can change markup without corresponding Python edits;
- all generated internal links and resources resolve;
- invalid configuration prevents rendering and publication.

Run the full suite on relevant pushes and pull requests. Scheduled rendering
may continue to use a cheaper path if the same source revision was already
qualified and schedule cost is a concern.

### Priority 4: clarify remaining policy

Document and enforce:

- path resolution relative to the configuration file or repository root;
- which metadata fields are invariant and which are extensible;
- timezone and display-format ownership;
- the trusted-content policy for incident Markdown;
- stable service-page and incident-anchor compatibility guarantees.

## Suggested acceptance criteria for alignment

The implementation can be considered aligned with the reviewed design goals
when all of the following are true:

- service and level sets occur in one authoritative data source;
- changing those sets through configuration updates every relevant generated
  page without editing Python or HTML templates;
- Python rendering modules contain no page-level HTML fragments;
- configuration contains no presentation markup;
- shared site chrome and navigation have one template implementation;
- every documented configuration option is consumed and validated;
- automated tests exercise configuration variation rather than only the
  production configuration;
- the publication workflow fails before deployment on invalid configuration,
  invalid incidents, or failed conformance tests.

## Verification performed and limitations

The following static checks informed this report:

- repository file and tracked-file inventory;
- clean-worktree check before documentation was added;
- direct inspection of both configuration files, all Python modules involved in
  reading, verification, selection, and rendering, all templates, relevant CSS,
  the rendering workflow, and the README;
- searches for configuration-key consumers, hard-coded service and level
  values, HTML fragments in Python, inline styling, and tracked tests;
- comparison of production and development configuration.

Dependency-backed verification was attempted but not completed:

- `python scripts/verify_incidents.py --config config/config.yml` failed because
  the `python` pyenv shim had no selected interpreter;
- the available Python 3.10 and Python 3.14 environments lacked PyYAML.

No dependency installation was authorized or performed. Therefore, this report
does not claim that the verifier, renderer, or hosted workflow passed at the
reviewed commit. The findings concern directly observable source structure and
wiring; no application files were changed during the review.
