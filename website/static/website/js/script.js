var toggle_menu = setInterval(function (){
    if($('#sidebar-upper').length > 0 && localStorage.getItem('toggled') == "true") { 
        clearInterval(toggle_menu);
        $('#sidebar-upper').addClass('toggled');
        $('#sidebar-lower').addClass('toggled');
    }
},1)

$(document).ready(function () {
    setTimeout(function (){
        clearInterval(toggle_menu);
    },5000);
    $('#sidebar-toggler').on('click', function () {
        $('#sidebar-upper').toggleClass('toggled');
        $('#sidebar-lower').toggleClass('toggled');

        var classList = document.getElementById('sidebar-upper').className.split(/\s+/);
        var toggled = false
        for (var i = 0; i < classList.length; i++) {
            if (classList[i] === 'toggled') {
                toggled = true;
                break;
            }
        }
        localStorage.setItem('toggled', toggled)
    });
});