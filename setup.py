from setuptools import setup, find_packages

from opencanary_correlator import __version__

setup(
    name='opencanary-correlator',
    version=__version__,
    url='http://www.thinkst.com/',
    author='Thinkst Applied Research',
    author_email='info@thinkst.com',
    description='opencanary correlator',
    install_requires=[
        "simplejson",
        "cffi==1.1.2",
        "docopt==0.4.0",
        "httplib2==0.9.1",
        "mandrill==1.0.57",
        "pycparser==2.14",
        "PyNaCl==0.3.0",
        "pytz==2015.4",
        "redis==2.10.3",
        "requests==2.7.0",
        "six==1.9.0",
        "twilio==4.4.0",
        "Twisted==15.2.1",
        "wheel==0.24.0",
        "zope.interface==4.1.2"
    ],
    setup_requires=[
        'setuptools_git'
    ],
    license='BSD',
    packages = find_packages(exclude="test"),
    scripts=['bin/opencanary-correlator'],
    platforms='any',
    include_package_data=True,
)
