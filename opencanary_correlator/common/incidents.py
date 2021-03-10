from twisted.internet.threads import deferToThread
from opencanary_correlator.common.redismanager import *
from opencanary_correlator.common.constants import LOG_PORT_SCAN_NET, LOG_PORT_SCAN_HOST
from utils import current_time_offset
from notifications import notify
from logs import logger
import simplejson
import datetime
import opencanary_correlator.common.config as c

class Incident(object):
    CONFIG_INCIDENT_HORIZON = ''
    DESCRIPTION = 'Not available'

    def __init__(self, data=None, write_object=False, key=None):
        super(Incident, self).__setattr__('data', data)

        if write_object:
            self.do_creation()

        if key:
            self.key = key

    @classmethod
    def lookup_id(cls, id_=None, key=None):
        """This method can be called either on the parent Incident class
           or one of its subclasses.

           If called on Incident, a full key must be provided and this method
           returns a subclass.

           If called on a subclass, only the the incident ID must be provided.

           Returns an Incident subclass or None.
        """
        if key:
            if cls != Incident:
                return None

            if key.startswith(KEY_FTPLOGIN):
                cls = IncidentFTPLogin
            elif key.startswith(KEY_HTTP_LOGIN):
                cls = IncidentHTTPLogin
            elif key.startswith(KEY_SSH_LOGIN):
                cls = IncidentSSHLogin
            elif key.startswith(KEY_SMB_FILE_OPEN):
                cls = IncidentSMBFileOpen
            elif key.startswith(KEY_HOST_PORT_SCAN):
                cls = IncidentHostPortScan
            elif key.startswith(KEY_NETWORK_PORT_SCAN):
                cls = IncidentNetworkPortScan
            else:
                return None

        else:
            if id_ == None or cls == Incident:
                return None
            key = cls.INCIDENT_KEY_PREFIX+str(id_)

        fields = redis.hgetall(key)
        return cls(data=fields, key=key)

    def __getattr__(self, k):
        return self.data[k]

    def __setattr__(self, k, v):
        self.data[k] = v

    def save(self,):
        if not self.key:
            return False

        redis.hmset(self.key, self.data)

    def delete(self,):
        if not self.key:
            return False

        redis.zrem(KEY_INCIDENTS, self.key)
        if redis.delete(self.key) == 0:
            return False
        return True


    def find_incident(self, key_prefix=None, incident_horizon=None):
        start_time = current_time_offset()-incident_horizon

        recent_incidents = redis.zrevrangebyscore(KEY_INCIDENTS, '+inf', start_time)
        for incident in recent_incidents:
            if incident.startswith(key_prefix):
                return incident
        return None

    def make_key(self, time=''):
        if type(time) == float:
            time = repr(time)
        return self.INCIDENT_KEY_PREFIX + self.data['src_host'] + ':' + str(time)

    def add_log_data(self, current_incident):
        """
        Updates the log data field for the incident.

        Default action is to simple append to a list of data, but certain incidents (such as portscans)
        may want to preserve previously existing data differently. Overriding this method lets
        an incident decide how its log data is stored.
        """

        if current_incident.has_key('logdata'):
            current_incident['logdata'] = simplejson.loads(current_incident['logdata'])
        else:
            current_incident['logdata'] = []

        current_incident['logdata'].append(self.data['logdata'])
        current_incident['logdata'] = simplejson.dumps(current_incident['logdata'])

        return current_incident

    def do_creation(self,):
        """
        Insert an Incident hash.

        Before creating a new incident, a check is performed to see
        if the same src host has a live incident within the
        configured time horizon.
        """
        now = current_time_offset()
        incident_key_prefix = self.INCIDENT_KEY_PREFIX + self.data['src_host']
        incident_horizon = float(c.config.getVal(
                                    self.CONFIG_INCIDENT_HORIZON,
                                    default=c.config.getVal(
                                              'console.incident_horizon',
                                              default=60)))
        current_incident_key = self.find_incident(key_prefix=incident_key_prefix,
                                              incident_horizon=incident_horizon)

        if current_incident_key:
            #an incident already exists, update it
            current_incident = redis.hgetall(current_incident_key)
            current_incident['events_list'] += ','+repr(now)
            current_incident['events_count'] = int(current_incident['events_count'])+1
            current_incident['updated'] = True

            #add new log data to old incident
            if self.data.has_key('logdata'):
                current_incident = self.add_log_data(current_incident)

            redis.hmset(current_incident_key, current_incident)
            redis.zrem(KEY_INCIDENTS, current_incident_key)
            redis.zadd(KEY_INCIDENTS, now, current_incident_key)
        else:
            #this is a new incident
            incident_key = self.make_key(time=now)

            self.data['created'] = now
            self.data['events_list'] = repr(now)
            self.data['events_count'] = 1
            self.data['acknowledged'] = False
            self.data['notified'] = False
            self.data['updated'] = True
            self.data['description'] = self.DESCRIPTION
            if self.data.has_key('logdata'):
                if type(self.data['logdata']) == list:
                    self.data['logdata'] = simplejson.dumps(self.data['logdata'])
                else:
                    self.data['logdata'] = simplejson.dumps([self.data['logdata']])
            redis.hmset(incident_key, self.data)
            redis.zadd(KEY_INCIDENTS, now, incident_key)

            deferToThread(notify, self)

    def unacknowledge(self,):
        self.data['acknowledged'] = False
        self.save()

    def acknowledge(self,):
        self.data['acknowledged'] = True
        self.save()

    def format_title(self,):
        """Formatter for notifications"""
        return "{0} by {1} on {2} ({3})".format(self.DESCRIPTION, self.data['src_host'],
                                                self.data['node_id'], self.data['dst_host'])

    def _format_report(self,):
        """Formatter for notifications"""
        created = datetime.datetime.fromtimestamp(float(self.data['created'])).strftime('%Y-%m-%d %H:%M:%S (UTC)')
        return """
======================================================================
                                ALERT
======================================================================

  Incident: {0}
  Time    : {1}
  Source  : {2}
  Target  : {3} (id {4})
  EXTRA
======================================================================
""".format(self.DESCRIPTION, created, self.data['src_host'],
           self.data['dst_host'], self.data['node_id'])

    def format_report(self,):
        return self._format_report().replace('  EXTRA', '')

    def _format_report_short(self,):
        """Formatter for SMS notifications"""
        return  \
            """Canary Incident: {0}. Source {1}. Target {2} ({3}).EXTRA""".format(
           self.DESCRIPTION,
           self.data['src_host'],
           self.data['node_id'],
           self.data['dst_host'])

    def format_report_short(self,):
        return self._format_report_short().replace('EXTRA', '')


class IncidentFTPLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'ftp.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_FTPLOGIN
    DESCRIPTION = 'FTP Login Attempt'

class IncidentHTTPLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'http.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_HTTP_LOGIN
    DESCRIPTION = 'HTTP Login Attempt'

class IncidentSSHLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'ssh.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_SSH_LOGIN
    DESCRIPTION = 'SSH Login Attempt'

class IncidentTelnetLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'telnet.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_TELNET_LOGIN
    DESCRIPTION = 'Telnet Login Attempt'


class IncidentHTTProxy(Incident):
    CONFIG_INCIDENT_HORIZON = 'httproxy.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_HTTPPROXY_LOGIN
    DESCRIPTION = 'HTTP Proxy Login Attempt'


class IncidentMySQLLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'mysql.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_MYSQL_LOGIN
    DESCRIPTION = 'MySQL Login Attempt'


class IncidentMSSQLLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'mssql.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_MSSQL_LOGIN
    DESCRIPTION = 'MSSQL Login Attempt'


class IncidentTFTP(Incident):
    CONFIG_INCIDENT_HORIZON = 'tftp.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_TFTP
    DESCRIPTION = 'tftp login Attempt'

class IncidentNTPMonList(Incident):
    CONFIG_INCIDENT_HORIZON = 'ntp.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_NTP_MON_LIST
    DESCRIPTION = 'NTP Login Attempt'


class IncidentVNCLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'vnc.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_VNC_LOGIN
    DESCRIPTION = 'VNC Login Attempt'


