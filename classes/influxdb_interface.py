import datetime
import pytz

from influxdb import InfluxDBClient

DT_FRMT = '%Y-%m-%dT%H:%M:%SZ'

class InfluxDBInterface:

    """ Class and methods to interact with a InfluxDB database
    """

    def __init__(self, cfg, logger):

        self.cfg = cfg
        logger.info('Connection to InfluxDb server on socket [%s:%s]' % (cfg['influxDB']['host'],
                                                                         cfg['influxDB']['port']))
        try:
            self.influx_client = InfluxDBClient(
                                                    host=cfg['influxDB']['host'],
                                                    port=cfg['influxDB']['port'],
                                                    password=cfg['influxDB']['password'],
                                                    username=cfg['influxDB']['user'],
                                                    database=cfg['influxDB']['db'],
                                                    ssl=cfg['influxDB']['ssl']
                                                )
        except Exception as e:
            logger.error('EXCEPTION: %s' % str(e))
            self.influx_client = None

        self.logger = logger

    def get_random_key(self, meter, dt_utc):
        str_query = 'SELECT value FROM random_keys WHERE meter=\'m_%s\' AND time=\'%s\'' % (meter,
                                                                                            dt_utc.strftime(DT_FRMT))

        try:
            result = self.influxdb_client.query(str_query)
            return result.raw['series'][0]['values'][0][1]
        except Exception as e:
            self.logger.info('Random key not available in InfluxDB')
            return None

    def get_single_value(self, signal, start, end):
        query = 'SELECT mean("value") FROM data WHERE signal=\'%s\' AND time>=\'%s\' and time<\'%s\'' % (signal,
                                                                                                         start,
                                                                                                         end)
        self.logger.info('Query: %s' % query)
        try:
            result = self.influx_client.query(query)
            return result.raw['series'][0]['values'][0][1]
        except Exception as e:
            self.logger.error('EXCEPTION: %s' % str(e))
            return 0

    def get_dataset(self, signal, end_dt):
        if 'minutesGrouping' not in self.cfg['utils'].keys():
            minutes_back = 15
        else:
            minutes_back = self.cfg['utils']['minutesGrouping']

        start_str_dt = datetime.datetime.strftime(end_dt-datetime.timedelta(minutes=minutes_back), DT_FRMT)
        end_str_dt = datetime.datetime.strftime(end_dt, DT_FRMT)
        return self.get_single_value(signal, start_str_dt, end_str_dt)

    def get_dt(self, str_dt, flag_set_minute=True):
        tz_local = pytz.timezone(self.cfg['utils']['timeZone'])

        if str_dt == 'now':
            dt = datetime.datetime.now()
        elif str_dt == 'now_s00':
            dt = datetime.datetime.now()
            dt = dt.replace(second=0, microsecond=0)
        else:
            dt = datetime.datetime.strptime(str_dt, DT_FRMT)
        dt = tz_local.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)

        if flag_set_minute is True:
            # Set the correct minute (0,15,30,45)
            return InfluxDBInterface.set_start_minute(dt_utc)
        else:
            return dt_utc

    @staticmethod
    def set_start_minute(dt_utc):
        if 0 <= dt_utc.minute < 15:
            return dt_utc.replace(minute=0, second=0, microsecond=0)
        elif 15 <= dt_utc.minute < 30:
            return dt_utc.replace(minute=15, second=0, microsecond=0)
        elif 30 <= dt_utc.minute < 45:
            return dt_utc.replace(minute=30, second=0, microsecond=0)
        else:
            return dt_utc.replace(minute=45, second=0, microsecond=0)
