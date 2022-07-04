import copy
import datetime
import pandas as pd
import pathlib
import re
import subprocess
import sys
import yaml


def get_modification_date(file_name):
    process = subprocess.run(['git', '--no-pager', 'log', '--format=%ci', file_name],
                             check=True, capture_output=True, text=True)
    date_strs = str(process.stdout).split('\n')
    return datetime.datetime.strptime(date_strs[0],
                                      '%Y-%m-%d %H:%M:%S %z') \
            .strftime('%Y-%m-%d %H:%M:%S')


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

    def parse_file(self, incident_file_name):
        if self._is_verbose:
            print(f"parsing file '{incident_file_name}'", file=sys.stderr)
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
                incident_nr = len(self._incidents['content'])
                self._incidents['id'].append(f'incident_{incident_nr:04d}')

    def parse(self, incident_dir_name):
        if self._is_verbose:
            print(f"parsing directory '{incident_dir_name}'", file=sys.stderr)
        incident_dir = pathlib.Path(incident_dir_name)
        all_succeed = True
        for incident_file in incident_dir.glob('*.yml'):
            try:
                self.parse_file(incident_file)
            except ValueError as error:
                print(f'### error: {error}', file=sys.stderr)
                all_succeed = False
                if not self._is_permissive:
                    raise error
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
