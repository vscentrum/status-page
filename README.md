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
1. add your incident description as a YAML file in the `incidents`
   directory;
1. commit your change and push;

You will find some example incidents in the
[example_incidents/](`example_incidents`) directory.

The push event triggers rendering the website.

The scheduled run updates the site as incidents start or end, even when
no source files have changed. Scheduled runs can be delayed by GitHub Actions.

## Semantics

Incident level:
1. low: you can expect reduced performance, but functionality is intact.
   For instance, parts of the system are offline for maintenance.
2. medium: performance is reduced, and some functionality may not be
  available.  For instance some node types may not be available, or non-critical
  storage could be impacted.
3. high: functionality is impacted to a large extent.  You may be able to log
  in, but not to launch jobs, and your data may be temporarily inaccessible.

This is a rough indication, the description of the incident should detail its
scope and impact for the user.

Affected:
The domain are fairly self-explanatory (eg. tier1_compute, tier1_data, tier1_cloud, tier2_antwerp, tier2_xxx, backbone) and are define in the config.yml file. 
Note however that a problem with local storage may have impact on other systems.  If the storage system that
hosts the home and data directories of users at an institute is down, these
users will not be able to use infrastructure on other sites either.  You may
want to lists such issues also for the VSC storage domain.

Planned:
Note that the `planned` field is intended for bookkeeping purposes only.  By
construction, an incident is planned when its start date is in the future.
As soon as the start date is in the past, and the end date still in the future,
it is a current event.

Incident naming scheme:
To keep it a bit organised, start the incident filename with the site that reported the incident followed by the date of report and in case of multiple incidents on a day, add an index (eg. kul_20221021_01)

The filename also determines the incident's link anchor on the site (e.g.,
`kul_20221021_01.yml` becomes `#incident_kul_20221021_01`).  Use only letters,
digits, `_` and `-`, and do not rename an incident file once it has been
published, since that breaks existing links to it.

## Development

The `config/dev_config.yml` configuration file is intended for development
and testing.  The render script takes an options `--now` that can be used
to set the "current time".  The example incidents in the `example_incidents`
directory can be used with `--now '2022-01-20 10:00:00'`, e.g,.
```bash
$ ./scripts/render_site.py  --now '2022-01-20 10:00:00'  --config config/dev_config.yml
```
Note that one of those example incidents contains an error on purpose.

