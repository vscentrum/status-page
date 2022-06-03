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

Two workflows have been defined:
1. a workflow triggered by a push to the main branch, and
1. a workflow that is executed every 30 minutes.

Both workflows render the site into the `docs` directory.  This
directory is exposed by Github Pages and will be linked to
https://status.vscentrum.be/

To create an incident:
1. do a git pull of the main branch;
1. add your incident description as a YAML file in the `incidents`
   directory;
1. commit your change and push;

You will find some example incidents in the
[example_incidents/](`example_incidents`) directory.

The push event triggers rendering the website.

The script that runs every 30 minutes will ensure that an incident with
and end date will no longer show up when that date is reached.

## Development

The `config/dev_config.yml` configuration file is intended for development
and testing.  The render script takes an options `--now` that can be used
to set the "current time".  The example incidents in the `example_incidents`
directory can be used with `--now '2022-01-20 10:00:00'`, e.g,.
```bash
$ ./scripts/render_site.py  --now '2022-01-20 10:00:00'  --config config/dev_config.yml
```
Note that one of those example incidents contains an error on purpose.
