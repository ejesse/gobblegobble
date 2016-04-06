from gobblegobble.bot import gobble_listen


@gobble_listen('hello')
@gobble_listen('hi')
def hi(message):
    message.respond("Hello <@%s>" % message.sender)


@gobble_listen('good morning')
def good_morning(message):
    message.respond("Good morning <@%s>" % message.sender)


@gobble_listen('good afternoon')
def good_afternoon(message):
    message.respond("Good afternoon <@%s>" % message.sender)


@gobble_listen('good evening')
def good_evening(message):
    message.respond("Good evening <@%s>" % message.sender)


@gobble_listen('ping')
def ping(message):
    message.respond('pong')


@gobble_listen("How's the new body working out?")
def edi_new_body(message):
    message.reply("It is interesting. The crew are approaching this platform to speak with me, even though they can do so anywhere on the ship. It's as if they wish to treat me as part of the crew. I am not, but this changes my perspective. I like it. ")