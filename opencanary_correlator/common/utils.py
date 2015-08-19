from datetime import datetime
import string

def current_time_offset():
    return int(datetime.utcnow().strftime("%s"))

def get_clock():
    now = datetime.utcnow()
    day = string.lstrip(now.strftime("%d"),'0')
    return {'date': now.strftime("%B "+day+", %Y"), 'time': now.strftime('%H:%M')}

def seconds_to_age(s):
    try:
        weeks, remainder = divmod(int(s),         60*60*24*7)
        days, remainder  = divmod(remainder, 60*60*24)
        hours, remainder = divmod(remainder, 60*60)
        minutes, seconds = divmod(remainder, 60)
        if weeks > 0:
            num = weeks
            time_str = 'week'
        elif days > 0:
            num = days
            time_str = 'day'
        elif hours > 0:
            num = hours
            time_str = 'hour'
        elif minutes > 0:
            num = minutes 
            time_str = 'minute'
        elif seconds >= 0:
            num = seconds
            time_str = 'second'
        else:
            num = -1
            time_str = 'age error'

        return '{0} {1}{2}'.format(int(num), time_str, 's' if num != 1 else '')
    except Exception as e:
        return 'age error'

def timestamp_age(timestamp):
        t = datetime.fromtimestamp(float(timestamp))
        now = datetime.utcnow()
        return seconds_to_age((now - t).total_seconds())

def timestamp_printable(timestamp):
    try:
        t = datetime.fromtimestamp(float(timestamp))
        return t.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (UTC)")
    except:
        return str(timestamp)

def timestamp_js(timestamp):
    return int(float(timestamp)*1000)
