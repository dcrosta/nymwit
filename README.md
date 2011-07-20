# Nymwit

Nymwit is a word game in which players compete to come up with the most
creative, popular, quirky, or notable acronym given a set of letters — in other
words, [backronyms](http://en.wikipedia.org/wiki/Backronym).

Nymwit is written in [Python](http://www.python.org), using
[Django](http://www.djangoproject.com) and
[MongoEngine](http://mongoengine.org), and uses
[MongoDB](http://www.mongodb.org) for storage.

# Installing & Running

    pip install -u requirements.txt
    python nymwit/manage.py runserver

There is an accompanying Django management command, `gamestate`, which is
designed to be run by cron (or a similar scheduling system) frequently, as
often as once per minute. This command advances the state of Nymwit games
as the states ("playing", "voting") end. Without doing so, a game will
remain in the "playing" state forever.

# License

Nymwit is licensed under a permissive BSD-like license. See LICENSE in this
directory for details. Feel free to fork the project on GitHub; bug fixes,
improvements, and suggestions are always welcome.

