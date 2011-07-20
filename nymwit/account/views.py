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

from django.contrib import auth
from django.contrib.auth.views import login, logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from mongoengine.django.auth import User
from mongoengine.django.shortcuts import get_document_or_404

from forms import *
from game.models import Game
from mongoengine.django.auth import User


def render(request, template_name, **kwargs):
    return render_to_response(template_name, kwargs, RequestContext(request))

def redirect(view_name, *args):
    return HttpResponseRedirect(reverse(view_name, args=args))


def signup(request):
    if request.method == 'GET':
        form = SignupForm()

    elif request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                user = auth.authenticate(
                    username=user.username,
                    password=user._raw_password)
                auth.login(request, user)
                return redirect('game.views.index')
            except DidntSave:
                pass

    return render(request, 'signup.html', form=form)

def profile(request, username):
    profile = get_document_or_404(User, username=username)

    current = Game.objects(players=profile.username, state__in=('playing', 'voting'))
    current.order_by('next_ending')

    past = Game.objects(players=profile.username, state__in=('invalid', 'finished')).limit(10)
    past.order_by('-next_ending')

    prefs_form = None
    # if profile == request.user:
    #     initial = PreferencesForm.initial_for(profile)
    #     prefs_form = PreferencesForm(initial=initial)

    return render(request, 'profile.html',
                  profile=profile,
                  current=current,
                  past=past,
                  prefs_form=prefs_form)

def profile_redirect(request):
    if not request.user.is_authenticated():
        return redirect('account.views.login')
    return redirect('account.views.profile', request.user.username)
