import smtplib
import mandrill
import opencanary_correlator.common.config as c
from email.mime.text import MIMEText
from opencanary_correlator.common.logs import logger

def send_email(from_='notifications@opencanary.org', to='', subject='', message='', server='', port=25):
    logger.debug('Emailing %s' % to)
    if not server:
        return

    msg = MIMEText(message)

    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    s = smtplib.SMTP(server, port)
    try:
        s.sendmail(from_, [to], msg.as_string())
        logger.info('Email sent to %s' % (to))
    except Exception as e:
        logger.error('Email sending produced exception %r' % e)
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

        # With Python 3.7 this line will fail because async is a reserved word
        # The new line should be: result = mandrill_client.messages.send(message=message, asy=False, ip_pool='Main Pool')
        result = mandrill_client.messages.send(message=message, async=False, ip_pool='Main Pool')

    except mandrill.Error, e:
        print('A mandrill error occurred: %s - %s' % (e.__class__, e))
