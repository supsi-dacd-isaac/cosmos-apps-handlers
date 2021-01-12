# --------------------------------------------------------------------------- #
# Modules
# --------------------------------------------------------------------------- #
import argparse
import json
import logging
import pytz
import sys
import os
import time

from influxdb import InfluxDBClient

from classes.cosmos_interface import CosmosInterface
from classes.influxdb_interface import InfluxDBInterface

# --------------------------------------------------------------------------- #
# Classes
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Functions
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # --------------------------------------------------------------------------- #
    # Arguments
    # --------------------------------------------------------------------------- #
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-f', help='configuration file')
    arg_parser.add_argument('-c', help='command')
    arg_parser.add_argument('-s', help='signal')
    arg_parser.add_argument('-l', help='log file')

    args = arg_parser.parse_args()
    cfg = json.loads(open(args.f).read())

    # Get configuration about connections to InfluxDB and remote service related to data retrieving
    tmp_config = json.loads(open(cfg['connectionsFile']).read())
    cfg.update(tmp_config)

    # set logging object
    if not args.l:
        log_file = None
    else:
        log_file = args.l

    # define logger
    logger = logging.getLogger()
    logging.basicConfig(format='%(asctime)-15s::%(levelname)s::%(funcName)s::%(message)s', level=logging.INFO,
                        filename=log_file)

    # starting program
    logger.info('Starting program')

    ci = CosmosInterface(app='ps', cfg=cfg, logger=logger)

    if args.c == 'set_measure':
        signal = args.s

        influxdb_interface = InfluxDBInterface(cfg=cfg, logger=logger)
        end_dt_utc = influxdb_interface.get_dt('now_s00', flag_set_minute=False)
        value = influxdb_interface.get_dataset(signal, end_dt_utc)

        timestamp = '%s' % int(end_dt_utc.timestamp())

        str_value = '%.2f' % value

        # Do the transaction
        transaction_params = {
                        "signal": signal,
                        "timestamp": timestamp,
                        "value": str_value
                   }
        ci.do_transaction(cmd='setMeasure', params=transaction_params)

        # Wait enough time
        time.sleep(6)

        # Do a query
        query_params = {
                        "signal": signal,
                        "timestamp": timestamp
                       }
        data = ci.do_query(cmd='getMeasure', params=query_params)
        logger.info(data)

        data = ci.do_query(cmd='getMeasure', params={"signal": 'E_cons', "timestamp": timestamp})
        logger.info(data)

    # starting program
    logger.info('Ending program')
