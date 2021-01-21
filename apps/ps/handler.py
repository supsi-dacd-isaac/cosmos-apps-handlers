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
import utilities as u

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

    # Get configuration about sidechain info
    tmp_config = json.loads(open(cfg['sidechainFile']).read())
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

    app_cli = '%scli' % cfg['tendermint']['app']

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

    elif args.c == 'add_allowed_meters':

        for node in cfg["nodes"].keys():
            host = cfg['nodes'][node][2]
            user = cfg['nodes'][node][3]
            remote_goroot = cfg['nodes'][node][4]
            account = cfg['nodes'][node][5]

            real_cmd = '%s/bin/%s keys show %s' % (remote_goroot, app_cli, u.get_real_account(host, user, account))
            key_str = u.exec_real_cmd(host, user, real_cmd, False)

            # Build the dataset
            res = ''
            for elem in key_str:
                res = '%s%s' % (res, elem)
            data_key = json.loads(res)

            # Do the transaction
            transaction_params = {
                "meter": data_key["name"],
                "account": data_key["address"]
            }
            ci.do_transaction(cmd='meterAccount', params=transaction_params)

            # Wait enough time
            time.sleep(6)

    elif args.c == 'set_market_parameters':
        ci.do_transaction(cmd='parameters', params=cfg['defaultMarketParameters'])

        # Wait enough time
        time.sleep(6)

    elif args.c == 'set_admin':
        host = cfg['nodes'][cfg["admin"]][2]
        user = cfg['nodes'][cfg["admin"]][3]
        remote_goroot = cfg['nodes'][cfg["admin"]][4]
        account = cfg['nodes'][cfg["admin"]][5]

        real_cmd = '%s/bin/%s keys show %s' % (remote_goroot, app_cli, u.get_real_account(host, user, account))
        key_str = u.exec_real_cmd(host, user, real_cmd, False)

        # Build the dataset
        res = ''
        for elem in key_str:
            res = '%s%s' % (res, elem)
        data_key = json.loads(res)
        ci.do_transaction(cmd='setAdmin', params={'address': data_key['name']})

    elif args.c == 'list_allowed_meters':
        data = ci.do_query(cmd='meterAccount', params={})
        logger.info(data)

    elif args.c == 'list_market_parameters':
        data = ci.do_query(cmd='parameters', params={})
        logger.info(data)

    elif args.c == 'show_admin':
        data = ci.do_query(cmd='getAdmin', params={})
        logger.info(data)

    elif args.c == 'get_account_info':
        logger.info(ci.get_account_info())

    elif args.c == 'get_account_sequence_numbers':
        an, sn = ci.get_account_sequence_numbers()
        logger.info('Account number: %i' % an)
        logger.info('Sequence number: %i' % sn)

    # starting program
    logger.info('Ending program')
