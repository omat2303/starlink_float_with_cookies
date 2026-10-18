// Toma las cookies de starlink.com del propio Chrome y las manda al backend, que
// las guarda cifradas. Es el único contexto que puede leer cookies HttpOnly: una
// página web (el panel) no puede. Chrome 136+ las cifra con app-bound encryption,
// así que leer el archivo Cookies del disco tampoco sirve.
//
// El backend exige el token de ingesta (X-Ingest-Token), que se pega una vez en
// la página de opciones de la extensión.
// Pon aquí el dominio donde vive tu panel (el repo trae uno de ejemplo).
const LOGIN = 'http://localhost:8000/api/v1/auth/login';

async function ingestToken() {
  const { ingestToken } = await chrome.storage.local.get('ingestToken');
  return ingestToken || '';
}

async function sendCookies() {
  const cookies = await chrome.cookies.getAll({ domain: 'starlink.com' });
  if (!cookies.length) {
    return { ok: false, error: 'No hay cookies de starlink.com en este perfil' };
  }

  const header = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
  const res = await fetch(LOGIN, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Ingest-Token': await ingestToken() },
    body: JSON.stringify({ cookie: header }),
  });
  return res.ok ? { ok: true, count: cookies.length } : { ok: false, error: `HTTP ${res.status}` };
}

async function report(result) {
  await chrome.action.setBadgeBackgroundColor({ color: result.ok ? '#16a34a' : '#dc2626' });
  await chrome.action.setBadgeText({ text: result.ok ? 'OK' : '!' });
  if (!result.ok) console.error('StarPanel:', result.error);
  return result;
}

chrome.action.onClicked.addListener(() => sendCookies().then(report));

chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
  if (msg?.type !== 'send-starlink-cookies') return false;
  sendCookies().then(report).then(respond);
  return true; // respuesta asíncrona
});
