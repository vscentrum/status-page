import copy
import datetime
import zoneinfo
import pandas as pd
import pathlib
import re
import subprocess
import sys
import yaml


def format_git_date(date_str):
    return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z') \
            .astimezone(zoneinfo.ZoneInfo('Europe/Brussels')) \
            .strftime('%Y-%m-%d %H:%M:%S')


def get_modification_date(file_name):
    process = subprocess.run(['git', '--no-pager', 'log', '-1', '--format=%ci', '--', file_name],
                             check=True, capture_output=True, text=True)
    date_str = str(process.stdout).strip()
    if date_str:
        return format_git_date(date_str)
    else:
        mtime = pathlib.Path(file_name).stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')


def get_modification_dates(dir_name):
    '''Return the last commit date of all files in a directory, using a
    single pass over the history rather than one git log per file.'''
    if not pathlib.Path(dir_name).is_dir():                                                                             
        raise FileNotFoundError(f"The provided incident directory {dir_name} does not exist")
    assert pathlib.Path(dir_name).exists(), \
        f"The provided incident directory {dir_name} does not exist"
    # paths are listed relative to the repository root (--relative is not
    # applied to merge commits), so strip the directory's prefix
    process = subprocess.run(['git', 'rev-parse', '--show-prefix'],
                             cwd=dir_name, check=True, capture_output=True, text=True)
    prefix = process.stdout.strip()
    # --cc also lists files changed by merge commits, as git log <file> does
    process = subprocess.run(['git', '--no-pager', 'log', '--format=date:%ci',
                              '--name-only', '--cc', '--', '.'],
                             cwd=dir_name, check=True, capture_output=True, text=True)
    dates = {}
    date_str = None
    for line in process.stdout.splitlines():
        if line.startswith('date:'):
            date_str = line[len('date:'):]
        elif line.startswith(prefix):
            dates.setdefault(line[len(prefix):], format_git_date(date_str))
    return dates


INCIDENT_SUFFIXES = ('.yml', '.yaml', '.md')
FRONT_MATTER_DELIMITER = '---'


def read_yaml_incident(file):
    try:
        return yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ValueError(f'{file.name}: invalid YAML: {error}') from error


def is_front_matter_delimiter(line):
    """Return whether *line* is an unindented front-matter delimiter."""
    return line.rstrip('\r\n').rstrip(' \t') == FRONT_MATTER_DELIMITER


def read_markdown_incident(file):
    '''Read an incident written as Markdown with a YAML front matter block,
    i.e., the metadata fields between two '---' lines, followed by the
    description in Markdown.  The result has the same structure as a YAML
    incident file.'''
    lines = file.read().splitlines(keepends=True)
    if not lines or not is_front_matter_delimiter(lines[0]):
        raise ValueError(f"{file.name}: file should start with a "
                         f"'{FRONT_MATTER_DELIMITER}' line")
    for end, line in enumerate(lines[1:], start=1):
        if is_front_matter_delimiter(line):
            break
    else:
        raise ValueError(f"{file.name}: no closing '{FRONT_MATTER_DELIMITER}' "
                         "line for the metadata")
    try:
        meta_data = yaml.safe_load(''.join(lines[1:end]))
    except yaml.YAMLError as error:
        raise ValueError(f'{file.name}: invalid metadata: {error}') from error
    if not isinstance(meta_data, dict):
        raise ValueError(f'{file.name}: no meta_data')
    incident = {'meta_data': meta_data}
    content = ''.join(lines[end + 1:])
    if content.strip():
        incident['content'] = content
    return incident


