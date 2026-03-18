const http = require('http');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = 3001;
let serverStarted = false;

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function normalizePhone(phone) {
  const digits = String(phone || '').replace(/\D/g, '');
  if (!digits) {
    return '';
  }
  return `${digits}@c.us`;
}

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './auth_info' }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  },
});

const server = http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/send') {
    return sendJson(res, 404, { ok: false, error: 'Not found' });
  }

  let rawBody = '';
  req.on('data', (chunk) => {
    rawBody += chunk;
    if (rawBody.length > 1024 * 1024) {
      req.destroy();
    }
  });

  req.on('end', async () => {
    try {
      const body = JSON.parse(rawBody || '{}');
      const phone = body.phone;
      const message = body.message;

      if (!phone || !message) {
        return sendJson(res, 400, { ok: false, error: 'phone y message son obligatorios' });
      }

      const chatId = normalizePhone(phone);
      if (!chatId) {
        return sendJson(res, 400, { ok: false, error: 'phone inválido' });
      }

      await client.sendMessage(chatId, String(message));
      console.log(`[SEND] ✅ ${chatId} | ${String(message).slice(0, 80)}`);
      return sendJson(res, 200, { ok: true });
    } catch (error) {
      console.error('[SEND] ❌ Error enviando mensaje:', error.message || error);
      return sendJson(res, 500, { ok: false, error: String(error.message || error) });
    }
  });
});

client.on('qr', () => {
  console.log('Escanea el QR ejecutando connect2.js si la sesión no está autenticada.');
});

client.on('auth_failure', (msg) => {
  console.error('❌ Error de autenticación:', msg);
});

client.on('ready', () => {
  console.log('✅ WhatsApp listo');
  if (!serverStarted) {
    serverStarted = true;
    server.listen(PORT, () => {
      console.log(`🌐 HTTP server escuchando en http://localhost:${PORT}`);
    });
  }
});

client.initialize();
