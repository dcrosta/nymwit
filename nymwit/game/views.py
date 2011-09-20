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

import cgi
from datetime import datetime, timedelta
import json
from pytz import utc
import random
import re
import time

from django.core.urlresolvers import reverse
from django.contrib.messages import add_message, SUCCESS, ERROR
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import Http404
from mongoengine.django.shortcuts import get_document_or_404

from game.models import Game, Leaderboard
from game.forms import *
from game.templatetags.game import gametime
from util import *


def index(request):
    your_games = []
    if request.user and request.user.is_authenticated():
        your_games = Game.active(players=request.user.username)
        other_games = Game.active.filter(players__nin=[request.user.username])
        other_games = other_games.count()
    else:
        other_games = Game.active.count()

    return render(request, 'index.html',
        your_games=your_games,
        other_games=other_games
    )

@login_required
def new_game(request):
    form = GameForm()

    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            g = Game()
            g.acronym = form.get_acronym()
            g.max_players = int(form.cleaned_data['max_players'])
            g.minutes_per_round = int(form.cleaned_data['minutes_per_round'])
            g.save()
            g.add_player(request.user)

            return redirect('game.views.game', g.pk)

    return render(request, 'new_game.html', form=form)

def game(request, game_id):
    game = get_document_or_404(Game, pk=game_id)

    play_form = None
    vote_form = None
    initial = {}

    if game.state == 'playing':
        play = game.your_play(request.user)
        if play:
            initial['entry'] = play.entry
        play_form = PlayForm(game=game, initial=initial)
        if request.method == 'POST':
            play_form = PlayForm(request.POST, game=game)
            if play_form.is_valid():
                entry = play_form.cleaned_data['entry']
                game.record_play(request.user, entry)
                add_message(request, SUCCESS, 'Got it. You can change your entry until voting begins.')
                return redirect('game.views.game', game.pk)

    elif game.state == 'voting':
        entries = [(i, play.entry) for i, play in enumerate(game.plays)
                   if play.username != request.user.username]
        vote = game.your_vote(request.user)
        if vote:
            initial['entry'] = vote.index
        vote_form = VoteForm(entries=entries, game=game, initial=initial)
        if request.method == 'POST':
            vote_form = VoteForm(request.POST, entries=entries, game=game)
            if vote_form.is_valid():
                vote_index = vote_form.cleaned_data['entry']
                for_username = game.plays[vote_index].username
                game.record_upvote(request.user, for_username)
                add_message(request, SUCCESS, 'Got it. You can change your vote until voting ends.')
                return redirect('game.views.game', game.pk)

    chat_form = ChatForm(game=game)
    return render(request, 'game.html',
                  game=game,
                  play_form=play_form,
                  vote_form=vote_form,
                  chat_form=chat_form,
                  chatlog_json=json.dumps(_chatlog_json(game)))

def _chatlog_json(game, since_timestamp=0):
    messages = []
    for chat in game.chat:
        timestamp = utctimestamp(chat.datetime)
        if timestamp > since_timestamp:
            messages.append({
                't': timestamp,
                'u': chat.username,
                'l': reverse('account.views.profile', args=[chat.username]),
                'm': cgi.escape(chat.message),
            })
    return messages

@login_required
def chat(request, game_id):
    game = get_document_or_404(Game, pk=game_id)
    if request.method == 'POST':
        chat_form = ChatForm(request.POST, game=game)
        if chat_form.is_valid():
            message = chat_form.cleaned_data['message']
            game.add_chat(request.user, message)

    return redirect('game.views.game', game_id)

@login_required
def join(request, game_id):
    game = get_document_or_404(Game, pk=game_id)

    random_join = request.session.pop('join_auto', None)

    status = game.add_player(request.user)
    if status in ('ok', 'duplicate'):
        add_message(request, SUCCESS, "Great, you're in.")
    elif status == 'toomany':
        if random_join and random_join == game.pk:
            # we tried to join a game which became
            # full by the time we tried to join it
            return redirect('game.views.join_random')
        add_message(request, ERROR, "Sorry, this game is full :-(")
    else:
        add_message(request, ERROR, "Sorry, you can't join this game :-(")

    return redirect('game.views.game', game.pk)

