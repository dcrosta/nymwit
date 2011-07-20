(function() {
  var latest = 0;
  var timeout = null;

  function next_timeout() {
    var diff = (Date.now() / 1000) - latest;
    if (diff < 5) {
      return 1000;
    } else if (diff < 10) {
      return 5000;
    } else if (diff < 20) {
      return 10000;
    } else {
      return 20000;
    }
  }

  function pluralize(n, unit) {
    if (n == 1)
      return n + " " + unit + " ago";
    return n + " " + unit + "s ago";
  }

  function nicetime(timestamp) {
    var now = Math.floor(Date.now() / 1000);
    var then = parseInt(timestamp, 10);
    var diff = Math.max(0, now - then);

    var days = Math.floor(diff / 86400);
    diff -= 86400 * days;
    var hours = Math.floor(diff / 3600);
    diff -= 3600 * hours;
    var minutes = Math.floor(diff / 60);
    var seconds = diff - 60 * minutes;

    if (days == 0 && hours == 0 && minutes == 0) {
      return "just now";
    } else if (days == 0 && hours == 0) {
      return pluralize(minutes, "minute");
    } else if (days == 0) {
      return pluralize(hours, "hour");
    } else if (days < 7) {
      return pluralize(days, "day");
    } else if (days < 30) {
      return pluralize(Math.floor(days / 7), "week");
    } else if (days < 365) {
      return pluralize(Math.floor(days / 30), "month");
    } else {
      return pluralize(Math.floor(days / 365), "year");
    }
  }

  function by_timestamp(a, b) {
    if (a.t < b.t) {
      return -1;
    } else if (b.t < a.t) {
      return 1;
    } else {
      return 0;
    }
  }

  function do_heartbeat() {
    var path = window.location.pathname;
    var url = (/\/$/.test(path) ? path : path + '/') + 'heartbeat/';
    jQuery.getJSON(url, {since: latest}, function(heartbeat) {
      var chat = heartbeat.chat;
      chat.sort(by_timestamp);
      for (var i=0; i<chat.length; i++) {
        var c = chat[i];
        latest = Math.max(latest, c.t);
        prepend(c);
      }
      $('div.chat span.time').each(function() {
        $(this).empty().text(nicetime(this.id));
      });
      $('#gamestate').empty().append(heartbeat.nice_state);
      if (heartbeat.players !== []) {
        $('#with').empty().append('(with ' + heartbeat.players.join(', ') + ')');
      } else {
        $('#with').empty().append('(no other players)');
      }
      if (heartbeat.state !== gamestate) {
        if ($('ul.messages').length == 0) {
          $('#acro').after('<ul class="messages"></ul>');
        }
        var messages = $('ul.messages')
        messages.append('<li class="info generated">Game is now ' + heartbeat.state + '. Please <a href="' + window.location.href + '">reload this page</a>.</li>');
        messages.find('.generated').fadeIn().removeClass('generated');
        gamestate = heartbeat.state;
      }
      timeout = setTimeout(do_heartbeat, next_timeout());
    });
  }

  function prepend(c) {
    $('div.chat').prepend('<div><span class="time" id="' + c.t + '">' + nicetime(c.t) + '</span><span class="author"><a href="' + c.l + '">' + c.u + '</a></span><span class="message">' + c.m + '</span></div>');
  }

  $(document).ready(function() {
    if (chatlog === "undefined") {
      chatlog = []
    }

    chatlog.sort(by_timestamp);
    for (var i=0; i<chatlog.length; i++) {
      var c = chatlog[i];
      latest = Math.max(latest, c.t);
      prepend(c);
    }
    timeout = setTimeout(do_heartbeat, 1000);

    $('#chatform').submit(function(evt) {
      var form = this;
      clearTimeout(timeout);
      timeout = null;
      var url = $(form).attr('action');
      var data = {
        message: $(form).find('#id_message').val(),
        game_id: $(form).find('#id_game_id').val(),
        username: $(form).find('#id_username').val(),
        csrfmiddlewaretoken: $(form).find('[name="csrfmiddlewaretoken"]').val()
      };
      $(form).find('#id_message').attr('disabled', 'disabled');
      jQuery.post(url, data, function() {
        do_heartbeat();
        $(form).find('#id_message').val('').removeAttr('disabled');
      });
      evt.preventDefault();
      return false;
    });
  });

})();
