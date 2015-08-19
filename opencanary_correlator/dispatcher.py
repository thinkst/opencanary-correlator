import logging
logger = logging.getLogger('opencanary-correlator')

from opencanary_correlator.common.constants import *

from common.logs import RedisHandler

logger.setLevel(logging.DEBUG)
redis_h = RedisHandler()
redis_h.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
redis_h.setFormatter(formatter)
logger.addHandler(redis_h)

from opencanary_correlator.handlers import *

logmap = {
    LOG_BASE_BOOT: [],
    LOG_BASE_MSG: [],
    LOG_BASE_DEBUG: [],
    LOG_BASE_ERROR: [],
    LOG_FTP_LOGIN_ATTEMPT: [handleFTPLogin],
    LOG_HTTP_GET: [],
    LOG_HTTP_POST_LOGIN_ATTEMPT: [handleHTTPLogin],
    LOG_SSH_NEW_CONNECTION: [],
    LOG_SSH_REMOTE_VERSION_SENT: [],
    LOG_SSH_LOGIN_ATTEMPT: [handleSSHLogin],
    LOG_SMB_FILE_OPEN: [handleSMBFileOpen],
    LOG_PORT_SYN: [handleSYNPacketHostPortscanDetector, handleSYNPacketNetworkPortscanDetector],
    LOG_TELNET_LOGIN_ATTEMPT: [handleTelnetLogin],
    LOG_HTTPPROXY_LOGIN_ATTEMPT: [handleHTTPProxy],
    LOG_MYSQL_LOGIN_ATTEMPT: [handleMySQL],
    LOG_MSSQL_LOGIN_SQLAUTH: [handleMSSQL],
    LOG_MSSQL_LOGIN_WINAUTH: [handleMSSQL],
    LOG_TFTP: [handleTFTP],
    LOG_NTP_MONLIST: [handleNTP],
    LOG_VNC: [handleVNC],
    LOG_SNMP_CMD: [handleSNMP],
    LOG_RDP: [handleRDP],
    LOG_SIP_REQUEST: [handleSIP]
}


def process_device_report(data=None):
    logtype = data['logtype']
    if logtype not in logmap:
        logger.error('No handler for type %d ' %  (logtype))
        return

    for handler in logmap[logtype]:
        handler(data=data)
