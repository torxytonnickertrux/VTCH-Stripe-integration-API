(() => {
  const dot = document.getElementById('statusDot');
  const latencyEl = document.getElementById('latencyIndicator');
  const titleEl = document.getElementById('heroTitle');
  let glitchTimer = 0;
  function glitchTick() {
    if (!titleEl) return;
    titleEl.classList.add('active');
    setTimeout(() => titleEl.classList.remove('active'), 320);
    const next = 4000 + Math.random() * 5000;
    glitchTimer = setTimeout(glitchTick, next);
  }
  if (titleEl) glitchTimer = setTimeout(glitchTick, 2000);
  async function ping() {
    const t0 = performance.now();
    let ok = false;
    try {
      const res = await fetch('/health', { cache: 'no-store', headers: { 'ngrok-skip-browser-warning': 'true' } });
      ok = res.ok;
    } catch (e) {
      ok = false;
    }
    const dt = Math.max(1, Math.floor(performance.now() - t0));
    if (latencyEl) latencyEl.textContent = 'LAT ' + dt + 'ms';
    if (dot) {
      const speed = Math.max(1, Math.min(3, dt / 250));
      const color = ok ? (dt < 120 ? '#34d399' : dt < 250 ? '#f59e0b' : '#ef4444') : '#ef4444';
      dot.style.animationDuration = (1.2 * speed) + 's';
      dot.style.background = color;
      dot.style.boxShadow = '0 0 10px ' + color;
    }
  }
  function schedulePing() {
    const base = 10000;
    const jitter = 3000 * Math.random();
    setTimeout(() => { ping().then(schedulePing); }, base + jitter);
  }
  schedulePing();
  const mini = document.getElementById('miniMap');
  if (mini) {
    const ctx = mini.getContext('2d');
    function resizeMini() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = mini.clientWidth;
      const h = mini.clientHeight;
      mini.width = Math.floor(w * dpr);
      mini.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resizeMini();
    window.addEventListener('resize', resizeMini);
    let tt = 0;
    function drawMini() {
      tt += 16;
      const w = mini.clientWidth;
      const h = mini.clientHeight;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(17,24,39,.85)';
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = 'rgba(31,41,55,.6)';
      for (let x = 0; x < w; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += 24) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      ctx.fillStyle = 'rgba(52,211,153,.8)';
      for (let i = 0; i < 8; i++) {
        const x = (i * 28 + tt * 0.15) % w;
        const y = (Math.sin((i * 0.6 + tt * 0.005)) * 0.5 + 0.5) * h;
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();
      }
      requestAnimationFrame(drawMini);
    }
    requestAnimationFrame(drawMini);
  }
})();