class IncidentSNMP(Incident):
    CONFIG_INCIDENT_HORIZON = 'snmp.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_SNMP_LOGIN
    DESCRIPTION = 'SNMP Command Received'


class IncidentRDPLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'rdp.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_RDP_LOGIN
    DESCRIPTION = 'RDP Login Attempt'


class IncidentSIPLogin(Incident):
    CONFIG_INCIDENT_HORIZON = 'sip.incident_horizon'
    INCIDENT_KEY_PREFIX = KEY_SIP_LOGIN
    DESCRIPTION = 'SIP Login Attempt'



class IncidentSMBFileOpen(Incident):
    CONFIG_INCIDENT_HORIZON = 'smb.file_open_horizon'
    INCIDENT_KEY_PREFIX = KEY_SMB_FILE_OPEN
    DESCRIPTION = 'Shared File Opened'

    def format_report(self):
        report = self._format_report()
        try:
            d = simplejson.loads(self.data['logdata'])[0]
            filename = d['FILENAME']
            user = d['USER']
            report = report.replace('  EXTRA', '  File    : {0}\n  User    : {1}\n'.format(filename, user))
        except Exception as e:
            logger.error('Could not extract SMB filename from log data: %r' % (self.data))
        return report


    def format_report_short(self,):
        report = self._format_report_short()
        try:
            d = simplejson.loads(self.data['logdata'])[0]
            filename = d['FILENAME']
            user = d['USER']
            report = report.replace('EXTRA', ' File "{0}", user "{1}".'.format(filename, user))
        except Exception as e:
            logger.error('Could not extract SMB filename from log data: %r' % (self.data))
        return report

class IncidentHostPortScan(Incident):
    CONFIG_INCIDENT_HORIZON = 'scans.host_portscan_horizon'
    INCIDENT_KEY_PREFIX = KEY_HOST_PORT_SCAN
    DESCRIPTION = 'Host Port Scan'

    def add_log_data(self, current_incident):
        logger.debug('add_log_data(1)')
        if current_incident.has_key('logdata'):
            logger.debug('add_log_data(2)')
            logger.debug(current_incident['logdata'])
            logger.debug(simplejson.loads(current_incident['logdata']))
            current_incident['logdata'] = set(simplejson.loads(current_incident['logdata']))
        else:
            logger.debug('add_log_data(3)')
            current_incident['logdata'] = set()

        logger.debug('add_log_data(4)')
        current_incident['logdata'].update(self.data['logdata'])
        logger.debug(current_incident['logdata'])
        current_incident['logdata'] = simplejson.dumps(sorted([int(x) for x in current_incident['logdata']]))
        logger.debug(current_incident['logdata'])

        current_incident['logtype'] = LOG_PORT_SCAN_HOST
        return current_incident

class IncidentNetworkPortScan(Incident):
    CONFIG_INCIDENT_HORIZON = 'scans.network_portscan_horizon'
    INCIDENT_KEY_PREFIX = KEY_NETWORK_PORT_SCAN
    DESCRIPTION = 'Network Port Scan'

    def add_log_data(self, current_incident):
        logger.debug('network_add_log_data(1)')
        if current_incident.has_key('logdata'):
            logger.debug('network_add_log_data(2)')
            logger.debug(current_incident['logdata'])
            logger.debug(simplejson.loads(current_incident['logdata']))
            current_incident['logdata'] = set(simplejson.loads(current_incident['logdata']))
        else:
            logger.debug('network_add_log_data(3)')
            current_incident['logdata'] = set()

        logger.debug('network_add_log_data(4)')
        current_incident['logdata'].update(self.data['logdata'])
        logger.debug(current_incident['logdata'])
        current_incident['logdata'] = simplejson.dumps(list(current_incident['logdata']))
        logger.debug(current_incident['logdata'])

        current_incident['logtype'] = LOG_PORT_SCAN_NET
        return current_incident

    def format_report(self,):
        """Formatter for notifications"""
        try:
            targets = ', '.join([host for host in simplejson.loads(self.data['logdata'])])
        except:
            targets = 'Target data absent'
        return """
======================================================================
                                ALERT
======================================================================

  Incident: {0}
  Time    : {1}
  Source  : {2}
  Port    : {3}
  Targets : {4}

======================================================================
""".format(self.DESCRIPTION, self.data['created'], self.data['src_host'],
           self.data['dst_port'], targets)