@login_required
def join_random(request):
    games = Game.objects(players__ne=request.user.username, state='playing')
    games.where('this[~num_players] < this[~max_players]')
    games.order_by('next_ending').limit(1)
    for game in games:
        request.session['join_auto'] = game.pk
        return redirect('game.views.join', game.pk)
    else:
        return render(request, 'nogames.html')

def random_game(request):
    n = min(Game.active.count(), 100)
    if n == 0:
        return render(request, 'nogames.html')

    game = Game.active.skip(random.randint(0, n - 1)).limit(1).only('pk').first()
    return redirect('game.views.game', game.pk)

def heartbeat(request, game_id):
    game = get_document_or_404(Game, pk=game_id)
    if request.method == 'GET' and 'application/json' in request.META['HTTP_ACCEPT']:
        since_timestamp = int(request.GET.get('since', 0))
        chatlog = _chatlog_json(game, since_timestamp)
        out = {
            'state': game.state,
            'nice_state': gametime(game),
            'next_ending': utctimestamp(game.next_ending),
            'chat': chatlog,
            'players': filter(lambda x: x != request.user.username, game.players),
        }
        return HttpResponse(json.dumps(out), mimetype='application/json')

    return redirect('game.views.game', game.pk)

def time_period(window, key):
    if key == None:
        return None

    if window == 'y':
        return key

    elif window == 'm':
        year, month = int(key[:4]), int(key[4:])
        month = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
                 'August', 'September', 'October', 'November', 'December')[month - 1]
        return '%s %s' % (month, year)

    elif window == 'w':
        weeknum = int(key)
        weekstart = datetime(1970, 1, 4, tzinfo=utc)
        weekstart += timedelta(days=weeknum * 7)
        weekend = weekstart + timedelta(days=6)

        if weekstart.month == weekend.month:
            start = weekstart.strftime('%B %d')
            end = weekend.strftime('%d, %Y')
        elif weekstart.year == weekend.year:
            start = weekstart.strftime('%B %d')
            end = weekend.strftime('%B %d, %Y')
        else:
            start = weekstart.strftime('%B %d, %Y')
            end = weekend.strftime('%B %d, %Y')

        time_period = '%s - %s' % (start, end)
        time_period = re.sub(r' 0(\d)', r' \1', time_period)
        return time_period

def leaderboard(request, window, key):
    url_window = window
    window_name = {
        'y': 'For',
        'm': 'For the month of',
        'w': 'For the week of',
        'a': 'For all time',
    }

    now = datetime.now(utc)

    if window == 'all':
        window = 'a'
        key = ''
        prev, next = None, None

    elif window == 'year':
        window = 'y'
        if key is None:
            key = now.strftime('%Y')

        if int(key) <= 0:
            raise Http404()

        prev, next = int(key) - 1, int(key) + 1

    elif window == 'month':
        window = 'm'
        if key is None:
            key = now.strftime('%Y%m')

        year, month = int(key[:4]), int(key[4:])
        if year <= 0 or month <= 0 or month > 12:
            raise Http404()

        if month == 1:
            prev = '%d%02d' % (year - 1, 12)
            next = '%d%02d' % (year, month + 1)
        elif month == 12:
            prev = '%d%02d' % (year, month - 1)
            next = '%d%02d' % (year + 1, 1)
        else:
            prev = '%d%02d' % (year, month - 1)
            next = '%d%02d' % (year, month + 1)

    elif window == 'week':
        window = 'w'
        if key is None:
            key = Leaderboard.weeknum(now)

        if int(key) <= 0:
            raise Http404()

        prev, next = int(key) - 1, int(key) + 1


    prev = Leaderboard.exists(window, prev) and prev or None
    next = Leaderboard.exists(window, next) and next or None

    if not Leaderboard.exists(window, key):
        return render(request, 'no_leaderboard.html',
                      window_name=window_name.get(window),
                      time_period=time_period(window, key),
                     )

    leaders = Leaderboard.leaders(window, key)

    rank = None
    if request.user.is_authenticated():
        rank = Leaderboard.rank(window, key, request.user.username)

    return render(request, 'leaderboard.html',
                  leaders=leaders,
                  rank=rank,
                  window_name=window_name.get(window),
                  time_period=time_period(window, key),
                  url_window=url_window,
                  prev=prev,
                  prev_time_period=time_period(window, prev),
                  next=next,
                  next_time_period=time_period(window, next),
                 )

