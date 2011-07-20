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

__all__ = ('GameForm', 'PlayForm', 'ChatForm', 'VoteForm')

import random

from django import forms
from django.forms import widgets
from django.conf import settings
from django.core.urlresolvers import reverse
from mongoforms import MongoForm
from mongoforms.fields import ReferenceField

from mongoengine.django.auth import User
from models import Game

# cumulative distribution of initial letter frequency in english,
# according to http://en.wikipedia.org/wiki/Letter_frequency;
letter_dist = (
    ('A', 0.11602), ('B', 0.16304), ('C', 0.19815), ('D', 0.22485),
    ('E', 0.24485), ('F', 0.28264), ('G', 0.30214), ('H', 0.37446),
    ('I', 0.43732), ('J', 0.44363), ('K', 0.45053), ('L', 0.47758),
    ('M', 0.52132), ('N', 0.54497), ('O', 0.60761), ('P', 0.63307),
    ('Q', 0.63480), ('R', 0.65132), ('S', 0.72887), ('T', 0.89558),
    ('U', 0.91045), ('V', 0.91664), ('W', 0.98325), ('X', 0.98330),
    ('Y', 0.99950), ('Z', 1.00000)
)

def letter():
    r = random.random()
    for letter, freq in letter_dist:
        out = letter
        if r <= freq:
            break
    return out

def make_acronym(length):
    return ''.join(letter() for x in range(length))

shortest = 4
longest = 7
lengths = range(shortest, longest + 1)
length_choices = zip(lengths, lengths)

minutes_choices = [
    (10, '10 Minutes'),
    (20, '20 Minutes'),
    (30, '30 Minutes'),
    (60, '1 Hour'),
    (120, '2 Hours'),
    (360, '6 Hours'),
    (720, '12 Hours'),
    (1440, '1 Day'),
]

players_choices = [(i, str(i)) for i in xrange(5, 16)]

class GameForm(forms.Form):
    length = forms.ChoiceField(
        choices=length_choices, initial=6,
        label='Acronym Length')
    minutes_per_round = forms.ChoiceField(choices=minutes_choices, initial=120)
    max_players = forms.ChoiceField(choices=players_choices, initial=10)

    def get_acronym(self):
        if not hasattr(self, 'cleaned_data') or 'length' not in self.cleaned_data:
            return None

        if not hasattr(self, '_acronym'):
            length = int(self.cleaned_data['length'])
            self._acronym = make_acronym(length)

        return self._acronym

class PlayForm(forms.Form):
    entry = forms.CharField(required=True, label='Your Entry')

    def __init__(self, *args, **kwargs):
        self._game = kwargs.pop('game')
        super(PlayForm, self).__init__(*args, **kwargs)

    def clean(self):
        try:
            entry = self.cleaned_data['entry']
        except:
            raise forms.ValidationError('Ooops! Something went wrong :-(')

        if not self._game.entry_is_valid(entry):
            raise forms.ValidationError("Your entry doesn't match the acronym!")

        return self.cleaned_data

class VoteForm(forms.Form):
    entry = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        self._game = kwargs.pop('game')
        entries = kwargs.pop('entries', [])
        super(VoteForm, self).__init__(*args, **kwargs)
        self.fields['entry'].choices = [('', 'Choose an entry')] + entries

    def clean_entry(self):
        try:
            entry = int(self.cleaned_data['entry'])
            assert entry >= 0
            assert entry <= len(self._game.plays)
            return entry
        except:
            raise forms.ValidationError('This field is required')

class ChatForm(forms.Form):
    message = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        self._game = kwargs.pop('game')
        super(ChatForm, self).__init__(*args, **kwargs)

    @property
    def action(self):
        # used by _form.html to submit to a different
        # URL than the page in which it is displayed
        return reverse('game.views.chat', args=[self._game.pk])

