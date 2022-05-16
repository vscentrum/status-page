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
