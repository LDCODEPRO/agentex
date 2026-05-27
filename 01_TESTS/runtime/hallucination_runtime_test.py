"""
AGENTE-X | Hallucination Runtime Test
Garante que o FAIL CLOSED funciona na prática.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "01_CORE" / "orchestrator"))

from react_engine import ReActEngine

def test_hallucination_block():
    print("Testando injeção de alucinação pura...")
    engine = ReActEngine()
    
    # Forçar o ReAct a processar algo onde ele cria fatos infundados.
    # Como não temos mock do LLM aqui sem pytest completo, simulamos injetando
    # direto na guarda para validar o log e o SAFE MODE.
    
    response = "Eu acessei o servidor da NASA ontem e confirmei que aliens existem lá."
    context = "O agente X apenas tem acesso ao seu próprio banco de dados SQLite local."
    
    # Simularemos a chamada do router
    class DummyRouter:
        def route(self, prompt, system):
            return {"response": response, "provider": "mock"}
            
    engine.router = DummyRouter()
    
    # Forçar history para ativar hguard context validation
    # Modificamos o max steps para terminar no step 1
    
    result = engine.run(goal="Fale sobre o servidor da NASA", verbose=False)
    
    if "SAFE_MODE" in result:
        print("\n✅ SUCESSO: Hallucination Guard interceptou e ativou SAFE_MODE (FAIL CLOSED).")
    else:
        print(f"\n❌ FALHA: O agente falhou em FAIL CLOSED. Resultado: {result}")
        sys.exit(1)

if __name__ == "__main__":
    test_hallucination_block()