class IncidentFactory:

    @classmethod
    def create_incident(cls, type_, data=None):
        print('{0}: {1}'.format(type_, data))
        logger.debug('Creating incident type: {0}'.format(type_))
        if type_ == 'ftp.login_attempt':
            IncidentFTPLogin(data=data, write_object=True)
        elif type_ == 'http.login_attempt':
            IncidentHTTPLogin(data=data, write_object=True)
        elif type_ == 'ssh.login_attempt':
            IncidentSSHLogin(data=data, write_object=True)
        elif type_ == 'smb.file_open':
            IncidentSMBFileOpen(data=data, write_object=True)
        elif type_ == 'scans.host_portscan':
            IncidentHostPortScan(data=data, write_object=True)
        elif type_ == 'scans.network_portscan':
            IncidentNetworkPortScan(data=data, write_object=True)
        elif type_ == 'telnet.login_attempt':
            IncidentTelnetLogin(data=data, write_object=True)
        elif type_ == 'httpproxy.login_attempt':
            IncidentHTTProxy(data=data, write_object=True)
        elif type_ == 'mysql.login_attempt':
            IncidentMySQLLogin(data=data, write_object=True)
        elif type_ == 'mssql.login_attempt':
            IncidentMSSQLLogin(data=data, write_object=True)
        elif type_ == 'tftp.action':
            IncidentTFTP(data=data, write_object=True)
        elif type_ == 'ntp.monlist':
            IncidentNTPMonList(data=data, write_object=True)
        elif type_ == 'vnc.login_attempt':
            IncidentVNCLogin(data=data, write_object=True)
        elif type_ == 'snmp.cmd':
            IncidentSNMP(data=data, write_object=True)
        elif type_ == 'rdp.login_attempt':
            IncidentRDPLogin(data=data, write_object=True)
        elif type_ == 'sip.login_attempt':
            IncidentSIPLogin(data=data, write_object=True)
        else:
            logger.error('Unknown incident type: {0}'.format(type_))


if __name__ == '__main__':
    test_events = [{'updated': 'True', 'src_port': '40198', 'logdata': "{u'USERNAME': u'qwe', u'PASSWORD': u'qwe'}", 'created': '1418997029.99313', 'notified': 'False', 'events_count': '4', 'acknowledged': 'False', 'logtype': '2000', 'dst_host': '192.168.233.1', 'node_id': '23456', 'local_time': '2014-12-19 11:29:43.671930', 'reported_dst_host': '127.0.0.1', 'events_list': '1418997029.99,1418997030.76,1418997031.3,1418997032.16', 'dst_port': '2100', 'src_host': '127.0.0.1'}, {'updated': 'True', 'src_port': '40198', 'logdata': "{u'USERNAME': u'qwe', u'PASSWORD': u'qwe'}", 'notified': 'False', 'events_count': '7', 'acknowledged': 'False', 'created': '1418996901.18268', 'logtype': '2000', 'dst_host': '192.168.233.1', 'node_id': '23456', 'local_time': '2014-12-19 11:29:43.671930', 'reported_dst_host': '127.0.0.1', 'events_list': '1418996901.18,1418996902.37,1418996903.1,1418996903.57,1418996904.0,1418996904.4,1418996904.85', 'dst_port': '2100', 'src_host': '127.0.0.1'}, {'updated': 'True', 'src_port': '40198', 'logdata': "{u'USERNAME': u'qwe', u'PASSWORD': u'qwe'}", 'created': '1418996840.670021', 'notified': 'False', 'events_count': '1', 'acknowledged': 'False', 'logtype': '2000', 'dst_host': '192.168.233.1', 'node_id': '23456', 'local_time': '2014-12-19 11:29:43.671930', 'reported_dst_host': '127.0.0.1', 'events_list': '1418996840.67', 'dst_port': '2100', 'src_host': '127.0.0.1'}]
    import pdb;pdb.set_trace()
    for data in test_events:
        IncidentFTPLogin(data=data, write_object=True)
