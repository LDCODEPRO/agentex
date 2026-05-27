"""
AGENTE-X | Mission Templates
Templates estruturais e grafos lógicos para as missões.
"""
import json

class MissionTemplates:
    @staticmethod
    def get_template(goal: str) -> dict:
        """
        Retorna um plano inicial com base no objetivo.
        Em um sistema FASE 5, usaria LLM. Na FASE 4 (atual), usamos
        regras base para evitar dependências lentas ou falhas.
        """
        # Exemplo simples de template de auditoria ou implementação
        if "auditoria" in goal.lower() or "audit" in goal.lower():
            return {
                "steps": [
                    {"id": "step_1", "task": "Coletar evidências do disco e banco de dados"},
                    {"id": "step_2", "task": "Analisar estrutura e gerar log de conformidade"},
                    {"id": "step_3", "task": "Redigir relatório final em 08_AUDITS"}
                ]
            }
        else:
            return {
                "steps": [
                    {"id": "step_1", "task": f"Planejamento inicial para: {goal}"},
                    {"id": "step_2", "task": "Execução core da tarefa"},
                    {"id": "step_3", "task": "Validação pós-execução"}
                ]
            }
