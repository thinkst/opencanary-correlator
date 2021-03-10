import logging

class RedisHandler(logging.Handler):
    """
    A class which sends records to a redis list.
    """

    def __init__(self, level=logging.NOTSET):
        #this song and dance avoids a circular dependency at load time,
        #by importing only when this class is instatiated
        super(RedisHandler, self).__init__(level=level)
        from queries import write_log
        self.write_log = write_log

    def emit(self, record):
        """
        Emit a record.
        """
        try:
            self.write_log(self.format(record))
        except:
            self.handleError(record)

logger = None
# Console and correlator use different logger names. Common modules
# should still log to the logger for the process under which they're running.
# Impact of this is we don't support multiple loggers per process

# In Python 3.x this will fail as dict_keys() is no longer returns a list, but an object.
# The following will provide an iterable list (if that is still the right thing to do)
# existing_logger_names = list(logging.getLogger().manager.loggerDict.keys())
existing_logger_names = logging.getLogger().manager.loggerDict.keys()
if len(existing_logger_names) > 0:
    lgr = existing_logger_names[0]
    logger = logging.getLogger(lgr)


