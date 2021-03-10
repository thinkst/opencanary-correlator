
from opencanary_correlator.common.redismanager import redis, KEY_LOGS, KEY_INCIDENTS, KEY_DEVICE, \
    KEY_USER, KEY_USER_COUNT,\
    KEY_CONSOLE_SETTING_PREFIX, \
    KEY_WHITELIST_IPS
from opencanary_correlator.common.utils import timestamp_age, timestamp_printable, timestamp_js
from opencanary_correlator.common.logs import logger
from opencanary_correlator.common.incidents import Incident
import nacl.hash
import datetime
import simplejson

def get_device_id_hash(device_id):
    return nacl.hash.sha256(str(device_id), encoder=nacl.encoding.RawEncoder)[:12].encode("hex")

def jsonify_incident(key, incident):
    incident['key'] = key
    incident['created_printable'] = timestamp_printable(incident['created'])
    incident['created_age']       = timestamp_age(incident['created'])
    incident['created_age_seconds'] = float(datetime.datetime.utcnow().strftime("%s")) - float(incident['created'])

    MAX_EVENT_COUNT = 100

    events_list_printable = []
    events_list           = []
    events = incident['events_list'].split(',')
    for e in events[:MAX_EVENT_COUNT]:
        events_list_printable.append(timestamp_printable(e))
        events_list.append(timestamp_js(e))
    incident['events_list_printable'] = ','.join(events_list_printable)
    incident['events_list'] = events_list
    if len(events) > MAX_EVENT_COUNT:
        incident['events_skipped'] = len(events) - MAX_EVENT_COUNT

    if incident.has_key('logdata'):
        incident['logdata'] = simplejson.loads(incident['logdata'])
        if type(incident['logdata']) == list:
            incident['logdata'] = incident['logdata'][:MAX_EVENT_COUNT]

    return incident

def _filter_incidents(filter_=None, include_hosts=True):
    host_cache = {}
    keys = redis.zrangebyscore(KEY_INCIDENTS, '-inf', '+inf')
    incidents = []
    for key in keys:
        incident = redis.hgetall(key)
        try:
            if not filter_(incident):
                continue

            if include_hosts:
                if not host_cache.has_key(incident['node_id']):
                    host_cache[incident['node_id']] = \
                        redis.hgetall(KEY_DEVICE+get_device_id_hash(incident['node_id']))
                incident['host'] = host_cache[incident['node_id']]
            incidents.append(jsonify_incident(key, incident))
        except Exception as e:
            logger.critical(e)

    return incidents

def get_device(node_id):
    try:
        host = redis.hgetall(KEY_DEVICE+get_device_id_hash(node_id))
        host['unacknowleged_incidents'] = get_unacknowledged_incidents(include_hosts=False, node_id=node_id)
        return host
    except:
        return None

def should_notify(node_id):
    key = KEY_DEVICE+get_device_id_hash(node_id)
    return redis.hget(key, 'ignore_notifications_general') != 'True'

def get_incident(key):
    try:
        incident = redis.hgetall(key)
        incident['host'] = redis.hgetall(KEY_DEVICE+get_device_id_hash(incident['node_id']))
        return jsonify_incident(key, incident)
    except:
        return None

def get_all_incidents(include_hosts=True, node_id=None):
    if node_id:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: node_id == incident['node_id'])
    else:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: True)

def get_all_incidents_objs():
    return [Incident.lookup_id(key=x['key']) for x in get_all_incidents()]

def get_unacknowledged_incidents(include_hosts=True, node_id=None):
    if node_id:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: incident['acknowledged'] == 'False' and
                                        node_id == incident['node_id'])
    else:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: incident['acknowledged'] == 'False')

def get_unacknowledged_incidents_objs():
    return [Incident.lookup_id(key=x['key']) for x in get_unacknowledged_incidents()]

def get_acknowledged_incidents(include_hosts=True, node_id=None):
    if node_id:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: incident['acknowledged'] == 'True' and
                                            node_id == incident['node_id'])
    else:
        return _filter_incidents(include_hosts=include_hosts,
                                 filter_=lambda incident: incident['acknowledged'] == 'True')


def get_acknowledged_incidents_objs():
    return [Incident.lookup_id(key=x['key']) for x in get_acknowledged_incidents()]

def clear_incidents():
    for incident_key in redis.zrevrangebyscore(KEY_INCIDENTS, '+inf', '-inf'):
        redis.delete(incident_key)

    redis.delete(KEY_INCIDENTS)

def write_log(logline):
    if redis.llen(KEY_LOGS) > 1000:
        redis.ltrim(KEY_LOGS, 0, 999)
    redis.lpush(KEY_LOGS, logline)

def get_logs(limit=None):
    return redis.lrange(KEY_LOGS, 0, -1)

def get_console_setting(setting, **kwargs):
    key = KEY_CONSOLE_SETTING_PREFIX+setting
    value = redis.get(key)
    if not value:
        return kwargs.get('default', None)
    return value

def set_console_setting(setting, value):
    key = KEY_CONSOLE_SETTING_PREFIX+setting
    return redis.set(key, value)

if __name__ == "__main__":
    print('All: %r'  % get_all_devices())
    print('All Incidents: %r' % get_all_incidents())
    print('All Unacknowledged Incidents: %r' % get_unacknowledged_incidents())
