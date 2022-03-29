#!/usr/bin/env python

import argparse
from config_reader import read_config
import pprint


def main():
    arg_parser = argparse.ArgumentParser(description='check config file')
    arg_parser.add_argument('file', help='configuration file to check')
    options = arg_parser.parse_args()
    config = read_config(options.file)
    pprint.pprint(config)

if __name__ == '__main__':
    main()
