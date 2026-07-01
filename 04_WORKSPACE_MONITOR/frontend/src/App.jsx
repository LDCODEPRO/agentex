import { Component } from 'react';
import { api } from './api';
import Login from './Login';

const TITLES = {
  overview: ['Visão Geral', 'Dashboard executivo do Agente X'],
  chat: ['Chat Jarvis', 'Converse com o agente · resumo auditável'],
  missions: ['Missões', 'Gerenciamento de missões do agente'],
  queue: ['Fila', 'Orquestração do Maestro por status real'],
  brains: ['Cérebro / LLMs', 'Cascata de inteligência e custos'],
  memory: ['Memória', 'Memória persistente do Agente X'],
  logs: ['Logs', 'Eventos do sistema em tempo real'],
  security: ['Segurança', 'Safe Gate · permissões e bloqueios reais'],
  finance: ['Financeiro', 'Finance Engine · custo controlado'],
  settings: ['Configurações', 'Ambiente, chaves e políticas'],
};

const MISSION_FILTERS = ['all', 'MISSION_CREATED', 'MISSION_COMPLETED', 'MISSION_FAILED', 'MISSION_VALIDATED', 'MISSION_CANCELLED'];
const LOG_LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const QUEUE_COLS = [
  { key: 'QUEUED', label: 'Na fila', accent: '#8b97a7' },
  { key: 'RUNNING', label: 'Executando', accent: '#22d3ee' },
  { key: 'DONE', label: 'Concluídas', accent: '#34d399' },
  { key: 'FAILED', label: 'Falhou', accent: '#f87171' },
  { key: 'CANCELLED', label: 'Cancelada', accent: '#fb923c' },
];

function timeAgo(iso) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T'));
  const s = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (s < 60) return `há ${s}s`;
  if (s < 3600) return `há ${Math.floor(s / 60)}min`;
  if (s < 86400) return `há ${Math.floor(s / 3600)}h`;
  return `há ${Math.floor(s / 86400)}d`;
}

const LEVEL_COLOR = { INFO: '#60a5fa', WARNING: '#fbbf24', ERROR: '#f87171', CRITICAL: '#f87171' };

export default class App extends Component {
  state = {
    authChecked: false, authenticated: false,
    screen: 'overview', memTab: null, logFilter: 'ALL', missionFilter: 'all',
    input: '', typing: false, sending: false,
    chat: [{ role: 'agent', kind: 'welcome', text: 'Olá, Diretor. Agente X operando em produção — memória conectada, custo dentro do teto. Descreva uma missão ou pergunta.' }],
    overview: null, activity: [], health: [],
    missions: [], queue: null, brains: [],
    memoryTabs: [], memoryItems: [],
    logs: [], blocked: [], finance: null, settings: [],
  };

  msgRef = { current: null };

  componentDidMount() {
    api.me().then((r) => {
      this.setState({ authChecked: true, authenticated: r.authenticated });
      if (r.authenticated) this.afterLogin();
    }).catch(() => this.setState({ authChecked: true, authenticated: false }));
  }

  componentWillUnmount() {
    clearInterval(this._poll);
    clearTimeout(this._tid);
  }

  afterLogin = () => {
    this.load(this.state.screen);
    clearInterval(this._poll);
    this._poll = setInterval(() => this.load(this.state.screen, { silent: true }), 6000);
  };

  logout = async () => {
    await api.logout();
    clearInterval(this._poll);
    this.setState({ authenticated: false });
  };

  go = (id) => {
    this.setState({ screen: id });
    this.load(id);
  };

  load(screen, opts = {}) {
    const s = this.state;
    const done = (patch) => this.setState(patch);
    switch (screen) {
      case 'overview':
        api.overview().then((overview) => done({ overview })).catch(() => {});
        api.activity().then((activity) => done({ activity })).catch(() => {});
        api.systemHealth().then((health) => done({ health })).catch(() => {});
        break;
      case 'missions':
        api.missions(s.missionFilter).then((missions) => done({ missions })).catch(() => {});
        break;
      case 'queue':
        api.queue().then((queue) => done({ queue })).catch(() => {});
        break;
      case 'brains':
        api.brains().then((brains) => done({ brains })).catch(() => {});
        break;
      case 'memory':
        if (!s.memoryTabs.length) {
          api.memoryTabs().then((memoryTabs) => {
            done({ memoryTabs });
            const tab = s.memTab || memoryTabs[0];
            this.setState({ memTab: tab });
            api.memory(tab).then((memoryItems) => done({ memoryItems })).catch(() => {});
          }).catch(() => {});
        } else if (s.memTab) {
          api.memory(s.memTab).then((memoryItems) => done({ memoryItems })).catch(() => {});
        }
        break;
      case 'logs':
        api.logs(s.logFilter).then((logs) => done({ logs })).catch(() => {});
        break;
      case 'security':
        api.securityBlocked().then((blocked) => done({ blocked })).catch(() => {});
        break;
      case 'finance':
        api.finance().then((finance) => done({ finance })).catch(() => {});
        break;
      case 'settings':
        if (!opts.silent) api.settings().then((settings) => done({ settings })).catch(() => {});
        break;
    }
  }

