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

import sys
from pytz import utc
from logging import getLogger

from datetime import datetime, timedelta
from django.core.management.base import NoArgsCommand

from game.models import Game

log = getLogger('job.advancegamestate')

class Command(NoArgsCommand):
    args = ''
    help = 'Advances game state from "playing" to "voting" to "finished" as necessary for active games'

    def handle_noargs(self, **options):
        games = Game.objects(state__in=('playing', 'voting'), next_ending__lte=datetime.now(utc))
        for game in games:
            if game.state == 'playing':
                if game.num_players < 2:
                    game.update(set__state='invalid')
                    log.debug('advanced game %s from playing to invalid, only %d players', game.pk, game.num_players)
                else:
                    new_next_ending = game.next_ending + timedelta(minutes=game.minutes_per_round)
                    game.update(set__state='voting', set__next_ending=new_next_ending)
                    log.debug('advanced game %s from playing to voting, next ending %s', game.pk, new_next_ending)
            elif game.state == 'voting':
                total_votes = sum(len(play.upvotes) for play in game.plays)
                if total_votes == 0:
                    game.update(set__state='invalid')
                    log.debug('advanced game %s from voting to invalid, 0 votes', game.pk)
                else:
                    game.update(set__state='finished')
                log.debug('advanced game %s from voting to finished', game.pk)

