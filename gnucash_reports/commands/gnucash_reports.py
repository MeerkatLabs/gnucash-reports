"""
This is the main execution program for the reporting library.
"""
from __future__ import absolute_import

import argparse
import glob
import logging
import sys

import os
import os.path
import simplejson as json
from yaml import load

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.abspath(os.getcwd()))

from gnucash_reports.wrapper import initialize
from gnucash_reports.reports import run_report
from gnucash_reports.configuration import configure_application
from datetime import datetime


def load_plugins():
    import pkg_resources

    # Register the reports
    for ep in pkg_resources.iter_entry_points(group='gnucash_reports_reports'):
        loader = ep.load()
        loader()

    # Register the configuration
    for ep in pkg_resources.iter_entry_points(group='gnucash_reports_configuration'):
        loader = ep.load()
        loader()


def main():
    """
    Execute main application
    :return:
    """
    load_plugins()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='configuration', default='core.yaml',
                        help='core configuration details of the application')
    parser.add_argument('-r', '--report', dest='report', default=None,
                        help='only execute the requested report')

    args = parser.parse_args()

    with open(args.configuration) as file_pointer:
        configuration = load(file_pointer, Loader=Loader)

        session = initialize(configuration['gnucash_file'])
        output_location = configuration.get('output_directory', 'output')
        report_location = configuration.get('report_definitions', 'reports')
        configure_application(configuration.get('global', dict()))

    if not os.path.exists(output_location):
        os.makedirs(output_location)

    all_reports = []

    if not args.report:
        reports_list = glob.glob(os.path.join(report_location, '*.yaml'))
    else:
        reports_list = [args.report]

    for infile in sorted(reports_list):

        print 'Processing: %s' % infile
        with open(infile) as report_configuration_file:
            report_configuration = load(report_configuration_file, Loader=Loader)

            result_definition = dict(name=report_configuration.get('page_name', 'Unnamed Page'),
                                     reports=[])

            for report_definition in report_configuration['definitions']:

                result = run_report(report_definition)

                if result:
                    result_definition['reports'].append(result)

            output_file_name = os.path.split(infile)[-1] + '.json'

            with open(os.path.join(output_location, output_file_name), 'w') as output_file:
                json.dump(result_definition, output_file)
                all_reports.append(dict(name=result_definition.get('name'), file=output_file_name))

    session.close()

    definition_dictionary = dict(
        modification_time=datetime.now().strftime('%c'),
        last_updated=datetime.now().strftime('%c'),
        reports=all_reports
    )

    with open(os.path.join(output_location, '__reports.json'), 'w') as all_report_file:
        json.dump(definition_dictionary, all_report_file)


if __name__ == '__main__':
    main()