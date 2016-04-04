import json
import time


class MockResponse():

    def __init__(self, text=None):
        self.text = text
        self.status_code = 200

class MockSearchList():
    pass


class MockSlackRequester():

    CALLS_TO_METHODS = {
        'chat.postMessage': 'chat_post_message'
    }

    @staticmethod
    def method_magic(api_method, **kwargs):
        if api_method not in MockSlackRequester.CALLS_TO_METHODS:
            raise AttributeError("API Method not found or not mocked at all")
        python_method = MockSlackRequester.CALLS_TO_METHODS[api_method]
        return getattr(MockSlackRequester, python_method)(**kwargs)

    @staticmethod
    def do(token, request="?", **kwargs):
        return MockSlackRequester.method_magic(request, **kwargs)

    @staticmethod
    def _test_magic(**kwargs):
        return kwargs

    @staticmethod
    def chat_post_message(**kwargs):
        response = {'channel': 'CBLAHCHANNEL',
             'message': {'text': kwargs['text'],
              'ts': time.time(),
              'type': 'message',
              'user': 'USOMEUSER'},
             'ok': True,
             'ts': time.time()}
        return MockResponse(text=json.dumps(response))

class MockSlackServer():

    def __init__(self, token, connect=True):
        self.token = token
        self.username = None
        self.domain = None
        self.login_data = {'self':{'created': 1459600186,'id': 'UJFIDFJDFAKE','manual_presence': 'active','name': 'edi','prefs': {}}}
        self.websocket = None
        self.users = MockSearchList()
        self.channels = MockSearchList()
        self.pingcounter = 0
        self.ws_url = None
        self.api_requester = MockSlackRequester()
        if token is not None:
            self.connected = True

    def api_call(self, method, **kwargs):
        return self.api_requester.do(self.token, method, **kwargs).text


class MockSlackClient():

    def __init__(self, token):
        self.token = token
        self.server = MockSlackServer(self.token, False)

    def rtm_connect(self):
        # assume we can connect if there's a valid token
        if self.token:
            return True
        else:
            return False

    def rtm_read(self):
        return []

    def api_call(self, method, **kwargs):
        result = json.loads(self.server.api_call(method, **kwargs))
        if self.server:
            if method == 'im.open':
                if "ok" in result and result["ok"]:
                    self.server.attach_channel(kwargs["user"], result["channel"]["id"])
            elif method in ('mpim.open', 'groups.create', 'groups.createchild'):
                if "ok" in result and result["ok"]:
                    self.server.attach_channel(result['group']['name'], result['group']['id'], result['group']['members'])
            elif method in ('channels.create', 'channels.join'):
                if 'ok' in result and result['ok']:
                    self.server.attach_channel(result['channel']['name'], result['channel']['id'], result['channel']['members'])
        return result
