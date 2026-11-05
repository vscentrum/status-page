import datetime
from html.parser import HTMLParser
import pathlib
import re
import subprocess
import sys
from urllib.parse import urlsplit

import pytest
import yaml


PROJECT_ROOT = pathlib.Path(__file__).parents[1]
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
PRODUCTION_CONFIG = PROJECT_ROOT / 'config' / 'config.yml'
# Render before the earliest production incident so every incident is visible as
# planned maintenance and exercises the complete HTML generation path.
RENDER_TIME = datetime.datetime(2000, 1, 1, 0, 0, 0)
sys.path.insert(0, str(SCRIPTS_DIR))

from config_reader import read_config  # noqa: E402
from incident_parser import IncidentParser  # noqa: E402
import utils  # noqa: E402


class HtmlInventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.incident_ids = []
        self.references = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get('id')
        if element_id:
            self.ids.append(element_id)
        if (
            tag == 'article'
            and 'incident' in attributes.get('class', '').split()
            and element_id
        ):
            self.incident_ids.append(element_id)
        for attribute in ('href', 'src'):
            if attributes.get(attribute):
                self.references.append(attributes[attribute])


def make_parser(config):
    return IncidentParser(
        meta_data_fields=config['meta_data_fields'],
        affected=config['affected'],
        level=config['level'],
        affected_aliases=config['affected_aliases'],
        is_permissive=False,
    )


def write_render_config(path, build_dir):
    with PRODUCTION_CONFIG.open(encoding='utf-8') as stream:
        config = yaml.safe_load(stream)

    config['incident_dirs'] = [
        str(PROJECT_ROOT / incident_dir)
        for incident_dir in config['incident_dirs']
    ]
    config['template_dir'] = str(PROJECT_ROOT / config['template_dir'])
    config['build_dir'] = str(build_dir)
    path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding='utf-8',
    )


def render_site(config_path, warnings_as_errors=False):
    command = [sys.executable]
    if warnings_as_errors:
        command.extend(['-W', 'error::DeprecationWarning'])
    command.extend(
        [
            str(SCRIPTS_DIR / 'render_site.py'),
            '--now',
            RENDER_TIME.isoformat(sep=' '),
            '--config',
            str(config_path),
        ]
    )
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def parse_html(path):
    inventory = HtmlInventory()
    inventory.feed(path.read_text(encoding='utf-8'))
    return inventory


def normalized_file_content(path):
    content = path.read_bytes()
    if path.suffix != '.html':
        return content
    text = content.decode('utf-8')
    text = re.sub(
        r'<p class="generated-at">.*?</p>',
        '<p class="generated-at">NORMALIZED</p>',
        text,
    )
    return text.encode('utf-8')


@pytest.fixture(scope='module')
def production_data():
    config = read_config(PRODUCTION_CONFIG)
    parser = make_parser(config)

    assert all(
        parser.parse(PROJECT_ROOT / incident_dir)
        for incident_dir in config['incident_dirs']
    )

    return config, parser.incidents


@pytest.fixture(scope='module')
def rendered_sites(tmp_path_factory):
    root = tmp_path_factory.mktemp('production-render')
    build_dirs = []
    for run_number in (1, 2):
        build_dir = root / f'build-{run_number}'
        config_path = root / f'config-{run_number}.yml'
        write_render_config(config_path, build_dir)
        render_site(config_path)
        build_dirs.append(build_dir)

    return tuple(build_dirs)


def test_runtime_is_python_314():
    assert sys.version_info[:2] == (3, 14)


def test_production_verifier_entry_point_succeeds():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / 'verify_incidents.py')],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == ''
    assert result.stderr == ''


