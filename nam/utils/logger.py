# -*- coding: utf-8 -*-
"""
    baca.utils.logger
    ~~~~~~~~~~~~~~~~~

    This module defines a custom logging class which allows python's logging
    to be used asynchronously with twisted.

    :copyright: © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import logging
from twisted.internet import defer
from twisted.python.log import PythonLoggingObserver

LoggingLoggerClass = logging.getLoggerClass()

class Logging(LoggingLoggerClass):
    def __init__(self, logger_name):
        LoggingLoggerClass.__init__(self, logger_name)

    @defer.inlineCallbacks
    def trace(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.log(self, 5, msg, *args, **kwargs)

    @defer.inlineCallbacks
    def debug(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.debug(self, msg, *args, **kwargs)

    @defer.inlineCallbacks
    def info(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.info(self, msg, *args, **kwargs)

    @defer.inlineCallbacks
    def warning(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.warning(self, msg, *args, **kwargs)

    warn = warning

    @defer.inlineCallbacks
    def error(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.error(self, msg, *args, **kwargs)

    @defer.inlineCallbacks
    def critical(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.critical(self, msg, *args, **kwargs)

    @defer.inlineCallbacks
    def exception(self, msg, *args, **kwargs):
        yield LoggingLoggerClass.exception(self, msg, *args, **kwargs)

def setup_logging():
    if logging.getLoggerClass() is not Logging:
        import nam.common
        if 'dev' in nam.common.get_version():
            format='%(asctime)s.%(msecs)03.0f [%(name)-30s:%(lineno)-4s] %(levelname)-7.7s: %(message)s'
        else:
            format='%(asctime)s.%(msecs)03.0f [%(name)-30s] %(levelname)-7.7s: %(message)s'
        logging.basicConfig(
            level=logging.DEBUG,
            datefmt='%H:%M:%S',
            format=format
        )
        logging.setLoggerClass(Logging)

        logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
        logging.getLogger('migrate').setLevel(logging.INFO)

        twisted_logging = PythonLoggingObserver('twisted')
        twisted_logging.start()
        logging.addLevelName(5, "TRACE")

def set_loglevel(logger, loglevel):
    log_levels = {
        "none": logging.NOTSET,
        "info": logging.INFO,
        "warn": logging.WARN,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "debug": logging.DEBUG,
        "trace": 5
    }
    logger.setLevel(log_levels[loglevel.lower()])
