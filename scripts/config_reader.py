import pathlib
import yaml


def read_config(config_file_name):
    with open(config_file_name, 'r') as config_file:
        config = yaml.safe_load(config_file)
    for field, value in config.items():
        if field.endswith('_dir') or field.endswith('_file'):
            config[field] = pathlib.Path(value)
        elif field.endswith('_dirs') or field.endswith('_files'):
            config[field] = list(map(lambda x: pathlib.Path(x),
                                     config[field]))
    for field in ('affected_aliases', 'affected_display_names'):
        config[field] = config.get(field) or {}
    return config
