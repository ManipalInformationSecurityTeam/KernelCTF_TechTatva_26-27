
function updateClock() {
    const now = new Date();
    document.getElementById('utc-clock').innerText = 'UTC ' + now.toISOString().substring(11, 19);
}
setInterval(updateClock, 1000); updateClock();
