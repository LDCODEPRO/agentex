"""
AGENTE-X | Runtime Validator
Inspeciona se processos críticos ou módulos estão carregados na memória.
"""
import sys

class RuntimeValidator:
    def validate_module_loaded(self, module_name: str) -> bool:
        return module_name in sys.modules

    def validate_variable_truth(self, variable_name: str, context: dict) -> bool:
        return bool(context.get(variable_name))
