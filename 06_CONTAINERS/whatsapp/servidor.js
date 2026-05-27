/**
 * Servico WhatsApp do Orquestrador
 * - Escaneia QR code uma vez e fica conectado
 * - Porta 3000: API para O_WHATSAPP agent enviar mensagens
 * - Escuta mensagens recebidas e encaminha ao O_WHATSAPP agent (porta 3001)
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode  = require('qrcode-terminal');
const http    = require('http');

const app = express();
app.use(express.json());

let clientePronto = false;

// -- Encaminha mensagem recebida ao O_WHATSAPP agent -------------------------

function encaminharParaAgente(payload) {
    const body = JSON.stringify(payload);
    const opts = {
        hostname: 'localhost',
        port:     3001,
        path:     '/mensagem',
        method:   'POST',
        headers:  {
            'Content-Type':   'application/json',
            'Content-Length': Buffer.byteLength(body)
        }
    };
    const req = http.request(opts, function(res) {
        var data = '';
        res.on('data', function(chunk) { data += chunk; });
        res.on('end', function() {
            try {
                var r = JSON.parse(data);
                if (r.ok) {
                    console.log('[AGENTE] Roteado para O_MAESTRO -> ' + payload.numero);
                }
            } catch(e) {}
        });
    });
    req.on('error', function(err) {
        console.error('[AGENTE] Erro ao encaminhar: ' + err.message);
    });
    req.write(body);
    req.end();
}

// -- Cliente WhatsApp --------------------------------------------------------

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './sessao' }),
    puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] }
});

client.on('qr', function(qr) {
    console.log('\n=== ESCANEIE O QR CODE COM SEU WHATSAPP ===');
    qrcode.generate(qr, { small: true });
    console.log('Aguardando autenticacao...\n');
});

client.on('authenticated', function() {
    console.log('[OK] Autenticado! Sessao salva.');
});

client.on('ready', function() {
    clientePronto = true;
    console.log('[OK] WhatsApp conectado e pronto.');
    console.log('[OK] API na porta 3000 | O_WHATSAPP agent na porta 3001\n');
});

client.on('disconnected', function(reason) {
    clientePronto = false;
    console.log('[AVISO] Desconectado: ' + reason);
});

// -- Escuta mensagens recebidas ----------------------------------------------

client.on('message', async function(msg) {
    if (msg.fromMe) return;
    if (msg.from === 'status@broadcast') return;
    if (msg.type !== 'chat') {
        console.log('[RECEBIDO] Tipo nao suportado: ' + msg.type + ' - ignorado');
        return;
    }

    var nome = 'Contato';
    try {
        var contato = await msg.getContact();
        nome = contato.pushname || contato.name || contato.number || 'Contato';
    } catch(e) {}

    var eGrupo = msg.from.endsWith('@g.us');
    var numero = msg.from.replace(/@.*/, '');

    console.log('[RECEBIDO] ' + nome + ' (' + numero + ')' + (eGrupo ? ' [GRUPO]' : '') + ': ' + msg.body.substring(0, 80));

    encaminharParaAgente({
        numero:   numero,
        nome:     nome,
        mensagem: msg.body,
        grupo:    eGrupo
    });
});

// -- API REST ----------------------------------------------------------------

// POST /enviar  { "numero": "5511999999999", "mensagem": "Ola!" }
app.post('/enviar', async function(req, res) {
    var numero   = req.body.numero;
    var mensagem = req.body.mensagem;

    if (!clientePronto) {
        return res.status(503).json({ ok: false, erro: 'WhatsApp nao conectado ainda' });
    }
    if (!numero || !mensagem) {
        return res.status(400).json({ ok: false, erro: 'numero e mensagem sao obrigatorios' });
    }

    try {
        var numeroLimpo = numero.replace(/\D/g, '');
        var idReal = await client.getNumberId(numeroLimpo);
        if (!idReal) {
            return res.status(404).json({ ok: false, erro: 'Numero ' + numeroLimpo + ' nao encontrado no WhatsApp' });
        }
        await client.sendMessage(idReal._serialized, mensagem);
        console.log('[ENVIADO] -> ' + numeroLimpo + ': ' + mensagem.substring(0, 60));
        res.json({ ok: true, para: numeroLimpo, mensagem: mensagem });
    } catch(err) {
        console.error('[ERRO]', err.message);
        res.status(500).json({ ok: false, erro: err.message });
    }
});

// GET /status
app.get('/status', function(req, res) {
    res.json({ ok: clientePronto, status: clientePronto ? 'conectado' : 'desconectado' });
});

// GET /contatos
app.get('/contatos', async function(req, res) {
    if (!clientePronto) return res.status(503).json({ ok: false, erro: 'Nao conectado' });
    try {
        var contatos = await client.getContacts();
        var lista = contatos
            .filter(function(c) { return c.name && c.number; })
            .map(function(c) { return { nome: c.name, numero: c.number }; })
            .slice(0, 50);
        res.json({ ok: true, contatos: lista });
    } catch(err) {
        res.status(500).json({ ok: false, erro: err.message });
    }
});

// -- Inicia ------------------------------------------------------------------

app.listen(3000, function() {
    console.log('=== SISTEMA OPEN CLAUDE - SERVICO WHATSAPP ===');
    console.log('Iniciando conexao com WhatsApp...\n');
});

client.initialize();