  setMissionFilter = (f) => { this.setState({ missionFilter: f }); api.missions(f).then((missions) => this.setState({ missions })); };
  setLogFilter = (f) => { this.setState({ logFilter: f }); api.logs(f).then((logs) => this.setState({ logs })); };
  setMemTab = (t) => { this.setState({ memTab: t }); api.memory(t).then((memoryItems) => this.setState({ memoryItems })); };

  send = (text) => {
    const t = (text != null ? text : this.state.input).trim();
    if (!t || this.state.sending) return;
    this.setState((s) => ({ chat: [...s.chat, { role: 'user', text: t }], input: '', sending: true, typing: true }));
    api.chat(t).then((r) => {
      this.setState((s) => ({
        typing: false, sending: false,
        chat: [...s.chat, {
          role: 'agent', kind: 'structured',
          pensamento: r.thought || '—', acao: r.action || '—', observacao: r.observation || '—',
          resposta: r.final_answer, fonte: r.provider || '—', tempo: r.elapsed_s != null ? `${r.elapsed_s}s` : '—',
        }],
      }));
    }).catch(() => {
      this.setState((s) => ({ typing: false, sending: false, chat: [...s.chat, { role: 'agent', kind: 'structured', pensamento: '—', acao: '—', observacao: '—', resposta: 'Erro ao falar com o agente. Tente de novo.', fonte: '—', tempo: '—' }] }));
    });
  };

  componentDidUpdate(_, prevState) {
    if (this.msgRef.current && this.state.screen === 'chat' && prevState.chat.length !== this.state.chat.length) {
      this.msgRef.current.scrollTop = this.msgRef.current.scrollHeight;
    }
  }

  nav(id) {
    const active = this.state.screen === id;
    return 'navbtn' + (active ? ' active' : '');
  }

