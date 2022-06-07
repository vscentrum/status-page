#!/usr/bin/env python

import argparse
from config_reader import read_config
from incident_parser import IncidentParser
from pathlib import Path
import sys


def main():
    arg_parser = argparse.ArgumentParser(description='generate web site pages')
    arg_parser.add_argument('incidents', nargs='?',
                            help='file or directory for incidents')
    arg_parser.add_argument('--config', default='config/config.yml',
                            help="configuratin file to use")
    arg_parser.add_argument('--verbose', action='store_true',
                            help='provide verbose output')
    options = arg_parser.parse_args()
    config = read_config(options.config)

    # parse incidents
    parser = IncidentParser(
        meta_data_fields=config['meta_data_fields'],
        affected=config['affected'],
        level=config['level'],
        is_verbose=options.verbose
    )
    if options.incidents is None:
        return 0 if all(map(lambda dir_path: parser.parse(dir_path),
                            config['incident_dirs'])) else 1
    else:
        path = Path(options.incidents)
        if path.is_dir():
            return 0 if parser.parse(path) else 1
        else:
            try:
                parser.parse_file(path)
                return 0
            except ValueError as error:
                print(f'### error: {error}', file=sys.stderr)
                return 1
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
