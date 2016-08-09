# gobblegobble

A django app-based chatbot named after turkeys yelling at each other.

## Usage:

Requires Django 9.x, python 3.5 (probably? 2.7 might work???)

1. Clone the repo, run python setup.py install

2. In Django settings, add 'gobblegobble' to INSTALLED_APPS.

3. (Skip if you have a slack token) Get a slack API token from here: https://my.slack.com/services/new/bot

3. Add your Slack API KEY to your settings:

    ```SLACKBOT_API_TOKEN = 'yoursecrretapitoken'```

4. Run any Django command (manage.py shell or runserver) and the bot will start.

5. Invite your bot to any channels.

6. There are some basic built-in commands, note replace BOT_NAME with the name of your bot from step 3:

    ```BOT_NAME hello```

    ```BOT_NAME hi```

    ```BOT_NAME ping```

At this point you are up and running. The bot only uses the RTM API and therefore requires no webhooks or exposed webserver.

## Creating new handlers

To add to your bot's functionality, decorate a function in any file in any of your Django project's apps. For example:

```
from gobblegobble.bot import gobble_listen

@gobble_listen('testing')
def test_responder(message):
    message.respond('I hear you loud and clear')
```

Message has two primary methods, `respond` and `reply`. Respond will simply post the message in the channel where it was triggered. Reply will '@' the user who triggered the message.

