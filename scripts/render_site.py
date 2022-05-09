#!/usr/bin/env python

import argparse
from config_reader import read_config
import datetime
from incident_parser import IncidentParser
from os import stat
from pathlib import Path
import shutil
import sys
import utils


def create_overview_page(current_incidents, planned_maintenance, config):
    current_table = utils.dataframe_to_html_table(current_incidents[config['current_overview_columns']], config['no_news_message'])
    planned_table = utils.dataframe_to_html_table(planned_maintenance[config['planned_overview_columns']], config['no_news_message'])
    config['build_dir'].mkdir(exist_ok=True)
    utils.process_template(config['template_dir'] / 'index.html', config['build_dir'] / 'index.html',
                           {'overview_table_current': current_table,
                            'overview_table_planned': planned_table})


def create_service_page(service, current_incidents, planned_maintenance, config):
    service_name = utils.format_name(service)
    incident_tmpl = utils.read_template(config['template_dir'] / config['incident_template_file'])
    current_incidents_text = utils.dataframe_to_html_text(current_incidents, incident_tmpl, config['no_news_message'])
    planned_maintenance_text = utils.dataframe_to_html_text(current_incidents, incident_tmpl, config['no_news_message'])
    utils.process_template(config['template_dir'] / config['service_template_file'], config['build_dir'] / f'{service}.html',
                           {'service_name': service_name,
                            'current_text': current_incidents_text,
                            'planned_text': planned_maintenance_text})


def copy_resources(config):
    for resource in config['resource_files']:
        resource_path = config['template_dir'] / resource
        if resource_path.is_file():
            shutil.copy(resource_path, config['build_dir'])
        elif resource_path.is_dir():
            shutil.copytree(resource_path, config['build_dir'] / resource, dirs_exist_ok=True)


def main():
    arg_parser = argparse.ArgumentParser(description='generate web site pages')
    arg_parser.add_argument('--now', help='fix datetime for debug and testing purposes')
    arg_parser.add_argument('--config', default='config/config.yml',
                            help="configuratin file to use")
    arg_parser.add_argument('--verbose', action='store_true',
                            help='verbose output for monitoring/debugging')
    options = arg_parser.parse_args()
    if options.now is not None:
        now = datetime.datetime.fromisoformat(options.now)
    else:
        now = datetime.datetime.now()
    if options.verbose:
        print(f'time: {now}')
    config = read_config(options.config)

    # set constant
    utils.NONE_DATE_STR = config['none_date_str']
    
    # parse incidents
    parser = IncidentParser(
        meta_data_fields=config['meta_data_fields'],
        affected=config['affected'],
        level=config['level'],
        is_verbose=options.verbose
    )
    for dir_path in config['incident_dirs']:
        parser.parse(dir_path)
    incidents = parser.incidents

    current_incidents = utils.select_current_incidents(incidents, date=now)
    planned_maintenance = utils.select_planned_maintenance(incidents, date=now)
    
    index_current_incidents = utils.add_href(current_incidents)

    create_overview_page(current_incidents=index_current_incidents,
                         planned_maintenance=planned_maintenance,
                         config=config)

    for service in parser.services:
        current_service_incidents = current_incidents[current_incidents.affected == service]
        planned_service_maintenance = planned_maintenance[planned_maintenance.affected == service]
        create_service_page(service, current_service_incidents, planned_service_maintenance, config)

        
    copy_resources(config)

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