  render() {
    if (!this.state.authChecked) return null;
    if (!this.state.authenticated) return <Login onLoggedIn={() => { this.setState({ authenticated: true }); this.afterLogin(); }} />;

    const s = this.state;
    const tt = TITLES[s.screen] || ['', ''];

    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: 'radial-gradient(1100px 560px at 82% -12%, rgba(52,211,153,0.07), transparent 58%), radial-gradient(900px 520px at -8% 112%, rgba(34,211,238,0.05), transparent 55%), #070a0f' }}>
        {this.renderSidebar()}
        <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <header style={{ position: 'sticky', top: 0, zIndex: 20, display: 'flex', alignItems: 'center', gap: 18, padding: '16px 28px', borderBottom: '1px solid rgba(96,128,160,0.12)', background: 'rgba(8,11,16,0.72)', backdropFilter: 'blur(12px)' }}>
            <div style={{ minWidth: 0 }}>
              <h1 style={{ margin: 0, fontFamily: "'Space Grotesk',sans-serif", fontWeight: 600, fontSize: 19, color: '#eef4f0' }}>{tt[0]}</h1>
              <p style={{ margin: '3px 0 0', fontSize: 12.5, color: '#7c8896' }}>{tt[1]}</p>
            </div>
            <div style={{ flex: 1 }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '6px 12px', borderRadius: 9, background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.28)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#34d399', animation: 'ring 1.8s infinite' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#8fe9c4', fontFamily: "'Space Grotesk'" }}>Produção · Online</span>
            </div>
            <button className="ghost-btn" onClick={this.logout} style={ghostBtnStyle}>Sair</button>
          </header>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {s.screen === 'overview' && this.renderOverview()}
            {s.screen === 'chat' && this.renderChat()}
            {s.screen === 'missions' && this.renderMissions()}
            {s.screen === 'queue' && this.renderQueue()}
            {s.screen === 'brains' && this.renderBrains()}
            {s.screen === 'memory' && this.renderMemory()}
            {s.screen === 'logs' && this.renderLogs()}
            {s.screen === 'security' && this.renderSecurity()}
            {s.screen === 'finance' && this.renderFinance()}
            {s.screen === 'settings' && this.renderSettings()}
          </div>
        </main>
      </div>
    );
  }

  renderSidebar() {
    const items = [
      ['overview', 'Visão Geral'], ['chat', 'Chat Jarvis'], ['missions', 'Missões'], ['queue', 'Fila'],
      ['brains', 'Cérebro / LLMs'], ['memory', 'Memória'], ['logs', 'Logs'], ['security', 'Segurança'],
      ['finance', 'Financeiro'], ['settings', 'Configurações'],
    ];
    return (
      <aside data-sidebar style={{ width: 248, flexShrink: 0, position: 'sticky', top: 0, height: '100vh', display: 'flex', flexDirection: 'column', borderRight: '1px solid rgba(96,128,160,0.13)', background: 'linear-gradient(180deg,rgba(13,18,26,0.6),rgba(8,11,16,0.6))', backdropFilter: 'blur(8px)', padding: '20px 14px', gap: 4 }}>
        <div data-sidehead style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '4px 8px 16px' }}>
          <div style={{ width: 38, height: 38, borderRadius: 11, flexShrink: 0, display: 'grid', placeItems: 'center', background: 'linear-gradient(140deg,#0d2a22,#103a30)', border: '1px solid rgba(52,211,153,0.4)' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M12 3v18M4 7.5l8 4.5 8-4.5" /></svg>
          </div>
          <div>
            <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 700, fontSize: 15.5, letterSpacing: 1.5, color: '#eef6f2' }}>AGENTE X</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: '#34d399', animation: 'pulse 1.8s infinite' }} /><span style={{ fontSize: 11, color: '#6dd6ac', fontWeight: 500 }}>Online 24/7</span></div>
          </div>
        </div>
        {items.map(([id, label]) => (
          <button key={id} className={this.nav(id)} onClick={() => this.go(id)} style={navBtnStyle}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: this.state.screen === id ? '#34d399' : 'rgba(139,151,167,0.4)', flexShrink: 0 }} />
            <span data-navlabel>{label}</span>
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <div data-sidefoot style={{ padding: 12, borderRadius: 11, background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(96,128,160,0.12)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: 'linear-gradient(140deg,#1a2433,#0f1620)', display: 'grid', placeItems: 'center', fontFamily: "'Space Grotesk'", fontWeight: 700, fontSize: 13, color: '#9ff0d0', border: '1px solid rgba(96,128,160,0.18)' }}>LZ</div>
            <div><div style={{ fontSize: 12.5, fontWeight: 600, color: '#dbe4ec' }}>Luiz</div><div style={{ fontSize: 10.5, color: '#6b7787' }}>Operador</div></div>
          </div>
          <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6, fontSize: 10.5, color: '#6b7787' }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399' }} />Ambiente: <span style={{ color: '#9ff0d0', fontWeight: 600 }}>Produção VPS</span></div>
        </div>
      </aside>
    );
  }

  renderOverview() {
    const ov = this.state.overview;
    const cards = ov ? [
      { k: 'Status do Agente', v: 'Online', sub: 'daemon ativo · systemd', c: '#34d399' },
      { k: 'Missões', v: `${ov.missions.done}/${ov.missions.total}`, sub: 'concluídas / total', c: '#60a5fa' },
      { k: 'Custo Hoje', v: `US$ ${ov.finance.daily_spend_usd}`, sub: `teto US$ ${ov.finance.daily_limit_usd}`, c: '#34d399' },
      { k: 'Fila', v: `${ov.fila.queued} · ${ov.fila.running}`, sub: 'aguardando · executando', c: '#22d3ee' },
      { k: 'Kill Switch (pagos)', v: ov.kill_switch ? 'Ativo' : 'Desativado', sub: ov.kill_switch ? 'custo zero forçado' : 'pagos liberados', c: ov.kill_switch ? '#fbbf24' : '#34d399' },
      { k: 'Memória', v: `${ov.knowledge}`, sub: 'itens de conhecimento', c: '#22d3ee' },
    ] : [];
    return (
      <div style={{ padding: '26px 28px 40px' }}>
        <section style={{ position: 'relative', overflow: 'hidden', borderRadius: 18, padding: '30px 32px', border: '1px solid rgba(52,211,153,0.22)', background: 'linear-gradient(120deg,rgba(13,30,25,0.85),rgba(10,16,22,0.6))', marginBottom: 24 }}>
          <div style={{ fontSize: 11.5, letterSpacing: 2, color: '#6dd6ac', fontWeight: 600, fontFamily: "'Space Grotesk'" }}>CENTRO DE COMANDO AUTÔNOMO</div>
          <h2 style={{ margin: '12px 0 0', fontFamily: "'Space Grotesk',sans-serif", fontWeight: 600, fontSize: 27, lineHeight: 1.28, color: '#f1f7f3', maxWidth: 680 }}>Agente X operando em produção, com memória, custo controlado e segurança auditável.</h2>
          <div style={{ display: 'flex', gap: 12, marginTop: 22, flexWrap: 'wrap' }}>
            <button className="cta-btn" onClick={() => this.go('chat')} style={ctaBtnStyle}>Abrir Chat Jarvis</button>
            <button className="ghost-btn" onClick={() => this.go('missions')} style={ghostBtnStyle}>Ver Missões</button>
          </div>
        </section>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 14, marginBottom: 24 }}>
          {cards.map((c) => (
            <div key={c.k} className="card" style={cardStyle}>
              <div style={{ position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: c.c, opacity: .85 }} />
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 11.5, color: '#7c8896' }}>{c.k}</span><span style={{ width: 8, height: 8, borderRadius: '50%', background: c.c }} /></div>
              <div style={{ marginTop: 10, fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 20, color: '#eef4f0' }}>{c.v}</div>
              <div style={{ marginTop: 6, fontSize: 11.5, color: '#6b7787' }}>{c.sub}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 18 }}>
          <section style={panelStyle}>
            <h3 style={h3Style}>Atividade recente</h3>
            {this.state.activity.map((e) => (
              <div key={e.id} style={{ display: 'flex', gap: 14, paddingBottom: 14, borderBottom: '1px solid rgba(96,128,160,0.08)', marginBottom: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: LEVEL_COLOR[e.level] || '#8b97a7', marginTop: 4, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 10 }}><span style={{ fontWeight: 600, fontSize: 13, color: '#dbe4ec' }}>{e.source}</span><span style={{ fontSize: 10.5, color: '#5f6b7a' }}>{timeAgo(e.created_at)}</span></div>
                  <div style={{ marginTop: 2, fontSize: 12, color: '#7c8896' }}>{e.message}</div>
                </div>
              </div>
            ))}
            {!this.state.activity.length && <div style={{ fontSize: 12.5, color: '#5f6b7a' }}>—</div>}
          </section>
          <section style={panelStyle}>
            <h3 style={h3Style}>Saúde do Sistema</h3>
            {this.state.health.map((h) => (
              <div key={h.l} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 12px', borderRadius: 9, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(96,128,160,0.10)', marginBottom: 8 }}>
                <span style={{ fontSize: 12.5, color: '#aeb9c6' }}>{h.l}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 600, color: h.c }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: h.c }} />{h.v}</span>
              </div>
            ))}
          </section>
        </div>
      </div>
    );
  }

  renderChat() {
    const s = this.state;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 70px)' }}>
        <div ref={(el) => (this.msgRef.current = el)} style={{ flex: 1, overflowY: 'auto', padding: '26px 28px 12px' }}>
          <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
            {s.chat.map((m, i) => m.role === 'user' ? (
              <div key={i} style={{ alignSelf: 'flex-end', maxWidth: '74%', background: 'linear-gradient(135deg,#163a2e,#11261f)', border: '1px solid rgba(52,211,153,0.25)', borderRadius: '14px 14px 4px 14px', padding: '12px 16px', fontSize: 13.5, color: '#e3f3ec' }}>{m.text}</div>
            ) : (
              <div key={i} style={{ alignSelf: 'flex-start', maxWidth: '88%', display: 'flex', gap: 12 }}>
                <div style={agentIconStyle}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="1.8"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /></svg></div>
                <div style={{ flex: 1, background: '#10151e', border: '1px solid rgba(96,128,160,0.16)', borderRadius: '4px 14px 14px 14px', padding: '15px 17px' }}>
                  {m.kind === 'welcome' ? <div style={{ fontSize: 13.5, color: '#cdd8e2', lineHeight: 1.55 }}>{m.text}</div> : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                      <TraceRow label="PENSAMENTO" color="#a78bfa" text={m.pensamento} />
                      <TraceRow label="AÇÃO" color="#60a5fa" text={m.acao} />
                      <TraceRow label="OBSERVAÇÃO" color="#22d3ee" text={m.observacao} />
                      <div style={{ marginTop: 4, padding: '13px 15px', borderRadius: 10, background: 'rgba(52,211,153,0.07)', border: '1px solid rgba(52,211,153,0.2)' }}>
                        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, color: '#34d399', marginBottom: 6 }}>RESPOSTA FINAL</div>
                        <div style={{ fontSize: 13.5, color: '#e3f3ec', lineHeight: 1.55 }}>{m.resposta}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                        <Chip>⬡ {m.fonte}</Chip>
                        <Chip>⏱ {m.tempo}</Chip>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {s.typing && (
              <div style={{ alignSelf: 'flex-start', display: 'flex', gap: 12, alignItems: 'center' }}>
                <div style={agentIconStyle}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="1.8"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /></svg></div>
                <div style={{ display: 'flex', gap: 5, padding: '14px 16px', background: '#10151e', border: '1px solid rgba(96,128,160,0.16)', borderRadius: '4px 14px 14px 14px' }}>
                  {[0, 0.18, 0.36].map((d) => <span key={d} style={{ width: 7, height: 7, borderRadius: '50%', background: '#34d399', animation: `dotb 1.2s infinite ${d}s` }} />)}
                </div>
              </div>
            )}
          </div>
        </div>
        <div style={{ padding: '14px 28px 22px', borderTop: '1px solid rgba(96,128,160,0.12)' }}>
          <div style={{ maxWidth: 860, margin: '0 auto' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', background: '#10151e', border: '1px solid rgba(96,128,160,0.2)', borderRadius: 13, padding: '8px 8px 8px 16px' }}>
              <input
                value={s.input}
                onChange={(e) => this.setState({ input: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); this.send(); } }}
                placeholder="Envie um comando ao Agente X…"
                disabled={s.sending}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#e6edf3', fontSize: 14, padding: '9px 0' }}
              />
              <button className="cta-btn" onClick={() => this.send()} disabled={s.sending} style={sendBtnStyle}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
              </button>
            </div>
            <div style={{ marginTop: 8, fontSize: 10.5, color: '#5f6b7a', textAlign: 'center' }}>Cadeia interna sensível não é exibida — apenas resumo auditável. <span style={{ color: '#6dd6ac' }}>Reality First.</span></div>
          </div>
        </div>
      </div>
    );
  }

  renderMissions() {
    const labels = { all: 'Todas', MISSION_CREATED: 'Criada', MISSION_COMPLETED: 'Concluída', MISSION_FAILED: 'Falhou', MISSION_VALIDATED: 'Validada', MISSION_CANCELLED: 'Cancelada' };
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginBottom: 18 }}>
          {MISSION_FILTERS.map((f) => <Chip key={f} active={this.state.missionFilter === f} onClick={() => this.setMissionFilter(f)}>{labels[f]}</Chip>)}
        </div>
        <div style={{ background: '#10151e', border: '1px solid rgba(96,128,160,0.15)', borderRadius: 14, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '90px 2.2fr 1.3fr 1fr', gap: 14, padding: '13px 20px', borderBottom: '1px solid rgba(96,128,160,0.14)', fontSize: 10.5, letterSpacing: 0.6, color: '#6b7787', fontWeight: 600 }}>
            <span>ID</span><span>TÍTULO</span><span>STATUS</span><span>CRIADA</span>
          </div>
          {this.state.missions.map((m) => (
            <div key={m.id} className="row" style={{ display: 'grid', gridTemplateColumns: '90px 2.2fr 1.3fr 1fr', gap: 14, padding: '14px 20px', borderBottom: '1px solid rgba(96,128,160,0.07)', alignItems: 'center' }}>
              <span style={{ fontFamily: "'JetBrains Mono'", fontSize: 12, color: '#8fe9c4' }}>{m.code}</span>
              <div style={{ minWidth: 0 }}><div style={{ fontSize: 13, color: '#dbe4ec', fontWeight: 500 }}>{m.title}</div>{m.summary && <div style={{ fontSize: 11, color: '#6b7787', marginTop: 2 }}>{m.summary.slice(0, 90)}</div>}</div>
              <StatusChip status={m.status} />
              <span style={{ fontSize: 11, color: '#7c8896', fontFamily: "'JetBrains Mono'" }}>{m.created_at}</span>
            </div>
          ))}
          {!this.state.missions.length && <div style={{ padding: 20, fontSize: 12.5, color: '#5f6b7a' }}>Nenhuma missão nesse filtro.</div>}
        </div>
      </div>
    );
  }

  renderQueue() {
    const q = this.state.queue || {};
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <p style={{ margin: '0 0 18px', fontSize: 13, color: '#7c8896' }}>Fila real do Maestro (<code>fila_execucao</code>) — 5 status que existem hoje no banco.</p>
        <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 8 }}>
          {QUEUE_COLS.map((col) => (
            <div key={col.key} style={{ flex: 1, minWidth: 220, display: 'flex', flexDirection: 'column', gap: 11 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: col.accent }} />
                <span style={{ fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 13, color: '#dbe4ec' }}>{col.label}</span>
                <span style={{ marginLeft: 'auto', fontSize: 11, color: '#6b7787', background: 'rgba(255,255,255,0.03)', padding: '1px 7px', borderRadius: 6 }}>{(q[col.key] || []).length}</span>
              </div>
              {(q[col.key] || []).slice(0, 8).map((c) => (
                <div key={c.id} style={{ background: '#10151e', border: '1px solid rgba(96,128,160,0.15)', borderTop: `2px solid ${col.accent}`, borderRadius: 11, padding: '13px 14px' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#e3eaf0' }}>{c.mission_code}</div>
                  <div style={{ marginTop: 9, fontSize: 10.5, color: '#8b97a7' }}>prioridade {c.priority}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  renderBrains() {
    const brains = this.state.brains;
    const total = brains.reduce((a, b) => a + b.calls, 0) || 1;
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <section style={panelStyle}>
          <h3 style={h3Style}>Cascata de Inteligência</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <CascadeStep label="Bridge" color="#34d399" />
            <Arrow /><CascadeStep label="Ollama" color="#22d3ee" />
            <Arrow /><CascadeStep label="APIs pagas (teto US$1/dia)" color="#fbbf24" />
          </div>
        </section>
        <section style={{ ...panelStyle, marginTop: 18 }}>
          <h3 style={h3Style}>Uso por provedor <span style={{ fontSize: 10.5, color: '#6b7787', fontWeight: 400 }}>· contagem real de chamadas</span></h3>
          {brains.map((b) => (
            <div key={b.provider} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 13, color: '#dbe4ec' }}>{b.provider}</span>
                <span style={{ fontSize: 11.5, color: '#9aa6b4', fontFamily: "'JetBrains Mono'" }}>{b.calls} chamadas · US$ {b.cost_usd}</span>
              </div>
              <div style={{ height: 8, borderRadius: 5, background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                <div style={{ height: '100%', borderRadius: 5, width: `${(b.calls / total) * 100}%`, background: '#34d399' }} />
              </div>
            </div>
          ))}
          {!brains.length && <div style={{ fontSize: 12.5, color: '#5f6b7a' }}>Sem chamadas registradas ainda.</div>}
        </section>
      </div>
    );
  }

  renderMemory() {
    const s = this.state;
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginBottom: 18 }}>
          {s.memoryTabs.map((t) => <Chip key={t} active={s.memTab === t} onClick={() => this.setMemTab(t)}>{t}</Chip>)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(290px,1fr))', gap: 14 }}>
          {s.memoryItems.map((i) => (
            <div key={i.id} className="card" style={cardStyleStatic}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: '#e3eaf0' }}>{i.key}</div>
                <span style={{ fontSize: 10, fontWeight: 600, color: '#7fb3ff', background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.22)', padding: '3px 8px', borderRadius: 6, flexShrink: 0 }}>{i.category}</span>
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: '#aeb9c6' }}>{i.value?.slice(0, 140)}</div>
              <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
                <Field label="CONFIANÇA" value={`${Math.round((i.confidence || 0) * 100)}%`} />
                <Field label="ATUALIZADO" value={i.updated_at} />
              </div>
            </div>
          ))}
          {!s.memoryItems.length && <div style={{ fontSize: 12.5, color: '#5f6b7a' }}>—</div>}
        </div>
      </div>
    );
  }

  renderLogs() {
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
          {LOG_LEVELS.map((l) => <Chip key={l} active={this.state.logFilter === l} onClick={() => this.setLogFilter(l)}>{l}</Chip>)}
        </div>
        <div style={{ background: '#0a0e14', border: '1px solid rgba(96,128,160,0.16)', borderRadius: 13, overflow: 'hidden', fontFamily: "'JetBrains Mono',monospace" }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderBottom: '1px solid rgba(96,128,160,0.14)', background: 'rgba(255,255,255,0.015)' }}>
            <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#f87171' }} /><span style={{ width: 11, height: 11, borderRadius: '50%', background: '#fbbf24' }} /><span style={{ width: 11, height: 11, borderRadius: '50%', background: '#34d399' }} />
            <span style={{ marginLeft: 8, fontSize: 11.5, color: '#7c8896' }}>agente-x · logs (tabela logs)</span>
          </div>
          <div style={{ maxHeight: 560, overflowY: 'auto', padding: '10px 4px' }}>
            {this.state.logs.map((l) => (
              <div key={l.id} className="log-row" style={{ display: 'flex', gap: 12, padding: '6px 14px', fontSize: 12, alignItems: 'baseline' }}>
                <span style={{ color: '#5f6b7a', flexShrink: 0 }}>{l.created_at}</span>
                <span style={{ flexShrink: 0, minWidth: 74, fontWeight: 600, color: LEVEL_COLOR[l.level] || '#8b97a7' }}>{l.level}</span>
                <span style={{ flexShrink: 0, minWidth: 96, color: '#7fb3ff' }}>{l.source}</span>
                <span style={{ color: '#c0cad6', flex: 1 }}>{l.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  renderSecurity() {
    const levels = [
      { n: 'READ', l: 'Leitura', d: 'Sempre permitida — consulta de estado, arquivos e métricas', c: '#34d399' },
      { n: 'WRITE', l: 'Escrita', d: 'Só dentro da raiz do projeto (allowlist do safe_gate)', c: '#22d3ee' },
      { n: 'SHELL', l: 'Comandos', d: 'Sem encadeamento (&&, |, ;), sem comandos destrutivos', c: '#fbbf24' },
    ];
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <h3 style={h3Style}>Níveis de permissão · Safe Gate</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 14, marginBottom: 26 }}>
          {levels.map((lv) => (
            <div key={lv.n} className="card" style={{ ...cardStyleStatic, position: 'relative' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 3, background: lv.c, opacity: .85 }} />
              <div style={{ fontFamily: "'JetBrains Mono'", fontSize: 11, color: lv.c, fontWeight: 600 }}>{lv.n}</div>
              <div style={{ marginTop: 7, fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 15, color: '#eef4f0' }}>{lv.l}</div>
              <div style={{ marginTop: 6, fontSize: 12, color: '#7c8896' }}>{lv.d}</div>
            </div>
          ))}
        </div>
        <h3 style={h3Style}>Bloqueios reais recentes</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {this.state.blocked.map((b) => (
            <div key={b.id} style={{ padding: '11px 13px', borderRadius: 10, background: 'rgba(248,113,113,0.05)', border: '1px solid rgba(248,113,113,0.16)' }}>
              <div style={{ fontFamily: "'JetBrains Mono'", fontSize: 12, color: '#f3b0b0', wordBreak: 'break-all' }}>{b.message}</div>
              <div style={{ marginTop: 5, fontSize: 10.5, color: '#6b7787' }}>{b.created_at}</div>
            </div>
          ))}
          {!this.state.blocked.length && <div style={{ fontSize: 12.5, color: '#5f6b7a' }}>Nenhum bloqueio registrado.</div>}
        </div>
      </div>
    );
  }

  renderFinance() {
    const f = this.state.finance;
    if (!f) return <div style={{ padding: 28 }} />;
    const pct = Math.min(100, (f.daily_spend_usd / f.daily_limit_usd) * 100);
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 14, marginBottom: 20 }}>
          <StatCard label="Gasto hoje" value={`US$ ${f.daily_spend_usd}`} color="#8fe9c4" />
          <StatCard label="Teto diário" value={`US$ ${f.daily_limit_usd}`} />
          <StatCard label="Gasto histórico" value={`US$ ${f.total_spend_usd}`} />
          <StatCard label="Hard stop" value={f.safe_mode ? 'Ativo' : 'Desativado'} color={f.safe_mode ? '#34d399' : '#f87171'} />
        </div>
        <section style={panelStyle}>
          <h3 style={h3Style}>Consumo do teto diário</h3>
          <div style={{ fontSize: 12, color: '#7c8896', marginBottom: 16 }}>US$ {f.daily_spend_usd} de US$ {f.daily_limit_usd} · <span style={{ color: '#6dd6ac' }}>{pct.toFixed(1)}% utilizado</span></div>
          <div style={{ height: 16, borderRadius: 9, background: 'rgba(255,255,255,0.04)', overflow: 'hidden', border: '1px solid rgba(96,128,160,0.12)' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#34d399,#22c79b)', borderRadius: 9 }} />
          </div>
        </section>
        <section style={{ ...panelStyle, marginTop: 18 }}>
          <h3 style={h3Style}>Uso por provedor</h3>
          {f.by_provider.map((p) => (
            <div key={p.provider} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(96,128,160,0.08)' }}>
              <span style={{ fontSize: 13, color: '#dbe4ec' }}>{p.provider}</span>
              <span style={{ fontSize: 12, color: '#9aa6b4', fontFamily: "'JetBrains Mono'" }}>US$ {p.cost_usd}</span>
            </div>
          ))}
        </section>
      </div>
    );
  }

  renderSettings() {
    return (
      <div style={{ padding: '24px 28px 40px' }}>
        <p style={{ margin: '0 0 18px', fontSize: 13, color: '#7c8896' }}>Chaves nunca são exibidas em texto puro — sempre mascaradas.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 14 }}>
          {this.state.settings.map((s) => (
            <div key={s.title} style={cardStyleStatic}>
              <div style={{ fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 14, color: '#eef4f0', marginBottom: 12, paddingBottom: 10, borderBottom: '1px solid rgba(96,128,160,0.1)' }}>{s.title}</div>
              {s.rows.map((r) => (
                <div key={r.k} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 9 }}>
                  <span style={{ fontSize: 12, color: '#7c8896' }}>{r.k}</span>
                  <span style={{ fontSize: 12, color: '#dbe4ec', fontFamily: "'JetBrains Mono'", textAlign: 'right' }}>{r.v}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }
}

// ---------- pequenos componentes / estilos reaproveitados ----------

function TraceRow({ label, color, text }) {
  return (
    <div style={{ display: 'flex', gap: 9 }}>
      <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, color, minWidth: 84 }}>{label}</span>
      <span style={{ fontSize: 12.5, color: '#9aa6b4', lineHeight: 1.5 }}>{text}</span>
    </div>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '7px 13px', borderRadius: 8, fontSize: 12.5, fontWeight: 500, cursor: onClick ? 'pointer' : 'default',
      whiteSpace: 'nowrap', fontFamily: "'Space Grotesk',sans-serif",
      border: '1px solid ' + (active ? 'rgba(52,211,153,0.42)' : 'rgba(96,128,160,0.18)'),
      background: active ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.02)',
      color: active ? '#9ff0d0' : '#8b97a7',
    }}>{children}</button>
  );
}

