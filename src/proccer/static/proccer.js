(function() {
    $(document).ready(function() {

        // Updates the text on the roll header.
        // If there are hidden jobs -> '[show all X jobs]'
        // otherwise -> '[hide]'
        var update_text = function(role) {
            if ($(role).find('.job:not(:visible)').length > 0) {
                // if there are hidden objects,
                // set the text to '[show all X jobs]'
                var n_jobs = $(role).find('.job').length;
                $(role).find('.toggle-text').text(
                    '[show all ' + n_jobs +' jobs]');
            } else {
                // if there are not hidden jobs
                $(role).find('.toggle-text').text('[hide]');
            }
        }

        // Hides all jobs with status 'ok' and updates the header text
        var hide_ok = function(role) {
            if ($(role).find('.job:not(.ok)').length == 0) {
                $(role).find('.role-details').hide();
            }
            $(role).find('.job.ok').hide();
            update_text(role);
        }

        // Shows all the jobs and updates the header thext
        var show_ok = function(role) {
            $(role).find('.role-details').show();
            $(role).find('.role-details .job').show();
            update_text(role);
        }

        // shows/hides jobs with status 'ok' with a click on the role header
        $('.role:has(.job.ok) .role-header').click(function() {
            var role = $(this).closest('.role');
            var is_hidden = role.find('.job:hidden').length > 0;

            if (is_hidden) {
                show_ok(role);
            } else {
                hide_ok(role);
            }
        });

        // hide all jobs with status 'ok' by default
        $('.role:has(.job.ok)').each(function(){
            hide_ok(this);
        });

    });
})();
