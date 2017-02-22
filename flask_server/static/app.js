if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
}

document.addEventListener("DOMContentLoaded", function() {
    var el = document.getElementById('day' + new Date().getDay());
    if (el) {
        setTimeout(function() {
            el.scrollIntoView();
        }, 50);
    }
}, false);
