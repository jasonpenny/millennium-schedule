if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
}

document.addEventListener("DOMContentLoaded", function() {
    var refreshBtn = document.getElementById('refresh-btn');
    refreshBtn.addEventListener('click', function() {
        window.location.reload();
    });

    var el = document.getElementById('day' + new Date().getDay());
    if (el) {
        setTimeout(function() {
            window.scrollTo(0, el.offsetTop - 34); // 2em + 2px (below the header)
        }, 50);
    }
}, false);
