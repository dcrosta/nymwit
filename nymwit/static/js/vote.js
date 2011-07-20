(function() {

  $(document).ready(function() {
    var html = []
    html[html.length] = '<ul class="entries">';
    $('select#id_entry option').each(function() {
      if (!this.value) {
        html[html.length] = '<li class="instructions">' + this.text + '</li>';
      } else {
        var sel = '';
        if (this.selected)
          sel = ' class="selected"';
        html[html.length] = '<li><label for="' + this.value + '"' + sel + '>' + this.text + '</label></li>';
      }
    });
    html[html.length] = '</ul>';

    $('td#td-entry').append(html.join(''));

    $('ul.entries li label').live('click', function() {
      $('ul.entries li label').removeClass('selected');
      $(this).addClass('selected');
      var forvalue = $(this).attr('for');
      $('select#id_entry option').each(function() {
        this.selected = (this.value == forvalue);
        if (this.selected) console.log(this);
      });
    });
  });
})();

