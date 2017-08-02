import importlib
import json
import logging
import pkgutil
import random
import re
import sys
from threading import Thread
import time
import traceback

from slackclient import SlackClient
from websocket._exceptions import WebSocketConnectionClosedException

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from gobblegobble.exceptions import GobbleError
from gobblegobble.mock_slackclient import MockSlackClient
from gobblegobble.registry import RESPONSE_REGISTRY


LOGGER = logging.getLogger(__name__)


def import_submodules(package_name):
    # thank you stack overflow: http://stackoverflow.com/questions/3365740/how-to-import-all-submodules
    """ Import all submodules of a module, recursively

    :param package_name: Package name
    :type package_name: str
    :rtype: dict[types.ModuleType]
    """
    package = sys.modules[package_name]
    return {
        name: importlib.import_module(package_name + '.' + name)
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__)
    }


def import_bot_handlers():
    for app_config in apps.get_app_configs():
        # skip the built-in django apps
        if '/django/' not in app_config.path:
            import_submodules(app_config.module.__name__)


def gobble_listen(matchstr, flags=re.IGNORECASE):
    def wrapper(func):
        RESPONSE_REGISTRY[re.compile(matchstr, flags)] = func
        LOGGER.info('registered respond_to plugin "%s" to "%s"', func.__name__, matchstr)
        return func
    return wrapper


def _get_slack_client():
    # for testing
    if hasattr(settings,'MOCK_SLACK'):
        if settings.MOCK_SLACK:
            return MockSlackClient
    return SlackClient


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        # we need the else to test the init behavior
        # this is probably suboptimal
        else:
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]


class GobbleBot(metaclass=Singleton):

    def __init__(self, api_token=None):
        try:
            self._is_initialized
        except AttributeError:
            self._actual_initialize(api_token=api_token)

    def _actual_initialize(self, api_token=None):

        self.api_token = api_token
        self.bot_loop_sleep_time = .001
        if self.api_token is None:
            if hasattr(settings, 'SLACKBOT_API_TOKEN'):
                self.api_token = settings.SLACKBOT_API_TOKEN
        if self.api_token is None:
            raise ImproperlyConfigured("GobbleBot needs an API token, either GobbleBot(api_token='faketoken') or set SLACKBOT_API_TOKEN in django settings.")

        if hasattr(settings, 'BOT_LOOP_SLEEP_TIME'):
            self.bot_loop_sleep_time = settings.BOT_LOOP_SLEEP_TIME

        self.client = _get_slack_client()(self.api_token)
        LOGGER.info("Checking slack client")
        if self.client.rtm_connect():
            self.bot_name = self.client.server.login_data['self']['name']
            self.bot_id = self.client.server.login_data['self']['id']

            thread = Thread(target = self.listen)
            thread.setDaemon(True)
            thread.start()
            LOGGER.info("GobbleBot %s is connected to Slack RTM" % self.bot_name)
            self._is_initialized = True

        else:
            LOGGER.error("Failed test connection to Slack RTM")

    def listen(self, retry_number=0):
        if retry_number > 0:
            # backoff retries, max of 5 minute intervals
            timetosleep = min(300, (2 ** retry_number)) + (random.randint(0,1000) / 1000.0)
            LOGGER.error("Attempting reconnection to slack in %s seconds, retry number %s" % (timetosleep, retry_number))
            time.sleep(timetosleep)
        retry_number = retry_number+1
        if self.client.rtm_connect():
            # reset it if we connected successfully
            retry_number = 0
            LOGGER.warn("Connected to Slack RTM")
            while True:
                try:
                    for event in self.client.rtm_read():
                        LOGGER.debug('New event from RTM: %s' % event)
                        self.handle_event(event)
                    time.sleep(self.bot_loop_sleep_time)
                except:
                    traceback.print_exc()
                    LOGGER.error("Connection lost due to above error, trying to reconnect...")
                    self.listen(retry_number=retry_number)
        else:
            self.listen(retry_number=retry_number)

    def handle_event(self, event):
        try:
            # throw away anything not a message
            if 'type' in event:
                if event['type'] == 'message':
                    if GobbleBot.is_message_respondable(event, self.bot_name, self.bot_id):
                        message = Message(event)
                        LOGGER.info("Found respondable message %s, looking for matches..." % message.text)
                        for matcher in RESPONSE_REGISTRY.keys():
                            matches = matcher.match(message.text)
                            if matches is not None:
                                LOGGER.info("Message matched: %s" % matcher)
                                func = RESPONSE_REGISTRY[matcher]
                                func(message, *matches.groups())
            else:
                LOGGER.debug("Got an event from slack with no type??? Got: %s" % (event))
        except:
            LOGGER.exception("failed to handle RTM event %s" % event)
                #self.client.api_call("chat.postMessage", channel=event['channel'], text="Message was: %s" % event['text'], as_user=True)

    def is_explicit_at(self, message):
        if message['text'].lower().startswith("<@%s>" % self.bot_id.lower()):
            return True
        return False

    def send_message(self, message):
        if message.sent:
            raise GobbleError("Message already sent")
        response = self.client.api_call("chat.postMessage", channel=message.channel, text=message.full_text, as_user=True)
        if response['ok']:
            message.timestamp = response['ok']
            message.sent = True
        return response

    def quick_send(self, message, channel):
        m = Message()
        m.channel = channel
        m.full_text = message
        return self.send_message(m)

    @staticmethod
    def is_message_respondable(message, bot_name, bot_id):
        matchers = ["%s " % bot_name, "<@%s>" % bot_id]
        # make extra sure we do not reply infinite loop
        # so ignore everything where the bot is the user
        if 'hidden' in message:
            if message['hidden']:
                return False
        if 'user' in message:
            if message['user'] == bot_id:
                return False
        for matcher in matchers:
            if message['text'].lower().startswith(matcher.lower()):
                return True
        try:
            wildcards = settings.GOBBLE_BOT_ALIASES
        except AttributeError:
            wildcards = []
        for wildcard in wildcards:
            if message['text'].lower().find(wildcard) > 0:
                return True
        return False


