import smtplib, ssl
import mandrill
import opencanary_correlator.common.config as c
from email.mime.text import MIMEText
from opencanary_correlator.common.logs import logger

#
# February 6, 2021 - Modifications to the send_email function:
#
# - Add functionality to log in to a secure SMTP server for sending e-mail
#
# NOTE: Customizations are based on https://realpython.com/python-send-email/
#       and https://xo.tc/installing-opencanary-on-a-raspberry-pi.html
#
def send_email(from_='notifications@opencanary.org', to='', subject='', message='', server='', port=25, username='', password=''):
    logger.debug('Emailing %s' % to)

    if not server:
        return

    msg = MIMEText(message)

    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    try:
        s = smtplib.SMTP(server, port)
        s.ehlo()
        s.starttls()
        s.ehlo()
        # Log in if appropriate
        if username and password:
            s.login(username, password)
        s.sendmail(from_, [to], msg.as_string())
        logger.info('Email sent to %s' % (to))
    except Exception as e:
        logger.error('Email sending produced exception %r' % e)
    finally:
        s.quit()

def mandrill_send(to=None, subject=None, message=None, reply_to=None):
    try:
        mandrill_client = mandrill.Mandrill(c.config.getVal("console.mandrill_key"))
        message = {
         'auto_html': None,
         'auto_text': None,
         'from_email': 'notifications@opencanary.org',
         'from_name': 'OpenCanary',
         'text': message,
         'subject': subject,
         'to': [{'email': to,
                 'type': 'to'}],
        }
        if reply_to:
            message["headers"] = { "Reply-To": reply_to }

        result = mandrill_client.messages.send(message=message, async=False, ip_pool='Main Pool')

    except mandrill.Error, e:
        print 'Oliver: mandrill_send'
        print 'A mandrill error occurred: %s - %s' % (e.__class__, e)
