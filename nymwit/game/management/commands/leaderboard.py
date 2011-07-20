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

from datetime import datetime, timedelta
from logging import getLogger
from pytz import utc
import sys
import time

from django.core.management.base import NoArgsCommand
from mongoengine import Document
from mongoengine import fields
from bson.code import Code
from pymongo.errors import OperationFailure
from pymongo import ASCENDING, DESCENDING

from game.models import Game
from game.models import Leaderboard

log = getLogger('jobs.leaderboard')

class Command(NoArgsCommand):
    args = ''
    help = 'Updates the leaderboard based on games finished since the last run'

    map_func = Code("""
        function() {
            var next_ending = this.next_ending;

            var year = next_ending.getFullYear();
            var month = next_ending.getMonth() + 1;
            month = month < 10 ? "0" + month : "" + month;

            // weeknum is the whole number of weeks since
            // Jan 4, 1970 at midnight, a Sunday; 277200000
            // is milliseconds since midnight Jan 1 1970
            var weeknum = Math.floor(((next_ending - 277200000) / 86400000) / 7);

            var plays = this.plays;
            for (var i=0; i<plays.length; i++) {
                var play = plays[i];
                var score = play.upvotes.length;
                var doc = {};
                doc["a"] = score;
                doc["y" + year] = score;
                doc["m" + year + month] = score;
                doc["w" + weeknum] = score;
                emit(play.username, doc);
            }
        }
        """)

    reduce_func = Code("""
        function(key, values) {
            var out = {};
            for (var i=0; i<values.length; i++) {
                var doc = values[i];
                for (var k in doc) {
                    if (!doc.hasOwnProperty(k))
                        continue;
                    out[k] = (out[k] || 0) + doc[k];
                }
            }
            return out;
        }
        """)

    def ensure_indices(self, leaderboard, date):
        year_key = date.strftime('value.y%Y')
        month_key = date.strftime('value.m%Y%m')
        week_key = 'value.w%s' % Leaderboard.weeknum(date)

        log.info('ensuring indices: %s %s %s', year_key, month_key, week_key)

        leaderboard.ensure_index([
            (year_key, DESCENDING),
            ('_id', ASCENDING)
        ], sparse=True)
        leaderboard.ensure_index([
            (month_key, DESCENDING),
            ('_id', ASCENDING)
        ], sparse=True)
        leaderboard.ensure_index([
            (week_key, DESCENDING),
            ('_id', ASCENDING)
        ], sparse=True)
        leaderboard.ensure_index([
            ('a', DESCENDING),
            ('_id', ASCENDING)
        ])


    def handle_noargs(self, **options):
        now = datetime.now(utc)

        leaderboard = Leaderboard.objects._collection
        bookkeeping = leaderboard.bookkeeping

        # acquire the "lock" to prevent (potential) other m-r
        # jobs on leaderboard from running concurrently
        try:
            lock = bookkeeping.find_and_modify(
                query={'_id': 1, 'locked': False},
                update={'$set': {'locked': True, 'started_at': now}},
                upsert=True,
                new=True)
        except OperationFailure:
            lock = bookkeeping.find_one()
            diff = (now - lock['started_at']).seconds
            if 300 < diff and diff < 600:
                log.info("another leaderboard job running for more than 5 minutes")
            elif 600 < diff:
                log.warning("another leaderboard job running for more than 10 minutes")
            sys.exit(1)

        try:
            # find the last updated date in the leaderboard,
            # or the earliest finished game if no leaderboard
            # entries exist yet
            start = lock.get('last_update')
            if not start:
                log.debug('running first time')
                first_game = Game.objects(state='finished')
                first_game = first_game.order_by('next_ending').first()

                if first_game:
                    start = first_game.next_ending
                else:
                    start = datetime.now(utc)

            end = datetime.now(utc)

            if end > start:
                log.info('map-reduce %s to %s', start, end)
                Game.objects._collection.map_reduce(
                    map=self.map_func,
                    reduce=self.reduce_func,
                    out=leaderboard.name,
                    reduce_output=True,
                    query=Game.objects(
                        state='finished',
                        next_ending__gte=start,
                        next_ending__lt=end)._query
                )

                # iterate each week between start and
                # end, and ensure indices exist on all
                # the score fields that they should
                for d in range(0, (end - start).days + 6, 7):
                    self.ensure_indices(leaderboard, start + timedelta(days=d))
            else:
                log.info('nothing to map-reduce')

        except:
            log.exception('error during leaderboard map-reduce')

        finally:
            finish = datetime.now(utc)
            diff = finish - now
            diff = 86400 * diff.days + diff.seconds
            log.info('finished, took %ss', diff)
            bookkeeping.find_and_modify(
                query={'_id': 1},
                update={'$set': {'locked': False, 'last_update': end}})

