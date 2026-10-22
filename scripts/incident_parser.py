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


class IncidentParser:
    
    def __init__(self, meta_data_fields, affected, level,
                 sep=r'\s*,\s*',
                 is_permissive=True, is_verbose=False):
        self._meta_data_fields = meta_data_fields
        self._field_values = {
            'affected': affected,
            'level': level,
        }
        self._sep = sep
        self._is_permissive = is_permissive
        self._is_verbose = is_verbose
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
        with open(incident_file_name, 'r') as file:
            incident = yaml.load(file, Loader=yaml.FullLoader)
            if self._is_verbose:
                print(f"validating file '{incident_file_name}'", file=sys.stderr)
            self.validate_incident(incident_file_name, incident)
            # since incidents can have an impact on multiple domains, they are
            # added to the list of incidents for each domain separately.
            for domain in re.split(self._sep, incident['meta_data']['affected']):
                for field in self._meta_data_fields:
                    if field == 'affected':
                        self._incidents[field].append(domain)
                    else:
                        self._incidents[field].append(incident['meta_data'].get(field))
                self._incidents['updated'].append(last_updated)
                self._incidents['content'].append(incident['content'])
                # derive the id from the file name so that links remain valid
                # when other incident files are added or removed
                incident_id = pathlib.Path(incident_file_name).stem
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
            if incident_file.suffix == '.yml':
                try:
                    self.parse_file(incident_file,
                                    modification_dates.get(incident_file.name))
                except ValueError as error:
                    all_succeed = False
                    print(f'### error: {error}', file=sys.stderr)
                    if not self._is_permissive:
                        raise error
            # all non-hidden files in incidents dir must me *.yml files
            else:
                all_succeed = False
                error_msg = f"Found indicent file that does not have .yml extension: {incident_file}"
                print(f'### error: {error_msg}', file=sys.stderr)
                if not self._is_permissive:
                    raise ValueError(error_msg)
        return all_succeed
            
    @property
    def incidents(self):
        return pd.DataFrame(self._incidents)
    
    def validate_incident(self, incident_file_name, incident):
        if 'meta_data' not in incident:
            raise ValueError(f'{incident_file_name}: no meta_data')
        meta_data = incident['meta_data']
        for field in self._meta_data_fields:
            if field not in meta_data:
                raise ValueError(f'{incident_file_name}: metadata field "{field}" is missing')
        for field, expected_values in self._field_values.items():
            for value in re.split(self._sep, meta_data[field]):
                if value not in expected_values:
                    raise ValueError(f'{incident_file_name}: invalid {field} value {value}')
        if not isinstance(meta_data['start_date'], datetime.datetime):
            raise ValueError(f'{incident_file_name}: no valid start_date')
        if meta_data['end_date'] is not None and not isinstance(meta_data['end_date'], datetime.datetime):
            raise ValueError(f'{incident_file_name}: no valid end_date')
        if meta_data['end_date'] is not None and meta_data['end_date'] < meta_data['start_date']:
            raise ValueError(f'{incident_file_name} end_date before start_date')
        if not isinstance(meta_data['planned'], bool):
            raise ValueError(f'{incident_file_name} planned is not boolean')
        if 'content' not in incident:
            raise ValueError(f'{incident_file_name}: no content')

    @property
    def affected(self):
        return copy.copy(self._field_values['affected'])
    
    @property
    def services(self):
        return self.affected

    @property
    def levels(self):
        return copy.copy(self._field_values['level'])
