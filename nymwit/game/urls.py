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

from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('game.views',
    url(r'^$', 'index'),

    url(r'^game/$', 'random_game'),
    url(r'^game/join/$', 'join_random'),
    url(r'^game/new/$', 'new_game'),

    url(r'^game/(?P<game_id>[0-9a-f]+)/$', 'game'),
    url(r'^game/(?P<game_id>[0-9a-f]+)/join/$', 'join'),
    url(r'^game/(?P<game_id>[0-9a-f]+)/chat/$', 'chat'),
    url(r'^game/(?P<game_id>[0-9a-f]+)/heartbeat/$', 'heartbeat'),

    url(r'^leaderboard/$', 'leaderboard', {'window': 'all', 'key': None}, name='game.views.leaderboard_all'),
    url(r'^leaderboard/(?P<window>year|month|week)/$', 'leaderboard', {'key': None}, name='game.views.leaderboard_window'),
    url(r'^leaderboard/(?P<window>year|month|week)/(?P<key>\d{4}|\d{6})/$', 'leaderboard'),
)

