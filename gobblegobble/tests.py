import json
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from gobblegobble.bot import GobbleBot, Message
from gobblegobble.exceptions import GobbleError
from gobblegobble.mock_slackclient import MockSlackRequester


@override_settings(MOCK_SLACK=True)
class TestGobbleBot(TestCase):

    def test__actual_initialize(self):
        bot = GobbleBot()
        with self.settings(SLACKBOT_API_TOKEN='testtoken1'):
            bot._actual_initialize()
            self.assertEqual(bot.api_token, 'testtoken1')
        with self.settings(SLACKBOT_API_TOKEN='testtoken2'):
            bot._actual_initialize(api_token='differenttoken')
            self.assertEqual(bot.api_token, 'differenttoken')
        with self.settings(SLACKBOT_API_TOKEN=None):
            bot.api_token = None
            self.assertRaises(ImproperlyConfigured, bot._actual_initialize)
            # fix it so other tests dont break
            bot._actual_initialize(api_token='somerandotoken')

    def test_missing_token(self):
        # note different from "None" above, this is
        # the actual lack of the attribute being in settings
        bot = GobbleBot()
        if hasattr(settings, 'SLACKBOT_API_TOKEN'):
            del settings.SLACKBOT_API_TOKEN
        bot.api_token = None
        self.assertRaises(ImproperlyConfigured, bot._actual_initialize)
        # fix it so other tests dont break
        bot._actual_initialize(api_token='somerandotoken')

    def test_is_respondable(self):
        bot = GobbleBot(api_token='faketoken')
        ignorable_message = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': 'test', 'channel': 'CFAKE123', 'ts': '1459618784.000031'}
        mention_message = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        mention_message_case = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name.upper(), 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        self_message = {'type': 'message', 'team': 'TFAKE123', 'user': bot.bot_id, 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        at_message = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '<@%s> hi' % bot.bot_id, 'channel': 'CFAKE123', 'ts': '1459619632.000033'}
        # better safe than sorry
        at_self_message = {'type': 'message', 'team': 'TFAKE123', 'user': bot.bot_id, 'text': '<@%s> hi' % bot.bot_id, 'channel': 'CFAKE123', 'ts': '1459619632.000033'}
        self.assertTrue(bot.is_message_respondable(mention_message))
        self.assertTrue(bot.is_message_respondable(mention_message_case))
        self.assertTrue(bot.is_message_respondable(at_message))
        self.assertFalse(bot.is_message_respondable(ignorable_message))
        self.assertFalse(bot.is_message_respondable(self_message))
        self.assertFalse(bot.is_message_respondable(at_self_message))
        self.assertFalse(bot.is_message_respondable({'type':'message','hidden':True}))

    def test_is_explicit_at(self):
        bot = GobbleBot(api_token='faketoken')
        at_message = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '<@%s> hi' % bot.bot_id, 'channel': 'CFAKE123', 'ts': '1459619632.000033'}
        mention_message = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        self.assertTrue(bot.is_explicit_at(at_message))
        self.assertFalse(bot.is_explicit_at(mention_message))

    def test_send_message(self):
        bot = GobbleBot(api_token='faketoken')
        message = Message({'text': 'test', 'user': bot.bot_id, 'channel': 'fakechannel', 'team': 'faketeam'})
        resp = bot.send_message(message)
        self.assertEqual(resp['message']['text'], message.text)
        self.assertTrue(resp['ok'])
        self.assertIsNotNone(message.timestamp)
        self.assertTrue(message.sent)

    def test_it_will_not_send_a_sent_message(self):
        bot = GobbleBot(api_token='faketoken')
        message = Message({'text': 'test', 'user': bot.bot_id, 'channel': 'fakechannel', 'team': 'faketeam', 'ts': time.time()})
        self.assertRaises(GobbleError, bot.send_message, message)


@override_settings(MOCK_SLACK=True)
class TestSlackMessage(TestCase):

    def test_parse_message(self):
        bot = GobbleBot(api_token='faketoken')
        message_dict = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        message = Message(message_dict)
        self.assertEqual(message.team, message_dict['team'])
        self.assertEqual(message.sender, message_dict['user'])
        self.assertEqual(message.full_text, message_dict['text'])
        self.assertEqual(message.text, 'test')
        self.assertEqual(message.channel, message_dict['channel'])
        self.assertEqual(message.timestamp, message_dict['ts'])
        self.assertTrue(message.sent)

    def test_it_parses_json_too(self):
        bot = GobbleBot(api_token='faketoken')
        message_dict = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        message = Message(json.dumps(message_dict))
        self.assertEqual(message.team, message_dict['team'])
        self.assertEqual(message.sender, message_dict['user'])
        self.assertEqual(message.full_text, message_dict['text'])
        self.assertEqual(message.text, 'test')
        self.assertEqual(message.channel, message_dict['channel'])
        self.assertEqual(message.timestamp, message_dict['ts'])
        self.assertTrue(message.sent)

    def test_respond(self):
        bot = GobbleBot(api_token='faketoken')
        message_dict = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        message = Message(message_dict)
        resp = message.reply("this is a reply")
        self.assertTrue(resp['ok'])
        self.assertIsNotNone(message.response.timestamp)
        self.assertTrue(message.response.sent)
        self.assertIsNotNone(message.response)
        self.assertEqual(message.response.full_text, "<@UFAKE123> this is a reply")

    def test_reply(self):
        bot = GobbleBot(api_token='faketoken')
        message_dict = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        message = Message(message_dict)
        bot = GobbleBot(api_token='faketoken')
        message_dict = {'type': 'message', 'team': 'TFAKE123', 'user': 'UFAKE123', 'text': '%s test' % bot.bot_name, 'channel': 'CFAKE123', 'ts': '1459618786.000032'}
        message = Message(message_dict)
        resp = message.respond("this is a response")
        self.assertTrue(resp['ok'])
        self.assertIsNotNone(message.response.timestamp)
        self.assertTrue(message.response.sent)
        self.assertIsNotNone(message.response)
        self.assertEqual(message.response.full_text, "this is a response")


@override_settings(MOCK_SLACK=True)
class TestMockSlack(TestCase):

    def test_method_magic(self):
        MockSlackRequester.CALLS_TO_METHODS['test.apiCall'] = '_test_magic'
        result = MockSlackRequester.method_magic('test.apiCall', foo='bar')
        self.assertEqual(result, {'foo':'bar'})


    def test_api_call(self):
        bot = GobbleBot('fjdksfjkdslfaketoken')
        resp = bot.client.api_call("chat.postMessage", channel="#bottesting", text="Hello from Python! :tada:", as_user=True)
        self.assertEqual(resp['message']['text'],"Hello from Python! :tada:")
