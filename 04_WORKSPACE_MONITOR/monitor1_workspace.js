/*
AGENTE-X | Monitor Workspace JS — M6.2.1
Zero Ghost: dados reais do backend ou INDISPONIVEL. Nunca simula.
*/
document.addEventListener("DOMContentLoaded", () => {

    const BACKEND = 'http://127.0.0.1:5050';
    let backendOnline = false;
    let metricsCache = {};

    // ── Relógio ──────────────────────────────────────────────
    function updateClock() {
        const now = new Date();
        document.getElementById('clock').textContent = now.toLocaleTimeString('pt-BR');
    }
    setInterval(updateClock, 1000);
    updateClock();

    // ── Tabs ─────────────────────────────────────────────────
    window.showTab = function(name, btn) {
        ['resumo','missoes','fila','finance'].forEach(t => {
            const el = document.getElementById('tab-' + t);
            if (el) el.style.display = (t === name) ? '' : 'none';
        });
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        if (name !== 'resumo' && backendOnline) fetchMetrics();
    };

    // ── Badge helper ─────────────────────────────────────────
    function badge(id, text, cls) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = text;
        el.className = 'badge ' + cls;
    }

    function setMetric(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = (val === undefined || val === null) ? '—' : val;
    }

    // ── Backend indicator ────────────────────────────────────
    function setBackendStatus(online) {
        backendOnline = online;
        const dot = document.getElementById('backend-dot');
        const lbl = document.getElementById('backend-label');
        if (online) {
            dot.className = 'pulse-dot online';
            lbl.textContent = 'BACKEND ONLINE';
            lbl.style.color = 'var(--color-real)';
        } else {
            dot.className = 'pulse-dot offline';
            lbl.textContent = 'BACKEND OFFLINE';
            lbl.style.color = 'var(--color-error)';
            const ids = ['status-runtime','status-git','status-hash',
                         'status-memory','status-gov','status-sqlite','status-obsidian'];
            ids.forEach(id => badge(id, 'INDISPONÍVEL', 'badge-unavailable'));
            badge('metrics-badge','backend offline','badge-unavailable');
        }
    }

    // ── /api/status ──────────────────────────────────────────
    function fetchStatus() {
        fetch(BACKEND + '/api/status', {signal: AbortSignal.timeout(3000)})
            .then(r => { if (!r.ok) throw new Error(); return r.json(); })
            .then(d => {
                setBackendStatus(true);
                badge('status-runtime', d.execucao || 'ATIVA', 'badge-active');
                const gitCls = d.git_status === 'SINCRONIZADO' ? 'badge-active' : 'badge-warning';
                badge('status-git',    d.git_status  || '?',   gitCls);
                badge('status-hash',   d.git_commit  || '?',   'badge-real');
                badge('git-commit',    d.git_commit  || '?',   'badge-real');
                badge('git-branch',    d.git_branch  || '?',   'badge-real');
                badge('git-status',    d.git_status  || '?',   gitCls);
                badge('status-memory', d.memoria     || '?',   d.memoria === 'OK' ? 'badge-active' : 'badge-error');
                badge('status-gov',    d.governanca  || '?',   d.governanca === 'OK' ? 'badge-active' : 'badge-error');
                badge('status-sqlite', d.memoria     || '?',   d.memoria === 'OK' ? 'badge-active' : 'badge-error');
                badge('status-obsidian', d.sincronia || '?',   'badge-active');
                // Métricas inline no /api/status
                if (d.missions_completed !== undefined) {
                    setMetric('m-completed', d.missions_completed);
                    setMetric('m-queued',    d.fila_queued);
                    setMetric('m-logs',      d.logs_total);
                    setMetric('m-errors',    d.logs_errors);
                    setMetric('m-finance',   '$' + (d.finance_daily_usd || 0).toFixed(4));
                    setMetric('m-total',     d.missions_total);
                    badge('metrics-badge', 'DADOS REAIS', 'badge-real');
                }
            })
            .catch(() => setBackendStatus(false));
    }

    // ── /api/metrics (completo) ──────────────────────────────
    function fetchMetrics() {
        fetch(BACKEND + '/api/metrics', {signal: AbortSignal.timeout(3000)})
            .then(r => { if (!r.ok) throw new Error(); return r.json(); })
            .then(d => {
                metricsCache = d;

                // Missões
                const miss = d.missions || {};
                setMetric('miss-completed', miss.completed);
                setMetric('miss-created',   miss.created);
                setMetric('miss-failed',     miss.failed);
                setMetric('miss-validated',  miss.validated);
                setMetric('miss-cancelled',  miss.cancelled);
                setMetric('miss-total',      miss.total);
                const pct = miss.total > 0 ? Math.round((miss.completed / miss.total) * 100) : 0;
                const bar = document.getElementById('miss-progress');
                if (bar) bar.style.width = pct + '%';
                const pctEl = document.getElementById('miss-pct');
                if (pctEl) pctEl.textContent = 'Taxa de conclusão: ' + pct + '%';

                // Fila
                const fila = d.fila || {};
                setMetric('fila-queued',    fila.queued);
                setMetric('fila-running',   fila.running);
                setMetric('fila-done',       fila.done);
                setMetric('fila-failed',     fila.failed);
                setMetric('fila-cancelled',  fila.cancelled);

                // Financeiro
                const fin = d.finance || {};
                setMetric('fin-daily',   '$' + (fin.daily_usd || 0).toFixed(4));
                setMetric('fin-monthly', '$' + (fin.monthly_usd || 0).toFixed(4));

                // Timeline (git info)
                updateTimeline(d);
            })
            .catch(() => {});
    }

    // ── Timeline ─────────────────────────────────────────────
    function updateTimeline(d) {
        const tl = document.getElementById('timeline');
        if (!tl) return;
        const git = d.git || {};
        const events = [
            {time: d.ts ? d.ts.slice(11,19) : '--:--', text: 'Heartbeat do backend'},
            {time: '--:--', text: 'Git: ' + (git.branch || '?') + ' @ ' + (git.last_commit || '?')},
            {time: '--:--', text: 'Missões concluídas: ' + (d.missions && d.missions.completed || 0)},
            {time: '--:--', text: 'Fila pendente: ' + (d.fila && d.fila.queued || 0)},
            {time: '--:--', text: 'Logs: ' + (d.logs && d.logs.total || 0) + ' | Erros: ' + (d.logs && d.logs.errors || 0)},
        ];
        tl.innerHTML = events.map(e => `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <span class="tl-time">${e.time}</span>
                <span class="tl-text">${e.text}</span>
            </div>`).join('');
        badge('tl-badge', 'REAL', 'badge-real');
    }

    // ── Resizers ─────────────────────────────────────────────
    function setupResizers() {
        const leftBar  = document.getElementById('left-bar');
        const rightBar = document.getElementById('right-bar');
        const rLeft    = document.getElementById('resizer-left');
        const rRight   = document.getElementById('resizer-right');
        const rLeftH   = document.getElementById('resizer-left-h');
        const leftTop  = document.getElementById('left-top-section');

        let mode = null;
        const start = (m) => (e) => {
            mode = m;
            document.getElementById(m === 'lh' ? 'resizer-left-h' :
                m === 'r' ? 'resizer-right' : 'resizer-left').classList.add('resizing');
            document.body.style.cursor   = (m === 'lh') ? 'row-resize' : 'col-resize';
            document.body.style.userSelect = 'none';
        };

        rLeft.addEventListener('mousedown',  start('l'));
        rRight.addEventListener('mousedown', start('r'));
        rLeftH.addEventListener('mousedown', start('lh'));

        document.addEventListener('mousemove', (e) => {
            if (!mode) return;
            if (mode === 'l')  leftBar.style.width = e.clientX + 'px';
            if (mode === 'r')  rightBar.style.width = (document.body.clientWidth - e.clientX) + 'px';
            if (mode === 'lh') leftTop.style.height = (e.clientY - leftBar.getBoundingClientRect().top) + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (!mode) return;
            ['resizer-left','resizer-right','resizer-left-h'].forEach(id => {
                document.getElementById(id).classList.remove('resizing');
            });
            document.body.style.cursor    = 'default';
            document.body.style.userSelect = 'auto';
            mode = null;
        });
    }

    // ── Init ─────────────────────────────────────────────────
    setBackendStatus(false);
    setupResizers();
    fetchStatus();
    fetchMetrics();
    setInterval(fetchStatus,  3000);
    setInterval(fetchMetrics, 10000);
});
