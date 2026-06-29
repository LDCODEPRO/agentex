"""
AGENTE-X | Base Tool
Contrato base para todas as ferramentas do agente.
"""
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Toda ferramenta deve herdar desta classe e implementar execute().
    name        — identificador usado no ReAct loop (ex: 'file_tool')
    description — descrição injetada no prompt do LLM
    parameters  — dict descrevendo parâmetros esperados (para o prompt)
    """
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Executa a ferramenta com os parâmetros fornecidos.
        Deve retornar sempre uma string (resultado ou mensagem de erro).
        Nunca retornar None ou lançar exceção silenciosa.
        """
        ...

    def schema(self) -> str:
        """Retorna a descrição formatada para injeção no prompt do LLM."""
        params = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"- {self.name}({params}): {self.description}"
