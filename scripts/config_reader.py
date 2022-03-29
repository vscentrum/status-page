import pathlib
import yaml


def read_config(config_file_name):
    with open(config_file_name, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
    for field, value in config.items():
        if field.endswith('_dir') or field.endswith('_file'):
            config[field] = pathlib.Path(value)
        elif field.endswith('_dirs') or field.endswith('_files'):
            config[field] = list(map(lambda x: pathlib.Path(x),
                                     config[field]))
    return config
