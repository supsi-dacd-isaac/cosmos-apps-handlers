import json
import argparse
import datetime
import logging
import sys

from influxdb import InfluxDBClient

import utilities as f

from classes.cosmos_interface import CosmosInterface

import utilities as u

# Main
if __name__ == "__main__":

    # Input args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-f', help='file')
    arg_parser.add_argument('-n', help='Node name (e.g. 39189375, nuc01')
    arg_parser.add_argument('-c', help='geographical coordinates (lat;lon)')
    arg_parser.add_argument('-l', help='logger')
    args = arg_parser.parse_args()

    # Get configuration settings
    cfg = json.loads(open(args.f).read())
    tmp_config = json.loads(open(cfg['connectionsFile']).read())
    cfg.update(tmp_config)
    tmp_config = json.loads(open(cfg['sidechainFile']).read())
    cfg.update(tmp_config)

    # Logger
    if not args.l:
        log_file = None
    else:
        log_file = args.l

    logger = logging.getLogger()
    logging.basicConfig(format='%(asctime)-15s::%(levelname)s::%(funcName)s::%(message)s', level=logging.INFO,
                        filename=log_file)

    logger.info('Starting program')

    logger.info('Connection to InfluxDB source server on socket [%s:%s]' % (cfg['influxDB']['host'],
                                                                            cfg['influxDB']['port']))
    try:
        ifc = InfluxDBClient(host=cfg['influxDB']['host'], port=cfg['influxDB']['port'],
                             password=cfg['influxDB']['password'], username=cfg['influxDB']['user'],
                             database=cfg['influxDB']['db'], ssl=cfg['influxDB']['ssl'])
    except Exception as e:
        logger.error('EXCEPTION: %s' % str(e))
        influx_client = None

    # Get data from the chain, referred to one minute ago
    dt = datetime.datetime.now().replace(second=0) - datetime.timedelta(minutes=1)

    try:
        # Create Cosmos interface
        ci = CosmosInterface(app='ps', cfg=cfg, logger=logger)

        data_tkns = u.get_tokens_amount(ci, cfg, '%scli' % cfg['tendermint']['app'], logger)

        data_power_cons = ci.do_query(cmd='getMeasure', params={'signal': 'PImp', 'timestamp': int(dt.timestamp())})
        data_power_prod = ci.do_query(cmd='getMeasure', params={'signal': 'PExp', 'timestamp': int(dt.timestamp())})

        # Consumed power and energy
        P_cons = float(data_power_cons['result']['value'])
        E_cons = P_cons * cfg['utils']['minutesGrouping'] / 60

        # Produced power and energy
        P_prod = float(data_power_prod['result']['value'])
        E_prod = P_prod * cfg['utils']['minutesGrouping'] / 60

        # Produced power and energy
        P_tot = P_cons - P_prod
        E_tot = E_cons - E_prod

    except Exception as e:
        logger.error('EXCEPTION: %s' % str(e))
        sys.exit()

    try:
        [lat, lon] = args.c.split(',')

        point = {
                    'time': int(dt.timestamp()),
                    'measurement': cfg['influxDB']['measurement'],
                    'fields': {
                            'P_cons': P_cons,
                            'P_prod': P_prod,
                            'E_cons': E_cons,
                            'E_prod': E_prod,
                            'P_tot': P_tot,
                            'E_tot': E_tot,
                            data_tkns['value']['coins'][0]['denom']: int(data_tkns['value']['coins'][0]['amount'])
                    },
                    'tags': {
                                'lat': lat,
                                'lon': lon,
                                'address': str(data_tkns['value']['address']),
                                'id': str(data_power_cons['result']['meterId'])
                        }
                 }
        # data_tkns['value']['address']

        logger.info('Insert point in DB')
        ifc.write_points([point], time_precision='s')
    except Exception as e:
        logger.error('EXCEPTION: %s' % str(e))
        sys.exit()

    logger.info('Ending program')