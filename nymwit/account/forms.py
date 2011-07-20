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

__all__ = ('DidntSave', 'SignupForm', 'PreferencesForm')

from django import forms
from django.forms import widgets
from django.forms import util
from mongoengine.django.auth import User
from mongoforms import MongoForm
from pymongo.errors import OperationFailure
import pytz

class DidntSave(Exception): pass

class SignupForm(MongoForm):
    class Meta:
        document = User
        fields = ('username', 'password')
    password = forms.CharField(widget=widgets.PasswordInput, required=True)
    confirm = forms.CharField(widget=widgets.PasswordInput, required=True)

    def clean(self):
        # ensure passwords match
        clean = self.cleaned_data

        password = 'password' in clean and clean['password'] or None
        confirm = 'confirm' in clean and clean['confirm'] or None

        try:
            password = password.strip()
            confirm = confirm.strip()

            assert password
            assert confirm
            assert password == confirm

            clean['password'] = password
            clean['confirm'] = confirm
        except:
            # raise forms.ValidationError('Passwords did not match')
            self._errors['confirm'] = self.error_class(['Passwords did not match'])

            clean.pop('password', None)
            clean.pop('confirm', None)

        return clean

    def clean_username(self):
        # ensure username is set and unique
        clean = self.cleaned_data
        username = 'username' in clean and clean['username'] or None

        try:
            username = username.strip()
            assert username
            assert 0 == User.objects(username=username).count()
        except:
            raise forms.ValidationError('Username is already in use')

        return username

    def save(self):
        try:
            user = super(SignupForm, self).save()
            user.set_password(self.cleaned_data['password'])
            # used immediately after return from
            # this method to log the new user in
            user._raw_password = self.cleaned_data['password']
            return user
        except OperationFailure:
            # there's a race condition that can cause violations
            # on the unique index on username; if we get such an
            # exception, set an error message and raise
            self._errors['username'] = ['Username is already in use']
            raise DidntSave

class PreferencesForm(forms.Form):
    timezone = forms.ChoiceField(choices=[(i, t) for i, t in
                                          enumerate(pytz.common_timezones)])

    @staticmethod
    def initial_for(user):
        initial = {}
        timezone = getattr(user, 'timezone', 'America/New_York')
        if timezone in pytz.common_timezones:
            initial['timezone'] = pytz.common_timezones.index(timezone)

        return initial

