import os, sys, json, copy

SETTINGS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings.json")

class Config:
    def __init__(self, configfile=SETTINGS):
        self.__config = None
        self.__configfile = configfile

        # throw exception if fails
        with open(configfile, "r") as f:
            self.__config = json.load(f)

    def moduleEnabled(self, module_name):
        k = "%s.enabled" % module_name
        if k in self.__config:
            return bool(self.__config[k])
        return False

    def getVal(self, key, default=None):
        # throw exception to caller
        #figures out the return type from the passed default, uses str if none is supplied
        return_type = type(default)
        if return_type == type(None):
            return_type = str
        try:
            return return_type(self.__config[key])
        except KeyError as e:
            if default is not None:
                return default
            raise e

    def setVal(self, key, val):
        """Set value only if valid otherwise throw exception"""

        oldconfig = copy.deepcopy(self.__config)
        self.__config[key] = val

        err = self.valid()
        if err is not None:
            self.__config = oldconfig
            raise ConfigException(key, err)

    def valid(self):
        """
        Test whether config is in a valid state
        Return None if valid and string error message on first failure
        """

        return None


    def save(self):
        """Backup config file to older version and save to new file"""

        err = self.valid()
        if err is not None:
            raise ConfigException("config", "Can't save invalid config: %s" % err)

        try:
            cfg = self.__configfile
            os.rename(cfg, cfg + ".bak")

            with open(cfg, "w") as f:
                json.dump(self.__config, f)

        except Exception, e:
            print("[-] Failed to save config file %s" % e)
            raise ConfigException("config", e)

    def __repr__(self):
        return self.__config.__repr__()

    def __str__(self):
        return self.__config.__str__()

class ConfigException(Exception):
    """Exception raised on invalid config value"""

    def __init__(self, key, msg):
        self.key = key
        self.msg = msg

    def __repr__(self):
        return "<%s %s (%s)>" % (self.__class__.__name__, self.key, self.msg)

config = None
