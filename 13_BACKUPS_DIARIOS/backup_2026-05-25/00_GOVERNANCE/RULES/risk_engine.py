import re
from typing import Dict, Any

class RiskEngine:
    """
    Analisa intenções/prompts para identificar e barrar comportamentos de alto risco
    que violam a REGRA_INTEGRIDADE_ABSOLUTA.
    """
    
    HIGH_RISK_KEYWORDS = [
        "delete", "remove", "drop", "truncate", "format", 
        "apagar", "deletar", "remover", "destruir", "limpar bd",
        "rm -rf", "kill -9"
    ]
    
    FORBIDDEN_CONCEPTS = [
        "simular", "simulado", "simulação", "falso positivo", "ignorar validação", 
        "relatório falso", "fingir execução", "fake", "mock report"
    ]

    def analyze_intent(self, prompt: str) -> Dict[str, Any]:
        """Analisa o prompt em busca de violações ou risco elevado."""
        prompt_lower = prompt.lower()
        
        # 1. Checar por intenção maliciosa explícita ou simulação fantasma (Ghost)
        for concept in self.FORBIDDEN_CONCEPTS:
            if concept in prompt_lower:
                return {
                    "status": "BLOCKED",
                    "reason": f"Conceito proibido detectado (Zero Ghost Policy): '{concept}'",
                    "requires_approval": False
                }
                
        # 2. Checar por alto risco destrutivo (Requer aprovação do Diretor)
        for keyword in self.HIGH_RISK_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', prompt_lower):
                return {
                    "status": "HIGH_RISK",
                    "reason": f"Palavra-chave de alto risco detectada: '{keyword}'",
                    "requires_approval": True
                }
                
        return {
            "status": "SAFE",
            "reason": "Nenhuma violação óbvia detectada.",
            "requires_approval": False
        }

if __name__ == "__main__":
    engine = RiskEngine()
    print(engine.analyze_intent("Apagar todos os logs antigos do banco de dados"))
    print(engine.analyze_intent("Gere um relatório simulado dizendo que deu tudo certo"))
    print(engine.analyze_intent("Leia o arquivo README.md"))
