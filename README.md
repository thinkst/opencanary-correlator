OpenCanary Correlator
=======================
Thinkst Applied Research

Overview
--------
OpenCanary Correlator collects events from OpenCanary daemons and coalesces them. It sends alerts via email and sms

Prerequisites
-------------
* Redis
* Python 2.7
* Mandrill API keys for email
* Twillio API keys for sms

On Ubuntu install the following:

```$ sudo apt-get install redis-server libffi-dev python-dev```

Install
-----------------
* Create a virtualenv

```
$ virtualenv env
$ source env/bin/activate
```

* Install via pip, or

```
$ pip install opencanary-correlator
```

* Install from source

```
$ git clone https://github.com/thinkst/opencanary-correlator
$ cd opencanary-correlator
$ python setup.py install
```

Run
---------------

* Start Redis
* Locate the installed template config file, by running the correlator without any arguments

```
$ opencanary-correlator
Warning: no config file specified. Using the template config (which does not have any alerting configured):
/path/to/template/opencanary_correlator.conf
$ cp /path/to/template/opencanary_correlator.conf ./
```

* Edit the config file to add API keys, email address and/or phone numbers for alerts
* Run the correlator with saved config file

```
opencanary-correlator --config=./opencanary_correlator.conf
```

* Configure instances of opencanaryd to send events to the correlator.
