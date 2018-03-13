$(document).on('keypress', 'input', function (e) {
    if(e.which == 13) {
        $(this).trigger('change');
    }
});