function StatusChip({ status }) {
  const map = {
    MISSION_COMPLETED: '#34d399', MISSION_VALIDATED: '#34d399', MISSION_FAILED: '#f87171',
    MISSION_CREATED: '#fbbf24', MISSION_CANCELLED: '#8b97a7',
  };
  const c = map[status] || '#8b97a7';
  return <span style={{ justifySelf: 'start', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, fontWeight: 600, color: c, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(96,128,160,0.16)', padding: '4px 9px', borderRadius: 7 }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: c }} />{status?.replace('MISSION_', '')}</span>;
}

function CascadeStep({ label, color }) {
  return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '11px 18px', borderRadius: 11, background: `${color}18`, border: `1px solid ${color}4d` }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: color }} /><span style={{ fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 13.5, color }}>{label}</span></div>;
}

function Arrow() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#5f6b7a" strokeWidth="2" strokeLinecap="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
}

function Field({ label, value }) {
  return <div><div style={{ fontSize: 9.5, color: '#5f6b7a', letterSpacing: 0.4 }}>{label}</div><div style={{ fontSize: 11.5, color: '#9aa6b4', marginTop: 2, fontFamily: "'JetBrains Mono'" }}>{value || '—'}</div></div>;
}

function StatCard({ label, value, color }) {
  return <div style={cardStyleStatic}><div style={{ fontSize: 11.5, color: '#7c8896' }}>{label}</div><div style={{ marginTop: 8, fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 24, color: color || '#eef4f0' }}>{value}</div></div>;
}

