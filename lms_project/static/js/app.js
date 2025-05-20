// static/js/app.js

document.addEventListener('DOMContentLoaded', () => {
  console.log(">>> app.js: start");

  /* ==========================================================
   * 1.  Уведомления (Bootstrap off-canvas)
   * ========================================================== */
  const offcanvasEl = document.getElementById('notifOffcanvas');

  if (offcanvasEl) {
    // событие fires, когда панель полностью открыта
    offcanvasEl.addEventListener('shown.bs.offcanvas', () => {
      const url = offcanvasEl.dataset.markReadUrl;
      if (!url) return;

      fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken'      : getCookie('csrftoken'),
          'X-Requested-With' : 'XMLHttpRequest',
        },
      })
      .then(r => (r.ok ? r.json() : Promise.reject(r)))
      .then(data => {
        console.log(`Помечено прочитанными: ${data.marked}`);
        const badge = document.querySelector('#notif-btn .badge');
        if (badge) badge.remove();          // убираем красный счётчик
      })
      .catch(err => console.error('notif error:', err));
    });
  }

  // --- Video progress & resume ---
  console.log("→ video progress script loaded");

  document.querySelectorAll('video[data-video-id]').forEach(video => {
    const vid       = video.dataset.videoId;
    let lastPct     = parseFloat(video.dataset.watchedPercent) || 0;

    console.log(`Video ${vid}: restored lastPct=${lastPct}%`);

    // 1) После загрузки метаданных — всегда прыгаем на lastPct
    video.addEventListener('loadedmetadata', () => {
      if (lastPct > 0 && video.duration) {
        const seekTime = video.duration * (lastPct / 100);
        video.currentTime = seekTime;
        console.log(`  seek to ${seekTime.toFixed(1)}s`);
      } else {
        console.log("  start at 0s");
      }
    }, { once: true });

    // 2) Каждые 5 секунд (пока видео играет) отправляем прогресс
    const ticker = setInterval(() => {
      if (video.paused || video.ended || !video.duration) return;

      // вычисляем процент с точностью до десятых
      const rawPct = (video.currentTime / video.duration) * 100;
      const pct    = parseFloat(rawPct.toFixed(1));

      if (pct <= lastPct) return;
      lastPct = pct;
      console.log(`  sendProgress vid=${vid}: ${pct}%`);

      fetch(`/content/videos/${vid}/progress/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ percent: pct })
      })
      .then(r => r.ok ? r.json() : Promise.reject(`Status ${r.status}`))
      .then(data => {
        console.log(`  saved: ${data.watched_percent}% viewed=${data.viewed}`);
      })
      .catch(err => console.error(`  progress error:`, err));
    }, 5000);

    // 3) При окончании видео — принудительно отправляем 100%
    video.addEventListener('ended', () => {
      lastPct = 100.0;
      console.log("  video ended — force send 100%");
      fetch(`/content/videos/${vid}/progress/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ percent: 100.0 })
      })
      .then(r => r.ok ? r.json() : Promise.reject(`Status ${r.status}`))
      .then(data => {
        console.log(`  saved final: ${data.watched_percent}% viewed=${data.viewed}`);
      })
      .catch(err => console.error(`  final save error:`, err));
    });
  });

  console.log(">>> app.js: end");

  // --- CSRF helper ---
  function getCookie(name) {
    let value = null;
    if (document.cookie && document.cookie !== '') {
      document.cookie.split(';').forEach(c => {
        const [k, v] = c.trim().split('=');
        if (k === name) value = decodeURIComponent(v);
      });
    }
    return value;
  }
});
