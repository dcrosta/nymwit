# Copyright (c) 2011, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re
from datetime import datetime, timedelta
from pytz import utc
import time

from mongoengine import Document
from mongoengine import EmbeddedDocument
from mongoengine import fields
from mongoengine.queryset import queryset_manager

punctuation = re.compile(r'[^a-zA-Z0-9 ]')

class Play(EmbeddedDocument):
    username = fields.StringField()
    entry = fields.StringField()
    upvotes = fields.ListField(fields.StringField())

class Chat(EmbeddedDocument):
    datetime = fields.DateTimeField()
    username = fields.StringField()
    message = fields.StringField()

class Game(Document):

    @queryset_manager
    def active(doc_cls, queryset):
        # works like Game.objects, but only
        # shows still-active games
        queryset.filter(state__in=('playing', 'voting'))
        return queryset

    # state is 'playing', 'voting', or 'finished', or 'invalid'
    #
    # a game is marked 'invalid' if the playing round ends with
    # fewer than 3 players (and thus there is no point in voting),
    # of if the voting round ends with 0 votes
    state = fields.StringField(default='playing')

    acronym = fields.StringField()

    # when does the current state end?
    next_ending = fields.DateTimeField()
    minutes_per_round = fields.IntField(default=120)

    # game chat
    chat = fields.ListField(fields.EmbeddedDocumentField('Chat'))

    # list of plays in this game; see class Play
    plays = fields.ListField(fields.EmbeddedDocumentField('Play'))

    # list of players' usernames
    players = fields.ListField(fields.StringField())
    num_players = fields.IntField(default=0)
    max_players = fields.IntField(default=10)

    meta = {
        'indexes': [
            {'fields': ['players', 'state']},
            {'fields': ['state', 'next_ending']},
        ]
    }

    def __unicode__(self):
        return unicode(self.pk)

    def save(self):
        if self.next_ending is None:
            self.next_ending = datetime.now(utc)
            self.next_ending += timedelta(minutes=self.minutes_per_round)
        super(Game, self).save()

    # biz logic methods. note that these DO NOT update
    # the internal state of the instance on which they
    # are called; use .reload() for that if necessary

    def add_chat(self, player, message):
        c = Chat()
        c.username = player.username
        c.datetime = datetime.now(utc)
        c.message = message
        self.update(push__chat=c)

    def add_player(self, player):
        # attempt to add the given player to the Game, and
        # return True on success, or False on failure (a
        # race condition exists where more players than
        # max_players can be added; if so, this attempt
        # to add the player fails)
        username = player.username
        if username in self.players:
            return 'duplicate'
        if self.num_players >= self.max_players:
            return 'toomany'
        self.update(push__players=username, inc__num_players=1)
        newself = Game.objects(pk=self.pk).only('num_players').first()
        if newself.num_players > self.max_players:
            # race condition happened, roll back
            self.update(pull__players=username, inc__num_players=-1)
            return 'toomany'
        return 'ok'

    def entry_is_valid(self, entry):
        entry = punctuation.sub('', entry)
        words = [w.strip() for w in entry.split(' ') if w.strip() != '']
        if len(words) != len(self.acronym):
            return False

        for letter, word in zip(self.acronym, words):
            if letter != word[0].upper():
                return False

        return True

    def record_play(self, by_player, entry):
        # attempt to record a play by a player. the
        # player must not have already played, and
        # must be in the list of players, and the
        # entry must match self.acronym. return
        # True on success, otherwise False
        if by_player.username not in self.players:
            return False
        if not self.entry_is_valid(entry):
            return False
        existing = self.your_play(by_player)
        if existing:
            # update existing play
            key = 'set__plays__%d__entry' % existing.index
            kwargs = {key: entry}
            self.update(**kwargs)
        else:
            play = Play()
            play.username = by_player.username
            play.entry = entry
            self.update(push__plays=play)
        return True

    def record_upvote(self, by_player, for_username):
        # attempt to record an upvote by one player
        # for another player. the two players must
        # be different, and the voting player must
        # not have already voted. return True if
        # the upvote succeeded, or False otherwise
        if by_player.username == for_username:
            return False

        # remove any other upvotes from this player
        # (there are at most 1)

        pull = None
        push = None
        for i, play in enumerate(self.plays):
            if play.username == for_username:
                push = i
            if by_player.username in play.upvotes:
                pull = i

        if push == pull:
            # either voting for the same entry, or
            # both are None; return True or False
            # accordingly
            return push is not None

        if pull is not None:
            key = 'pull__plays__%d__upvotes' % pull
            kwargs = {key: by_player.username}
            self.update(**kwargs)

        key = 'push__plays__%d__upvotes' % push
        kwargs = {key: by_player.username}
        self.update(**kwargs)

        return True

    def your_play(self, by_player):
        for i, play in enumerate(self.plays):
            if play.username == by_player.username:
                play.index = i
                return play
        return None

    def your_vote(self, by_player):
        for i, play in enumerate(self.plays):
            if by_player.username in play.upvotes:
                play.index = i
                return play
        return None

class Leaderboard(Document):
    # documents in this collection are created by the
    # map-reduce job in management/commands/leaderboard.py
    #
    # they should always be queried by one of the indices.
    # there will be many, of the form "yYYYY", "mYYYY-MM",
    # or "wYYYY-WW" where YYYY is current year or earlier,
    # MM is a 00 - 12, and MM is 00-52 (or sometimes 53).
    # furthermore, to make best use of the indices, always
    # select only fields 'username', and the name of the
    # indexed score field (this will ensure use of the
    # covered index)

    username = fields.StringField(db_field='_id')
    scores = fields.DictField(db_field='value')

    meta = {
        'allow_inheritance': False,
        'id_field': 'username',
    }

    @staticmethod
    def weeknum(dt):
        return (dt - datetime(1970, 1, 4, tzinfo=utc)).days / 7

    __index_cache = set()
    __index_cache_time = None

    @classmethod
    def __index_exists(cls, window, key):
        if not cls.__index_cache_time or (time.time() - cls.__index_cache_time) > 60:
            info = cls.objects._collection.index_information()
            cls.__index_cache.clear()
            cls.__index_cache.update(info.keys())
            cls.__index_cache_time = time.time()
        index_name = '%s.%s%s_-1__id_1' % (cls.scores.db_field, window, key)
        return index_name in cls.__index_cache

    @classmethod
    def exists(cls, window, key):
        return cls.__index_exists(window, key)

    @classmethod
    def leaders(cls, window, key, n=20):
        # generate a list of tuples of (username, score),
        # in rank order, of top-scoring users during the
        # given time period
        if not cls.__index_exists(window, key):
            raise StopIteration()

        indexbase = '%s%s' % (window, key)
        index = 'scores.%s' % indexbase
        leaders = cls.objects.order_by('-' + index).only(index, 'username')
        for l in leaders[:n]:
            yield (l.username, int(l.scores.get(indexbase, 0)))

    @classmethod
    def rank(cls, window, key, username):
        # determine the rank, if any, of the user during
        # the given time period, or None if the user did
        # not play during that time
        indexbase = '%s%s' % (window, key)
        index = 'scores.%s' % indexbase
        score = cls.objects(username=username)
        score = score.only(index).first()
        if score:
            score = score.scores.get(indexbase)
        if score:
            query = {index.replace('.', '__') + '__gt': score}
            return Leaderboard.objects(**query).order_by('-' + index).count() + 1
        return None