class IncidentParser:
    
    def __init__(self, meta_data_fields, affected, level,
                 affected_aliases=None,
                 sep=r'\s*,\s*',
                 is_permissive=True, is_verbose=False):
        self._meta_data_fields = meta_data_fields
        # maps alternative names of affected domains to their name in the
        # list of affected domains
        self._affected_aliases = dict(affected_aliases or {})
        self._field_values = {
            'affected': affected,
            'level': level,
        }
        self._sep = sep
        self._is_permissive = is_permissive
        self._is_verbose = is_verbose
        self._incident_sources = {}
        self._incidents = {}
        for field in self._meta_data_fields:
            self._incidents[field] = []
        self._incidents['updated'] = []
        self._incidents['id'] = []
        self._incidents['content'] = []

    def parse_file(self, incident_file_name, last_updated=None):
        if self._is_verbose:
            print(f"parsing file '{incident_file_name}'", file=sys.stderr)
        if last_updated is None:
            last_updated = get_modification_date(incident_file_name)
        suffix = pathlib.Path(incident_file_name).suffix
        if suffix not in INCIDENT_SUFFIXES:
            raise ValueError(f'{incident_file_name}: incident file should have '
                             f'one of the extensions {", ".join(INCIDENT_SUFFIXES)}')
        with open(incident_file_name, 'r', encoding='utf-8') as file:
            if suffix == '.md':
                incident = read_markdown_incident(file)
            else:
                incident = read_yaml_incident(file)
            if self._is_verbose:
                print(f"validating file '{incident_file_name}'", file=sys.stderr)
            # derive the id from the file name so that links remain valid
            # when other incident files are added or removed
            incident_id = pathlib.Path(incident_file_name).stem
            self.validate_incident(incident_file_name, incident, incident_id)
            previous_source = self._incident_sources.get(incident_id)
            if previous_source is not None:
                raise ValueError(
                    f'{incident_file_name}: duplicate incident id '
                    f'{incident_id}; already used by {previous_source}'
                )
            self._incident_sources[incident_id] = str(incident_file_name)
            # since incidents can have an impact on multiple domains, they are
            # added to the list of incidents for each domain separately.
            # aliases are replaced by the name of the domain they refer to,
            # and an incident is added only once for each domain
            domains = dict.fromkeys(
                self._affected_aliases.get(domain, domain)
                for domain in re.split(self._sep, incident['meta_data']['affected'])
            )
            for domain in domains:
                for field in self._meta_data_fields:
                    if field == 'affected':
                        self._incidents[field].append(domain)
                    else:
                        self._incidents[field].append(incident['meta_data'].get(field))
                self._incidents['updated'].append(last_updated)
                self._incidents['content'].append(incident['content'])
                self._incidents['id'].append(f'incident_{incident_id}')

    def parse(self, incident_dir_name):
        if self._is_verbose:
            print(f"parsing directory '{incident_dir_name}'", file=sys.stderr)
        incident_dir = pathlib.Path(incident_dir_name)
        all_succeed = True
        modification_dates = get_modification_dates(incident_dir)
        # sort so output does not depend on file system order
        for incident_file in sorted(incident_dir.glob('*')):
            # ignore non-files and hidden files
            if (not incident_file.is_file() or
                incident_file.stem.startswith('.')):
                continue
            # all non-hidden files in incidents dir must be *.yml, *.yaml or
            # *.md
            # files, parse_file reports other files as errors
            try:
                self.parse_file(incident_file,
                                modification_dates.get(incident_file.name))
            except ValueError as error:
                all_succeed = False
                print(f'### error: {error}', file=sys.stderr)
                if not self._is_permissive:
                    raise error
        return all_succeed
            
    @property
    def incidents(self):
        return pd.DataFrame(self._incidents)
    
    def validate_incident(self, incident_file_name, incident, incident_id):
        if not isinstance(incident, dict):
            raise ValueError(f'{incident_file_name}: incident should be a mapping')
        if 'meta_data' not in incident:
            raise ValueError(f'{incident_file_name}: no meta_data')
        meta_data = incident['meta_data']
        if not isinstance(meta_data, dict):
            raise ValueError(f'{incident_file_name}: meta_data should be a mapping')
        for field in self._meta_data_fields:
            if field not in meta_data:
                raise ValueError(f'{incident_file_name}: metadata field "{field}" is missing')
        for field, expected_values in self._field_values.items():
            if not isinstance(meta_data[field], str):
                raise ValueError(f'{incident_file_name}: {field} should be a string')
            for value in re.split(self._sep, meta_data[field]):
                if field == 'affected':
                    value = self._affected_aliases.get(value, value)
                if value not in expected_values:
                    raise ValueError(f'{incident_file_name}: invalid {field} value {value}')
        if not isinstance(meta_data['title'], str) or not meta_data['title'].strip():
            raise ValueError(f'{incident_file_name}: no valid title')
        if not isinstance(meta_data['start_date'], datetime.datetime):
            raise ValueError(f'{incident_file_name}: no valid start_date')
        if meta_data['end_date'] is not None and not isinstance(meta_data['end_date'], datetime.datetime):
            raise ValueError(f'{incident_file_name}: no valid end_date')
        dates = [meta_data['start_date']]
        if meta_data['end_date'] is not None:
            dates.append(meta_data['end_date'])
        if any(date.tzinfo is not None and date.utcoffset() is not None
               for date in dates):
            raise ValueError(
                f'{incident_file_name}: timezone-aware dates are not supported; '
                'use local Europe/Brussels time without an offset'
            )
        if meta_data['end_date'] is not None and meta_data['end_date'] < meta_data['start_date']:
            raise ValueError(f'{incident_file_name} end_date before start_date')
        if not isinstance(meta_data['planned'], bool):
            raise ValueError(f'{incident_file_name} planned is not boolean')
        if ('content' not in incident or
                not isinstance(incident['content'], str) or
                not incident['content'].strip()):
            raise ValueError(f'{incident_file_name}: no content')
        # Make sure a valid anchor (the incident_id) was derived
        if not re.match("^[A-Za-z0-9_-]+$", incident_id):
            raise ValueError(f'{incident_file_name}: the derived incident_id '
                             f'{incident_id} should only contain letters, '
                             'digits, _ and -')

    @property
    def affected(self):
        return copy.copy(self._field_values['affected'])
    
    @property
    def services(self):
        return self.affected

    @property
    def levels(self):
        return copy.copy(self._field_values['level'])
