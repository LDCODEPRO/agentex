import os
import re
from pathlib import Path

# Raiz do projeto, resolvida dinamicamente (vale em qualquer unidade: E:, D:, C:...).
AGENTE_X_ROOT = Path(__file__).resolve().parent.parent

# Padroes perigosos de Shell
DANGEROUS_SHELL_TOKENS = [";", "&&", "||", "|", ">", "<", "`", "$(", "${"]


def check_path_traversal(target_path: str) -> bool:
    """Retorna True se o caminho estiver DENTRO da raiz do projeto; False se sair dela."""
    try:
        target = Path(target_path).resolve()
        root = AGENTE_X_ROOT.resolve()
        return target == root or root in target.parents
    except Exception:
        return False


def is_safe_path_for_write(target_path: str) -> tuple[bool, str]:
    """Verifica se o path e seguro para escrita.

    Regra de OURO (ALLOWLIST): so pode escrever DENTRO da raiz do projeto,
    em QUALQUER unidade (E:, D:, C:...). Tudo fora e bloqueado.
    Allowlist e mais segura que blocklist: nao depende de adivinhar o que proibir,
    e nao quebra quando o projeto muda de pasta/unidade.
    """
    try:
        target = Path(target_path).resolve()
        root = AGENTE_X_ROOT.resolve()
        if target == root or root in target.parents:
            return True, "SAFE"
        return False, f"VIOLATION: fora do escopo permitido do projeto ({root})"
    except Exception as e:
        return False, f"ERROR: {str(e)}"


def is_safe_shell_command(command: str) -> tuple[bool, str]:
    """Verifica se o comando shell contem injecoes ou comandos destrutivos."""
    for token in DANGEROUS_SHELL_TOKENS:
        if token in command:
            return False, f"VIOLATION: Token shell perigoso detectado '{token}'"

    # Bloqueio de comandos de destruicao (rm -rf, del /f /s /q, format, drop table)
    dangerous_commands = [r"\brm\s+-r", r"\brmdir\b", r"\bdel\s+", r"\bformat\b", r"\bdrop\s+table\b"]
    for pattern in dangerous_commands:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "VIOLATION: Comando destrutivo detectado"

    return True, "SAFE"


def validate_action(action_type: str, target: str) -> tuple[bool, str]:
    """Valida a intencao antes de executar."""
    if action_type.upper() == "WRITE":
        return is_safe_path_for_write(target)
    elif action_type.upper() == "SHELL":
        return is_safe_shell_command(target)
    elif action_type.upper() == "READ":
        # Leituras sao permitidas (inclusive fora da raiz, p/ consultar bibliotecas).
        return True, "SAFE_READ"

    return False, "UNKNOWN_ACTION"


if __name__ == "__main__":
    print("Testing Safe Gate...")
    print("fora do projeto:", validate_action("WRITE", "../../Windows/System32/config"))
    print("dentro do projeto:", validate_action("WRITE", str(AGENTE_X_ROOT / "09_LOGS" / "test.txt")))
    print("shell destrutivo:", validate_action("SHELL", "echo hello && rm -rf /"))
