(() => {
  const canvas = document.getElementById('heroCanvas');
  const ctx = canvas.getContext('2d');
  let w = 0, h = 0, t = 0;
  function resize() {
    const parent = canvas.parentElement || document.body;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = parent.clientWidth || window.innerWidth;
    const ch = parent.clientHeight || window.innerHeight;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    canvas.width = Math.floor(cw * dpr);
    canvas.height = Math.floor(ch * dpr);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    w = cw;
    h = ch;
  }
  resize();
  window.addEventListener('resize', resize);
  function rnd(a, b) { return a + Math.random() * (b - a) }
  function drawGrid() {
    const spacing = 80;
    ctx.strokeStyle = 'rgba(31,41,55,0.35)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += spacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += spacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
  }
  function drawScanlines() {
    const lines = 18;
    for (let i = 0; i < lines; i++) {
      const y = (t * 0.6 + i * (h / lines)) % h;
      const g = ctx.createLinearGradient(0, y - 30, 0, y + 30);
      g.addColorStop(0, 'rgba(52, 211, 153, 0)');
      g.addColorStop(0.5, 'rgba(52, 211, 153, 0.12)');
      g.addColorStop(1, 'rgba(52, 211, 153, 0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, y - 30, w, 60);
    }
  }
  function drawNodes() {
    const count = 60;
    ctx.fillStyle = 'rgba(52,211,153,0.5)';
    for (let i = 0; i < count; i++) {
      const x = (i * 73 + t * 0.9) % w;
      const y = (Math.sin((i * 0.003 + t * 0.0005)) * 0.5 + 0.5) * h;
      ctx.beginPath();
      ctx.arc(x, y, 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  let last = performance.now();
  function frame(now) {
    const dt = now - last;
    last = now;
    t += dt;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0b0d0f';
    ctx.fillRect(0, 0, w, h);
    drawGrid();
    drawScanlines();
    drawNodes();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
