# VSC status page

Repository that drives the VSC status page.

## What is it?

1. `incidents`: directory containing the incidents.
1. `config`: directory containing the configuration file(s) for
   the verifier and the renderer.
1. `scripts`: Python scripts to verify incident files and render the web site.
1. `templates`: (HTML) templates to render the website from.
1. `docs`: directory that contains the actual website, populated
   automatically by the Github CI/CD.
1. `requirements.txt`: Python environment description.
1. `Dockerfile`: docker file that contains all software required to
   to run the scripts.
1. `.github`: CI/CD workflows.
1. `dev_incidents`: some incidents useful for testing during development.
1. `example_incidents`: some example incident files.

## How to use it?

One workflow verifies incidents and renders the site:
1. on pushes to `main` and pull requests that change incidents, configuration,
   scripts, templates, dependencies, or the workflow itself;
1. every 15 minutes, at minutes 13, 28, 43, and 58; and
1. on manual dispatch from the Actions tab.

Verification must succeed before rendering. All runs fetch full Git history
so incident update timestamps reflect the last incident commit, and use the
Europe/Brussels timezone.

Pull requests only verify and render; they never publish. Runs on `main`
compare freshly rendered output with `docs` and only publish and commit when
the content differs. Publication preserves `docs/CNAME`, and runs for the
same Git ref are serialized to prevent overlapping deployments.

The `docs` directory is exposed by Github Pages at
https://status.vscentrum.be/. No Pages configuration change is required.

