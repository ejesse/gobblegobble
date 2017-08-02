import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



MOCK_SLACK=True
SLACKBOT_API_TOKEN='testtoken'
BOT_LOOP_SLEEP_TIME = .001
SECRET_KEY = 'fake-key'
INSTALLED_APPS = [
    "tests",
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
