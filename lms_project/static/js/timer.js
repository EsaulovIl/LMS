// static/js/timer.js
document.addEventListener('DOMContentLoaded', function() {
  const timerEl = document.querySelector('[data-timer]');
  if (!timerEl) return;

  // читаем время и URL для редиректа
  let timeLeft = parseInt(timerEl.dataset.timeLeft, 10);
  const finishUrl = timerEl.dataset.finishUrl;
  const display = timerEl.querySelector('[data-time-display]');

  function formatTime(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return String(h).padStart(2, '0')
         + ':' + String(m).padStart(2, '0')
         + ':' + String(s).padStart(2, '0');
  }

  function tick() {
    if (timeLeft <= 0) {
      display.textContent = '00:00:00';
      if (finishUrl) window.location.href = finishUrl;
      clearInterval(intervalId);
      return;
    }
    display.textContent = formatTime(timeLeft);
    timeLeft--;
  }

  // первый рендер и интервал
  tick();
  const intervalId = setInterval(tick, 1000);
});