const navBtnStyle = { display: 'flex', alignItems: 'center', gap: 12, width: '100%', padding: '10px 12px', borderRadius: 9, border: 'none', cursor: 'pointer', textAlign: 'left', fontFamily: "'Space Grotesk', sans-serif", fontSize: 13.5, fontWeight: 500, color: '#8b97a7', background: 'transparent' };
const cardStyle = { position: 'relative', background: '#10151e', border: '1px solid rgba(96,128,160,0.15)', borderRadius: 14, padding: '17px 18px', overflow: 'hidden' };
const cardStyleStatic = { background: '#10151e', border: '1px solid rgba(96,128,160,0.15)', borderRadius: 13, padding: '16px 18px' };
const panelStyle = { background: '#10151e', border: '1px solid rgba(96,128,160,0.15)', borderRadius: 16, padding: 22 };
const h3Style = { margin: '0 0 16px', fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 14, color: '#eef4f0' };
const ctaBtnStyle = { display: 'flex', alignItems: 'center', gap: 9, padding: '11px 20px', borderRadius: 10, border: 'none', cursor: 'pointer', fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 14, color: '#04140d', background: 'linear-gradient(135deg,#3ee7a6,#22c79b)' };
const ghostBtnStyle = { display: 'flex', alignItems: 'center', gap: 9, padding: '11px 20px', borderRadius: 10, cursor: 'pointer', fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 14, color: '#cfe0d8', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(120,150,180,0.25)' };
const sendBtnStyle = { display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 10, border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg,#3ee7a6,#22c79b)', color: '#04140d', flexShrink: 0 };
const agentIconStyle = { width: 32, height: 32, borderRadius: 9, flexShrink: 0, display: 'grid', placeItems: 'center', background: 'linear-gradient(140deg,#0d2a22,#103a30)', border: '1px solid rgba(52,211,153,0.35)' };