To create an incident:
1. do a git pull of the main branch;
1. add your incident description as a Markdown (`.md`) or YAML (`.yml`) file
   in the `incidents` directory (see [Incident file formats](#incident-file-formats));
1. commit your change and push;

You will find some example incidents in the
[example_incidents/](`example_incidents`) directory.

The push event triggers rendering the website.

The scheduled run updates the site as incidents start or end, even when
no source files have changed. Scheduled runs can be delayed by GitHub Actions.

### Incident file formats

Two file formats are supported for incidents: Markdown and YAML.

#### Markdown

A Markdown file (`.md`) starts with the metadata as YAML between two `---`
lines, followed by the description of the incident in plain
[Markdown](https://www.markdownguide.org/basic-syntax/), e.g.,
[example_incidents/incident_02.md](example_incidents/incident_02.md):
```markdown
---
title: CalcUA Tier-2 access closed (Markdown test incident)
start_date: 2022-01-20 16:45:00
end_date: 2022-01-22 03:30:00
affected: tier2_antwerp
level: high
planned: no
---

**Note: this is a test incident**

#### [Update 2022-01-22 03:30:00]
Access to the login and portal nodes has been restored.
Running jobs is possible again.

#### [2022-01-20 16:45:00]
Due to a recently disclosed critical vulnerability, *access* to the
CalcUA clusters has been **closed**:

* access to both the login and portal nodes has been disabled;
* no new jobs will be allowed to start until further notice;
* users can still access their data through [Globus](https://www.globus.org/).

Our apologies for the inconvenience.
```
No HTML or YAML quoting is needed for the description.  A few things to keep
in mind:
* a list must be preceded by a blank line;
* a single line break inside a paragraph is ignored, use a blank line to
  start a new paragraph.

#### YAML

An incident can also be written as a YAML file (`.yml`) with the metadata
fields under `meta_data` and the description in a `content` field, see
[example_incidents/incident_01.yml](example_incidents/incident_01.yml).
The `content` field is also rendered as Markdown, but YAML folding rules
apply, which is error-prone.

## Semantics

Incident level:
1. low: you can expect reduced performance, but functionality is intact.
   For instance, parts of the system are offline for maintenance.
2. medium: performance is reduced, and some functionality may not be
  available.  For instance some node types may not be available, or non-critical
  storage could be impacted.
3. high: functionality is impacted to a large extent. You may or may not be
   able to log in, but you will not be able launch jobs, and your data may be
   temporarily inaccessible.

This is a rough indication, the description of the incident should detail its
scope and impact for the user.

Affected:
The domains are fairly self-explanatory (e.g., tier1_compute, tier1_data,
tier1_cloud, tier2_antwerp, tier2_xxx, backbone) and are defined in the
`config/config.yml` file.  On the site, the domains are shown with the names
defined in `affected_display_names` in the config.yml file, e.g.,
`tier2_brussels` is shown as "Tier-2 Brussel".  Some domains also have an
alternative name, defined in `affected_aliases`, that can be used in incident
files, e.g., `tier2_brussel` for `tier2_brussels` and `tier2_antwerpen` for
`tier2_antwerp`.  Note, however, that a problem with local storage may have
impact on other systems.  If the storage system that hosts the home and data
directories of users at an institute is down, these users will not be able to
use infrastructure on other sites either.  You may want to list such issues
also for the VSC storage domain.

Planned:
The `planned` field states whether the incident was scheduled in advance
(`yes`) or is an unexpected issue (`no`), and is shown as the type of the
incident (`planned` or `unplanned`) on the service pages.  It does not
determine in which section an incident is listed: an incident is listed under
planned maintenance when its start date is in the future.  As soon as the start
date is in the past, and the end date still in the future, it is a current
event.

Incident naming scheme:
To keep it a bit organised, start the incident filename with the site that
reported the incident followed by the date of report and in case of multiple
incidents on a day, add an index (e.g., kul_20221021_01).

The filename also determines the incident's link anchor on the site (e.g.,
`kul_20221021_01.md` becomes `#incident_kul_20221021_01`).  Use only letters,
digits, `_` and `-`, and do not rename an incident file once it has been
published, since that breaks existing links to it.

## Development

The `config/dev_config.yml` configuration file is intended for development
and testing; it uses the incidents in the `dev_incidents` directory.  The
render script takes an option `--now` that can be used to set the "current
time".  The dev incidents can be used with `--now '2022-01-20 10:00:00'`, e.g.,
```bash
$ ./scripts/render_site.py  --now '2022-01-20 10:00:00'  --config config/dev_config.yml
```
The dev incidents with `broken` in their file name contain errors on purpose,
to test the verification.  Both the render script and the verify script are
expected to report them.  The render script skips them and renders the other
incidents, while the verify script exits with a non-zero status:
```bash
$ ./scripts/verify_incidents.py  --config config/dev_config.yml
```
The hidden file `.incident_02_broken.yml` should be ignored, so it is
expected not to be reported.

The development corpus also contains targeted parser-robustness examples:

| Example | Intended coverage |
| --- | --- |
| `incident_07_markdown_timezone_aware.md` | A timezone-aware Markdown timestamp accepted by validation but incompatible with the renderer's naive current time. |
| `incident_08_yaml_timezone_aware.yml` | The equivalent shared-validator problem in the YAML format. |
| `incident_09_duplicate_stem.md` and `.yml` | Two formats producing the same incident anchor. |
| `incident_10_leading_indented_code.md` | Markdown-significant leading indentation that must be preserved. |
| `incident_11_indented_front_matter_delimiter.md` | An indented `---` inside a valid YAML block scalar. |
| `incident_12_unsupported_extension.yaml` | Valid incident YAML using the unsupported `.yaml` suffix. |
| `incident_98_markdown_affected_sequence_broken.md` | A metadata sequence that should produce a controlled validation error. |
| `incident_99_yaml_affected_sequence_broken.yml` | The equivalent shared-validator problem in the YAML format. |

The sequence-valued `affected` examples currently raise an uncaught `TypeError`,
so use the verifier's optional path argument to exercise either one in
isolation.  The full development corpus intentionally contains invalid files
and is expected to return a non-zero status; after the parser issues are fixed,
each invalid example should produce a controlled validation error and each
valid example should preserve its intended content.

Install the development dependencies and run the unit tests with:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_incident_parser.py
```

Known parser defects are marked as strict expected failures.  When a defect is
fixed, pytest reports an unexpected pass until the corresponding marker is
removed.

The application-level tests require Python 3.14.  They strictly validate every
production incident, invoke the production verifier, render the complete site
twice at a fixed time, check all incident anchors and local links, and compare
the normalized render outputs for determinism.  Run the complete Python 3.14
acceptance suite with:

```bash
python3.14 -m pip install -r requirements-dev.txt
python3.14 -m pytest
```

