from opencanary_correlator.common.redismanager import redis, KEY_DEVICE, KEY_TRACK_HOST_PORT_SCAN, KEY_TRACK_NETWORK_PORT_SCAN
from opencanary_correlator.common.utils import current_time_offset
from opencanary_correlator.common.incidents import IncidentFactory
from opencanary_correlator.common.logs import logger
import opencanary_correlator.common.config as c

def defaultHandler(incidentName):
    def handler(data=None):
        IncidentFactory.create_incident(incidentName, data=data)
    return handler

def handleHTTPLogin(data=None):
    IncidentFactory.create_incident('http.login_attempt', data=data)

def handleSSHLogin(data=None):
    IncidentFactory.create_incident('ssh.login_attempt', data=data)

def handleSMBFileOpen(data=None):
    IncidentFactory.create_incident('smb.file_open', data=data)

handleFTPLogin = defaultHandler('ftp.login_attempt')
handleTelnetLogin = defaultHandler('telnet.login_attempt')
handleHTTPProxy = defaultHandler('httpproxy.login_attempt')
handleMySQL = defaultHandler('mysql.login_attempt')
handleMSSQL = defaultHandler('mssql.login_attempt')
handleTFTP = defaultHandler('tftp.action')
handleNTP = defaultHandler('ntp.monlist')
handleVNC = defaultHandler('vnc.login_attempt')
handleSNMP = defaultHandler('snmp.cmd')
handleRDP =  defaultHandler('rdp.login_attempt')
handleSIP = defaultHandler('sip.login_attempt')


def handleSYNPacketHostPortscanDetector(data=None):
    """
    Creates an incident if a single canary receives SYN packets to more than 10 different
    ports in less than 50 seconds.
    """
    try:
        host_scan_key = KEY_TRACK_HOST_PORT_SCAN + data['src_host'] + ':' + data['dst_host']
        new_set = False
        if not redis.exists(host_scan_key):
            new_set = True
        if redis.sadd(host_scan_key, data['dst_port']):
            if new_set:
                redis.expire(host_scan_key, c.config.getVal('portscan.monitor_period', default=50))

            if redis.scard(host_scan_key) >= c.config.getVal('portscan.packet_threshold', default=5):
                data['logdata'] = list(redis.smembers(host_scan_key))
                IncidentFactory.create_incident('scans.host_portscan', data=data)
                redis.delete(host_scan_key)
    except Exception as e:
        import traceback
        logger.critical(traceback.format_exc())

def handleSYNPacketNetworkPortscanDetector(data=None):
    """
    Creates an incident if two or more canaries report a syn packet to the same dst port,
    from the same host, in an hour or less.
    """

    try:
        network_scan_target_key = KEY_TRACK_NETWORK_PORT_SCAN + data['src_host'] + ':' + data['dst_port'] + ':targets'
        try:
            dst_host = data['reported_dst_host']
        except KeyError:
            dst_host = data['dst_host']

        if not redis.sismember(network_scan_target_key, dst_host):
            redis.sadd(network_scan_target_key, dst_host)
            redis.expire(network_scan_target_key, c.config.getVal('networkscan.monitor_period', default=3600))

        pckt_count = redis.scard(network_scan_target_key)

        if pckt_count >= c.config.getVal('networkscan.packet_threshold', default=2):
            data['logdata'] = list(redis.smembers(network_scan_target_key))
            IncidentFactory.create_incident('scans.network_portscan', data=data)
    except Exception as e:
        import traceback
        logger.critical(traceback.format_exc())
