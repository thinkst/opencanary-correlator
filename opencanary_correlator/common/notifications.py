from twilio.rest import TwilioRestClient
from opencanary_correlator.common.logs import logger
from opencanary_correlator.common.emailer import mandrill_send, send_email
import opencanary_correlator.common.config as c
import requests

class SMS:
    def send(self, destination, message):
        ACCOUNT_SID = c.config.getVal('twilio.sid', default='')
        AUTH_TOKEN  = c.config.getVal('twilio.auth_token', default='')
        from_ = c.config.getVal('twilio.from_number', default='')

        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)


        client.messages.create(
            to=destination,
            from_=from_,
            body=message
        )

def notify(incident):
    if c.config.getVal('console.email_notification_enable', False):
        logger.debug('Email notifications enabled')
        addresses = c.config.getVal('console.email_notification_address', default=[])
        if c.config.getVal('console.mandrill_key', False):
            for address in addresses:
                logger.debug('Email sent to %s' % address)
                mandrill_send(to=address,
                              subject=incident.format_title(),
                              message=incident.format_report())
        else:
            server  = c.config.getVal('console.email_host', default='')
            port = int(c.config.getVal('console.email_port', default=25))
            if len(addresses) > 0 and server:
                for address in addresses:
                    send_email(to=address,
                               subject=incident.format_title(),
                               message=incident.format_report(),
                               server=server,
                               port=port)

    if c.config.getVal('console.sms_notification_enable', default=False):
        logger.debug('SMS notifications enabled')
        sms = SMS()
        sms_numbers = c.config.getVal('console.sms_notification_numbers', [])
        for to in sms_numbers:
            logger.debug('SMS sent to %s' % to)
            sms.send(to, incident.format_report_short())

    if c.config.getVal('console.slack_notification_enable', default=False):
        logger.debug('Slack notifications enabled')
        webhooks = c.config.getVal('console.slack_notification_webhook', default=[])
        for to in webhooks:
            response = requests.post(
                to, json={"text": incident.format_report_short()}
                )
            if response.status_code != 200:
                logger.error("Error %s sending Slack message, the response was:\n%s" % (response.status_code, response.text))
