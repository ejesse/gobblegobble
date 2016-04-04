import logging
import re

from gobblegobble.registry import RESPONSE_REGISTRY


LOGGER = logging.getLogger()


def gobble_respond_to_registry(matchstr, flags=0):
    """
    Gobblebot will do something and/or respond based on the message
    """
    def registrar(func):
        RESPONSE_REGISTRY[re.compile(matchstr, flags)] = func
        return func
    registrar.all = RESPONSE_REGISTRY
    return registrar



#def gobble_respond_to(matchstr, flags=0):
    """
    Gobblebot will do something and/or respond based on the message
    """
#    def wrapper(func):
#        #PluginsManager.commands['respond_to'][re.compile(matchstr, flags)] = func
#        LOGGER.info('registered respond_to plugin "%s" to "%s"', func.__name__, matchstr)
#        return func
#    return wrapper


def gobble_reply_to(matchstr, flags=0):
    """
    Gobblebot will @ the user who triggered the message
    """
    def wrapper(func):
        #PluginsManager.commands['listen_to'][re.compile(matchstr, flags)] = func
        LOGGER.info('registered listen_to plugin "%s" to "%s"', func.__name__, matchstr)
        return func
    return wrapper