import datetime
import pathlib
import sys

import pytest


PROJECT_ROOT = pathlib.Path(__file__).parents[1]
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
DEV_INCIDENTS_DIR = PROJECT_ROOT / 'dev_incidents'
sys.path.insert(0, str(SCRIPTS_DIR))

from config_reader import read_config  # noqa: E402
from incident_parser import IncidentParser, read_markdown_incident  # noqa: E402
import utils  # noqa: E402


CONFIG = read_config(PROJECT_ROOT / 'config' / 'dev_config.yml')
LAST_UPDATED = '2022-01-20 12:00:00'

VALID_INCIDENTS = {
    'incident_01.yml',
    'incident_03.yml',
    'incident_04.yml',
    'incident_05.md',
}

CONTROLLED_INVALID_INCIDENTS = {
    'incident_02_broken.yml',
    'incident_04_broken',
    'incident_06_broken.md',
    'incident_12_unsupported_extension.yaml',
}

ROBUSTNESS_INCIDENTS = {
    'incident_07_markdown_timezone_aware.md',
    'incident_08_yaml_timezone_aware.yml',
    'incident_09_duplicate_stem.md',
    'incident_09_duplicate_stem.yml',
    'incident_10_leading_indented_code.md',
    'incident_11_indented_front_matter_delimiter.md',
    'incident_98_markdown_affected_sequence_broken.md',
    'incident_99_yaml_affected_sequence_broken.yml',
}


def make_parser():
    return IncidentParser(
        meta_data_fields=CONFIG['meta_data_fields'],
        affected=CONFIG['affected'],
        level=CONFIG['level'],
        affected_aliases=CONFIG['affected_aliases'],
    )


def parse_incident(file_name):
    parser = make_parser()
    parser.parse_file(DEV_INCIDENTS_DIR / file_name, LAST_UPDATED)
    return parser


def test_all_development_incidents_are_classified():
    actual_files = {
        path.name
        for path in DEV_INCIDENTS_DIR.iterdir()
        if path.is_file() and not path.name.startswith('.')
    }
    expected_files = (
        VALID_INCIDENTS
        | CONTROLLED_INVALID_INCIDENTS
        | ROBUSTNESS_INCIDENTS
    )

    assert actual_files == expected_files


@pytest.mark.parametrize(
    ('file_name', 'expected_rows'),
    [
        pytest.param('incident_01.yml', 1, id='yaml-single-service'),
        pytest.param('incident_03.yml', 2, id='yaml-multiple-services'),
        pytest.param('incident_04.yml', 1, id='yaml-open-ended'),
        pytest.param('incident_05.md', 1, id='markdown'),
    ],
)
def test_valid_development_incidents_parse(file_name, expected_rows):
    incidents = parse_incident(file_name).incidents

    assert len(incidents) == expected_rows
    assert incidents['content'].str.len().gt(0).all()


@pytest.mark.parametrize(
    ('file_name', 'message'),
    [
        pytest.param(
            'incident_02_broken.yml',
            'invalid level value intermediate',
            id='invalid-level',
        ),
        pytest.param(
            'incident_04_broken',
            'incident file should have one of the extensions',
            id='missing-extension',
        ),
        pytest.param(
            'incident_06_broken.md',
            "no closing '---' line",
            id='missing-front-matter-delimiter',
        ),
        pytest.param(
            'incident_12_unsupported_extension.yaml',
            'incident file should have one of the extensions',
            id='unsupported-yaml-extension',
        ),
    ],
)
def test_invalid_development_incidents_raise_value_error(file_name, message):
    with pytest.raises(ValueError, match=message):
        parse_incident(file_name)


@pytest.mark.xfail(
    strict=True,
    reason='timezone-aware timestamps are accepted but fail during rendering',
)
@pytest.mark.parametrize(
    'file_name',
    [
        'incident_07_markdown_timezone_aware.md',
        'incident_08_yaml_timezone_aware.yml',
    ],
    ids=['markdown', 'yaml'],
)
def test_timezone_aware_incident_is_rejected_or_renderable(file_name):
    try:
        parser = parse_incident(file_name)
    except ValueError:
        return

    utils.select_current_incidents(
        parser.incidents,
        date=datetime.datetime(2022, 1, 20, 10, 0),
    )


@pytest.mark.xfail(
    strict=True,
    reason='different incident formats can currently create duplicate anchors',
)
def test_duplicate_incident_stems_are_rejected_or_deduplicated():
    parser = make_parser()
    parser.parse_file(
        DEV_INCIDENTS_DIR / 'incident_09_duplicate_stem.md',
        LAST_UPDATED,
    )

    try:
        parser.parse_file(
            DEV_INCIDENTS_DIR / 'incident_09_duplicate_stem.yml',
            LAST_UPDATED,
        )
    except ValueError:
        return

    assert parser.incidents['id'].is_unique


@pytest.mark.xfail(
    strict=True,
    reason='the Markdown reader strips indentation from the first content line',
)
def test_markdown_content_preserves_leading_indentation():
    path = DEV_INCIDENTS_DIR / 'incident_10_leading_indented_code.md'
    with path.open(encoding='utf-8') as stream:
        incident = read_markdown_incident(stream)

    assert incident['content'].startswith(
        '    first line should remain indented\n'
        '    second line should remain indented\n'
    )


@pytest.mark.xfail(
    strict=True,
    reason='an indented delimiter-like scalar line closes front matter early',
)
def test_markdown_front_matter_allows_indented_delimiter_line():
    incidents = parse_incident(
        'incident_11_indented_front_matter_delimiter.md'
    ).incidents

    assert incidents.iloc[0]['title'] == (
        'Markdown front matter containing\n'
        '---\n'
        'an indented delimiter-like line\n'
    )


@pytest.mark.xfail(
    strict=True,
    reason='sequence-valued affected metadata raises TypeError, not ValueError',
)
@pytest.mark.parametrize(
    'file_name',
    [
        'incident_98_markdown_affected_sequence_broken.md',
        'incident_99_yaml_affected_sequence_broken.yml',
    ],
    ids=['markdown', 'yaml'],
)
def test_affected_sequence_produces_controlled_validation_error(file_name):
    with pytest.raises(ValueError, match='affected'):
        parse_incident(file_name)
