import { useState } from 'react';
import { api } from './api';

export default function Login({ onLoggedIn }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(password);
      onLoggedIn();
    } catch {
      setError('Senha incorreta.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#070a0f', color: '#e6edf3', fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <form onSubmit={submit} style={{
        width: 320, background: '#10151e', border: '1px solid rgba(96,128,160,0.15)',
        borderRadius: 16, padding: '32px 28px',
      }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, margin: '0 auto 18px', display: 'grid',
          placeItems: 'center', background: 'linear-gradient(140deg,#0d2a22,#103a30)',
          border: '1px solid rgba(52,211,153,0.4)',
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
            <path d="M12 3v18M4 7.5l8 4.5 8-4.5" />
          </svg>
        </div>
        <div style={{ textAlign: 'center', fontFamily: "'Space Grotesk',sans-serif", fontWeight: 700, fontSize: 16, letterSpacing: 1.5, marginBottom: 22 }}>
          AGENTE X
        </div>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Senha do cockpit"
          style={{
            width: '100%', background: '#0a0e14', border: '1px solid rgba(96,128,160,0.2)',
            borderRadius: 10, padding: '11px 14px', color: '#e6edf3', fontSize: 14, outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        {error && <div style={{ marginTop: 10, fontSize: 12.5, color: '#f87171' }}>{error}</div>}
        <button type="submit" disabled={loading} style={{
          marginTop: 16, width: '100%', padding: '11px 0', borderRadius: 10, border: 'none',
          cursor: 'pointer', fontFamily: "'Space Grotesk'", fontWeight: 600, fontSize: 14,
          color: '#04140d', background: 'linear-gradient(135deg,#3ee7a6,#22c79b)',
          opacity: loading ? 0.7 : 1,
        }}>
          {loading ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
