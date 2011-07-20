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

from datetime import datetime
from pytz import utc

from django.conf import settings
from django.utils.timesince import timesince, timeuntil
from django import template
register = template.Library()

@register.filter
def your_play(game, user):
    play = game.your_play(user)
    return play and play.entry or ''

@register.filter
def can_play(game, user):
    if game.state != 'playing':
        return False
    if not user.is_authenticated() or user.username not in game.players:
        return False
    return True

@register.filter
def your_vote(game, user):
    play = game.your_vote(user)
    return play and play.entry or ''

@register.filter
def can_vote(game, user):
    if game.state != 'voting':
        return False
    if not user.is_authenticated() or user.username not in game.players:
        return False
    return True

@register.filter
def has_plays(game):
    return len(game.plays) > 0

@register.filter
def has_votes(game):
    for play in game.plays:
        if play.upvotes:
            return True
    return False

@register.filter
def can_join(game, user):
    return user.is_authenticated() and \
           game.state == 'playing' and \
           user.username not in game.players and \
           game.num_players < game.max_players

@register.filter
def can_chat(game, user):
    return user.is_authenticated() and user.username in game.players

@register.filter
def chat_open(game):
    return game.state in ('playing', 'voting') or (datetime.now(utc) - game.next_ending).seconds < 600

@register.filter
def filterout(sequence, thing):
    return filter(lambda x: x != thing, sequence)

@register.filter
def gametime(game):
    if game.state == 'finished':
        since_str = timesince(game.next_ending)
        # only show the most significant part of
        # the string
        since_str, _, _ = since_str.partition(',')
        return 'Finished %s ago' % since_str.strip()
    elif game.state == 'invalid':
        since_str = timesince(game.next_ending)
        # only show the most significant part of
        # the string
        since_str, _, _ = since_str.partition(',')
        return 'Cancelled %s ago' % since_str.strip()

    until_str = timeuntil(game.next_ending)
    # add "more" just after the first set of digits, so
    # "1 hour, 15 minutes" becomes "1 more hour, 15 minutes"
    num, _, rest = until_str.partition(' ')

    state = game.state[0].upper() + game.state[1:]

    return '%s for %s more %s' % (state, num, rest)

@register.filter
def invalid_reason(game):
    if len(game.players) < 2:
        return 'Too few players'
    elif sum(len(play.upvotes) for play in game.plays) == 0:
        return 'Nobody voted'
    return ''

@register.filter
def setscore(plays):
    for play in plays:
        play.score = len(play.upvotes)
    return plays


@register.tag
def addscript(parser, token):
    try:
        _, script = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])

    if not (script[0] == script[-1] and script[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return AddScriptNode(script[1:-1])

class AddScriptNode(template.Node):
    def __init__(self, script):
        self.script = script
    def render(self, context):
        if not hasattr(context, '_page_scripts'):
            context._page_scripts = ['jquery.js']
        if self.script not in context._page_scripts:
            context._page_scripts.append(self.script)
        return ''

@register.tag
def scripts(parser, token):
    return RenderScriptsNode()

class RenderScriptsNode(template.Node):
    def render(self, context):
        try:
            out = []
            for script in context._page_scripts:
                out.append('<script type="text/javascript" src="%sjs/%s"></script>' % (settings.STATIC_URL, script))
            del context._page_scripts
            return '\n    '.join(out)
        except:
            return ''

