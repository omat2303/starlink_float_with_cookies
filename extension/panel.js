// Botón que aparece sobre el panel: pide la cookie a la extensión, sincroniza y
// recarga. El sync lo hace la pestaña (no el service worker) porque tarda minutos
// y el service worker de MV3 se muere a los ~30s.
const btn = document.createElement('button');
btn.id = 'starlink-bridge';
btn.textContent = 'Traer cookie y sincronizar';
btn.style.cssText = [
  'position:fixed', 'right:16px', 'bottom:16px', 'z-index:9999',
  'padding:10px 14px', 'border-radius:8px', 'border:0', 'cursor:pointer',
  'background:#2563eb', 'color:#fff', 'font-size:13px',
  'box-shadow:0 2px 8px rgba(0,0,0,.35)',
].join(';');

btn.onclick = async () => {
  btn.disabled = true;
  btn.textContent = 'Enviando cookie…';
  try {
    const sent = await chrome.runtime.sendMessage({ type: 'send-starlink-cookies' });
    if (!sent?.ok) throw new Error(sent?.error || 'no se pudo enviar la cookie');

    btn.textContent = 'Sincronizando…';
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'X-Requested-With': 'starpanel' },
    });
    if (!res.ok) throw new Error(`sync HTTP ${res.status}`);

    btn.textContent = 'Listo, recargando…';
    location.reload();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Falló. Reintentar';
    console.error('StarPanel:', err);
  }
};

document.body.appendChild(btn);
