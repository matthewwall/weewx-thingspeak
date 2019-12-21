# $Id: thingspeak.py 1483 2016-04-25 06:53:19Z mwall $
# Copyright 2013-2014 Matthew Wall

"""
ThingSpeak calls itself "The open data platform for the internet of things".

https://thingspeak.com

This is a weewx extension that uploads data to ThingSpeak.

[StdRESTful]
    [[ThingSpeak]]
        api_key = TOKEN

[StdRESTful]
    [[ThingSpeak]]
        api_key = TOKEN
        unit_system = METRICWX

[StdRESTful]
    [[ThingSpeak]]
        api_key = TOKEN
        [[[fields]]]
            [[[[field1]]]]
                obs = barometer
            [[[[field2]]]]
                obs = outTemp
                units = degree_C
            [[[[field3]]]]
                obs = inTemp
                format = %.3f
"""

import Queue
import sys
import syslog
import time
import urllib
import urllib2

import weewx
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool, accumulateLeaves

VERSION = "X"

if weewx.__version__ < "3":
    raise weewx.UnsupportedFeature("weewx 3 is required, found %s" %
                                   weewx.__version__)

def logmsg(level, msg):
    syslog.syslog(level, 'restx: ThingSpeak: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

def _obfuscate(s):
    return ('X'*(len(s)-4) + s[-4:])

# some unit labels are rather lengthy.  this reduces them to something shorter.
UNIT_REDUCTIONS = {
    'degree_F': 'F',
    'degree_C': 'C',
    'inch': 'in',
    'mile_per_hour': 'mph',
    'mile_per_hour2': 'mph',
    'km_per_hour': 'kph',
    'km_per_hour2': 'kph',
    'meter_per_second': 'mps',
    'meter_per_second2': 'mps',
    'degree_compass': None,
    'watt_per_meter_squared': 'Wpm2',
    'uv_index': None,
    'percent': None,
    'unix_epoch': None,
    }

# return the units label for an observation
def _get_units_label(obs, unit_system):
    (unit_type, _) = weewx.units.getStandardUnitType(unit_system, obs)
    return UNIT_REDUCTIONS.get(unit_type, unit_type)

# get the template for an observation based on the observation key
def _get_template(obs_key, overrides, append_units_label, unit_system):
    tmpl_dict = dict()
    if append_units_label:
        label = _get_units_label(obs_key, unit_system)
        if label is not None:
            tmpl_dict['name'] = "%s_%s" % (obs_key, label)
    for x in ['name', 'format', 'units']:
        if x in overrides:
            tmpl_dict[x] = overrides[x]
    return tmpl_dict


class ThingSpeak(weewx.restx.StdRESTbase):

    _DEFAULT_FIELDS = {
        'field1': { 'obs':'outTemp',     'format':'%.1f'   },
        'field2': { 'obs':'outHumidity', 'format':'%.0f'   },
        'field3': { 'obs':'windSpeed',   'format':'%.1f'   },
        'field4': { 'obs':'windDir',     'format':'%03.0f' },
        'field5': { 'obs':'windGust',    'format':'%.1f'   },
        'field6': { 'obs':'barometer',   'format':'%.3f'   },
        'field7': { 'obs':'rain',        'format':'%.2f'   },
        }

    def __init__(self, engine, config_dict):
        """This service recognizes standard restful options plus the following:

        Required parameters:

        api_key: unique token for write access

        Optional parameters:

        unit_system: one of US, METRIC, or METRICWX
        Default is None; units will be those of the data in the database

        fields: dictionary of weewx observation names with optional upload
        format and units that correspond to the 8 available thingspeak fields
        Default is outTemp, outHumidity, windSpeed, windDir, windGust,
        barometer, rain in default units.
        """
        super(ThingSpeak, self).__init__(engine, config_dict)        
        loginf("service version is %s" % VERSION)
        try:
            site_dict = config_dict['StdRESTful']['ThingSpeak']
            site_dict = accumulateLeaves(site_dict, max_level=1)
            site_dict['api_key']
        except KeyError, e:
            logerr("Data will not be uploaded: Missing option %s" % e)
            return

        site_dict.setdefault('augment_record', True)
        site_dict['augment_record'] = to_bool(site_dict.get('augment_record'))

        usn = site_dict.get('unit_system', None)
        if usn is not None:
            site_dict['unit_system'] = weewx.units.unit_constants[usn]

        site_dict.setdefault('fields', self._DEFAULT_FIELDS)

        # if we are supposed to augment the record with data from weather
        # tables, then get the manager dict to do it.  there may be no weather
        # tables, so be prepared to fail.
        try:
            if site_dict.get('augment_record'):
                _manager_dict = weewx.manager.get_manager_dict_from_config(
                    config_dict, 'wx_binding')
                site_dict['manager_dict'] = _manager_dict
        except weewx.UnknownBinding:
            pass

        self.archive_queue = Queue.Queue()
        self.archive_thread = ThingSpeakThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        if usn is not None:
            loginf("desired unit system is %s" % usn)
        loginf("Data will be uploaded using api_key %s" %
               _obfuscate(site_dict['api_key']))

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)

class ThingSpeakThread(weewx.restx.RESTThread):

    _DEFAULT_SERVER_URL = 'http://api.thingspeak.com/update'

    def __init__(self, queue, api_key,
                 fields=None, unit_system=None, augment_record=True,
                 server_url=_DEFAULT_SERVER_URL, skip_upload=False,
                 manager_dict=None,
                 post_interval=None, max_backlog=sys.maxint, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5):
        super(ThingSpeakThread, self).__init__(queue,
                                               protocol_name='ThingSpeak',
                                               manager_dict=manager_dict,
                                               post_interval=post_interval,
                                               max_backlog=max_backlog,
                                               stale=stale,
                                               log_success=log_success,
                                               log_failure=log_failure,
                                               max_tries=max_tries,
                                               timeout=timeout,
                                               retry_wait=retry_wait)
        self.api_key = api_key
        self.server_url = server_url
        self.fields = fields
        self.unit_system = unit_system
        self.augment_record = augment_record
        self.skip_upload = to_bool(skip_upload)

    def process_record(self, record, dbm):
        if self.augment_record and dbm:
            record = self.get_record(record, dbm)
        if self.unit_system is not None:
            record = weewx.units.to_std_system(record, self.unit_system)
        url = self.get_url(record)
        if self.skip_upload:
            loginf("skipping upload")
            return
        req = urllib2.Request(url)
        req.add_header("User-Agent", "weewx/%s" % weewx.__version__)
        req.add_header("THINGSPEAKAPIKEY", "%s" % self.api_key)
        self.post_with_retries(req)

    def check_response(self, response):
        txt = response.read()
        if txt == '0' :
            raise weewx.restx.FailedPost("Posting failed")

    def get_url(self, record):
        tstr = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                             time.gmtime(record['dateTime']))
        parts = {'datetime': tstr}
        for k in self.fields:
            try:
                obs = self.fields[k].get('obs')
                if obs in record and record[obs] is not None:
                    v = float(record[obs])
                    fmt = self.fields[k].get('format', '%s')
                    to_units = self.fields[k].get('units')
                    if to_units is not None:
                        (from_unit, from_group) = weewx.units.getStandardUnitType(record['usUnits'], obs)
                        from_t = (v, from_unit, from_group)
                        v = weewx.units.convert(from_t, to_units)[0]
                    parts[k] = fmt % v
            except (TypeError, ValueError):
                pass

        url = self.server_url + '?' + urllib.urlencode(parts)
        logdbg('url: %s' % url)
        return url