class Message():

    def __init__(self, message_dict=None):
        self.text = None
        self.full_text = None
        self.sender = None
        self.channel = None
        self.timestamp = None
        self.at_user = None
        self.team = None
        self.sent = False
        self.response = None

        if message_dict is not None:
            self.parse_message(message_dict)

        if self.timestamp is not None:
            self.sent = True

    def parse_message(self, message_dict):
        if not isinstance(message_dict, dict):
            message_dict = json.loads(message_dict)
        self.sender = message_dict['user']
        self.channel = message_dict['channel']
        if 'ts' in message_dict:
            self.timestamp = message_dict['ts']
        self.team = None
        if 'team' in message_dict:
            self.team = message_dict['team']

        # since this is a bot we're going to strip out
        # the bot trigger from "text even tho strictly
        # it was in the text, see full_text for that content
        self.full_text = message_dict['text']
        bot = GobbleBot()
        if self.full_text.lower().startswith("%s " % (bot.bot_name.lower())):
            self.text = self.full_text[len(bot.bot_name)+1:]
        else:
            self.text = self.full_text

    def reply(self, reply_text):
        """
        '@'s the original sender with a new message from the bot
        to the same channel as the original
        """
        return self.respond("<@%s> %s"% (self.sender, reply_text))

    def respond(self, response_text):
        """
        Effectively just sends a new message from the bot
        to the same channel as the original
        """
        message = Message()
        message.channel = self.channel
        message.text = response_text
        message.full_text = response_text
        self.response = message
        bot = GobbleBot()
        return bot.send_message(message)

    def send(self):
        # convenience method
        bot = GobbleBot()
        bot.send(self)
