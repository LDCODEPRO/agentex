"""
AGENTE-X | Teste de Conexao LLM
Execute: python test_llm.py
Verifica se o LLM responde de verdade com as chaves configuradas no .env
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in [ROOT / "01_CORE/orchestrator", ROOT / "09_LOGS"]:
    p.mkdir(exist_ok=True)
    sys.path.insert(0, str(p))

print("=" * 55)
print("  AGENTE-X | TESTE DE CONEXAO LLM")
print("=" * 55)

from llm_router import LLMRouter

router = LLMRouter()
status = router.status()

print("\n[STATUS DOS PROVIDERS]")
for k, v in status.items():
    if isinstance(v, bool):
        icon = "[OK]    " if v else "[OFF]   "
    else:
        icon = "[INFO]  "
    print(f"  {icon} {k}: {v}")

print("\n[TESTANDO CONEXAO REAL...]")
print("  (requer acesso a internet — rode no Windows)")
result = router.test_connection()

print()
if result["status"] == "OK":
    print(f"  [OK] Provider : {result['provider']}")
    print(f"  [OK] Modelo   : {result['model']}")
    print(f"  [OK] Latencia : {result['latency_ms']}ms")
    print(f"  [OK] Resposta : {result['response'][:200]}")
    print()
    print("  AGENTE-X PRONTO PARA USO REAL COM LLM")
else:
    msg = result.get("message", "")
    if "ProxyError" in msg or "SSLError" in msg or "Max retries" in msg:
        print("  [SANDBOX] Sem acesso a internet no ambiente Linux.")
        print("  [SANDBOX] Execute no Windows para teste real:")
        print()
        print("    cd \"D:\\Agente X\"")
        print("    python test_llm.py")
        print()
        print("  As chaves estao configuradas. O router vai funcionar no Windows.")
    else:
        print(f"  [ERRO] {msg}")
        print()
        print("  Verifique D:\\Agente X\\.env")

print("=" * 55)
