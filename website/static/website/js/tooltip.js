function ajaxTooltip(el_id, el_type, tooltip_id, el, url){
    var prefix = '#' + el_type + '-'
    if(!$(prefix + tooltip_id).html().includes('Loading')){
        return;
    }
    $(el).addClass('in-check')
    $.ajax({
        url: url,
        type: "GET",
        success: function(response) {
            $(prefix + tooltip_id).html(response)
            $(el).attr("data-original-title", response)
            if($(el).hasClass('in-check')){
                $(el).tooltip('show');
            }
        },
        error: function(xhr) {
            $('#content-ajax-container').html("{% include 'website/error.html' with task_id='' %}");
        }
    });
}

function ajaxTooltipLeave(el){
    $(el).removeClass('in-check')
}

function initTableTooltips(){
    $('.tip').each(function () {
        $(this).tooltip(
        {
            html: true,
            placement: 'top',
            title: $('#' + $(this).data('tip')).html(),
            boundary: "window",
            container: 'body',
        });
    });
}