def test_every_production_incident_is_parsed_once_per_service(production_data):
    config, incidents = production_data
    source_files = {
        path
        for incident_dir in config['incident_dirs']
        for path in (PROJECT_ROOT / incident_dir).iterdir()
        if path.is_file() and not path.name.startswith('.')
    }
    expected_ids = {f'incident_{path.stem}' for path in source_files}

    assert {path.suffix for path in source_files} <= {'.md', '.yml', '.yaml'}
    assert len(expected_ids) == len(source_files)
    assert set(incidents['id']) == expected_ids
    assert not incidents.duplicated(['affected', 'id']).any()


def test_production_incidents_are_render_safe(production_data):
    _, incidents = production_data

    assert incidents['title'].map(
        lambda title: isinstance(title, str) and bool(title.strip())
    ).all()
    assert incidents['content'].map(
        lambda content: isinstance(content, str) and bool(content.strip())
    ).all()
    assert incidents['start_date'].map(
        lambda value: value.tzinfo is None
    ).all()
    assert incidents['end_date'].dropna().map(
        lambda value: value.tzinfo is None
    ).all()


def test_rendered_site_contains_all_expected_files(rendered_sites, production_data):
    build_dir, _ = rendered_sites
    config, _ = production_data
    expected_files = {
        'index.html',
        'style.css',
        'images/favicon.png',
        'images/vsc_logo.png',
        *(f'{service}.html' for service in config['affected']),
    }
    actual_files = {
        str(path.relative_to(build_dir))
        for path in build_dir.rglob('*')
        if path.is_file()
    }

    assert expected_files <= actual_files


def test_rendered_incidents_match_current_production_state(
    rendered_sites,
    production_data,
):
    build_dir, _ = rendered_sites
    config, incidents = production_data
    current = utils.select_current_incidents(
        incidents.copy(),
        date=RENDER_TIME,
    )
    planned = utils.select_planned_maintenance(
        incidents.copy(),
        date=RENDER_TIME,
    )
    assert current.empty
    assert len(planned) == len(incidents)
    visible = [current, planned]

    for service in config['affected']:
        expected_ids = {
            row.id
            for data_frame in visible
            for row in data_frame[data_frame.affected == service].itertuples()
        }
        inventory = parse_html(build_dir / f'{service}.html')
        assert set(inventory.incident_ids) == expected_ids

    expected_overview_links = {
        f'{row.affected}.html#{row.id}'
        for data_frame in visible
        for row in data_frame.itertuples()
    }
    overview = parse_html(build_dir / 'index.html')
    actual_overview_links = {
        reference
        for reference in overview.references
        if '#incident_' in reference
    }
    assert actual_overview_links == expected_overview_links


def test_rendered_html_has_unique_ids_and_resolvable_references(rendered_sites):
    build_dir, _ = rendered_sites
    html_files = sorted(build_dir.glob('*.html'))
    inventories = {path: parse_html(path) for path in html_files}

    for path, inventory in inventories.items():
        assert len(inventory.ids) == len(set(inventory.ids)), path.name
        for reference in inventory.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                continue
            target = path.parent / (parsed.path or path.name)
            assert target.is_file(), f'{path.name}: missing {reference}'
            if parsed.fragment and target.suffix == '.html':
                assert parsed.fragment in inventories[target].ids, (
                    f'{path.name}: unresolved fragment {reference}'
                )


def test_production_render_is_deterministic(rendered_sites):
    first, second = rendered_sites
    first_files = {
        path.relative_to(first)
        for path in first.rglob('*')
        if path.is_file()
    }
    second_files = {
        path.relative_to(second)
        for path in second.rglob('*')
        if path.is_file()
    }

    assert first_files == second_files
    for relative_path in first_files:
        assert normalized_file_content(first / relative_path) == (
            normalized_file_content(second / relative_path)
        ), str(relative_path)


@pytest.mark.xfail(
    strict=True,
    reason='pandas 3.1 deprecates DataFrame.sort_values(inplace=True)',
)
def test_production_render_has_no_deprecation_warnings(tmp_path):
    build_dir = tmp_path / 'build'
    config_path = tmp_path / 'config.yml'
    write_render_config(config_path, build_dir)

    render_site(config_path, warnings_as_errors=True)
