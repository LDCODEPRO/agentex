"""
AGENTE-X | Mission Validator
Valida se a missão realmente cumpriu seus objetivos (prova).
"""
import logging

logger = logging.getLogger("MissionValidator")

class MissionValidator:
    def validate_step(self, step: dict, result: dict) -> bool:
        """
        Valida a execução de um step.
        (Integrará mais tarde com a Validation Engine dedicada).
        """
        if result.get("status") == "ERROR":
            logger.warning(f"Step {step.get('id')} falhou na execução.")
            return False
            
        output = result.get("output", "")
        # Zero Ghost: não podemos apenas aceitar SUCCESS se não houver output substancial
        if not output or len(output) < 5:
            logger.warning(f"Step {step.get('id')} não produziu output válido.")
            return False
            
        logger.info(f"Step {step.get('id')} validado com sucesso.")
        return True

    def validate_mission(self, plan: dict, results: list) -> bool:
        """
        Valida a missão inteira.
        """
        if len(results) != len(plan.get("steps", [])):
            return False
            
        return all(r.get("validated", False) for r in results)
