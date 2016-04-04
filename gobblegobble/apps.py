import logging

from django.apps import AppConfig
from django.conf import settings

from gobblegobble.bot import GobbleBot, import_bot_handlers


LOGGER = logging.getLogger()

def copy_prefixed_settings(prefix, settings_from, settings_to):
    for setting in dir(settings_from):
        if setting.startswith(prefix):
            new_name = setting.replace(prefix,'')
            LOGGER.info("Copying %s setting to slackbot as %s" %(setting, new_name))
            setattr(settings_to, new_name, getattr(settings_from,setting))


class GobbleGobbleConfig(AppConfig):

    name = 'gobblegobble'

    def ready(self):
        AppConfig.ready(self)
        bot = GobbleBot()
        import_bot_handlers()
