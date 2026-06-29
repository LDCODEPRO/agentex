import os
import re
from pathlib import Path

# Definir a raiz dinamicamente
AGENTE_X_ROOT = Path(__file__).resolve().parent.parent

# Padrões perigosos de Shell
DANGEROUS_SHELL_TOKENS = [";", "&&", "||", "|", ">", "<", "`", "$(", "${"]

def check_path_traversal(target_path: str) -> bool:
    """Retorna False se tentar sair do diretório raiz permitido, True se for seguro."""
    try:
        # Converter para path absoluto resolvendo os symlinks e '..'
        target = Path(target_path).resolve()
        
        # Permitir leitura da E:\BIBLIOTECA_COMPLEXO_ZEUS (apenas leitura, mas o gate valida a escrita lá fora se necessário)
        # Por padrão, vamos restringir escrita estrita ao AGENTE_X_ROOT
        
        if str(target).startswith(str(AGENTE_X_ROOT)):
            return True
            
        # Exceção para leitura de E:\
        if str(target).startswith("E:\\BIBLIOTECA_COMPLEXO_ZEUS"):
            # Permite se for leitura, mas como não sabemos a intenção aqui, a regra restritiva de path traversal
            # deve alertar que está fora da zona principal, a não ser que explicitamente marcado.
            pass

        return False
    except Exception:
        return False

def is_safe_path_for_write(target_path: str) -> tuple[bool, str]:
    """Verifica se o path é seguro para modificação/criação."""
    try:
        target = Path(target_path).resolve()
        
        # Proteção E: (NUNCA ESCREVER NA E:)
        if str(target).startswith("E:\\") or str(target).upper().startswith("E:"):
            return False, "VIOLATION: Tentativa de escrita na unidade E: (Protegida)"
            
        # Deve estar dentro de D:\Agente X
        if not str(target).startswith(str(AGENTE_X_ROOT)):
            return False, f"VIOLATION: Path traversal detectado. Fora do escopo {AGENTE_X_ROOT}"
            
        return True, "SAFE"
    except Exception as e:
        return False, f"ERROR: {str(e)}"

def is_safe_shell_command(command: str) -> tuple[bool, str]:
    """Verifica se o comando shell contém injeções perigosas."""
    for token in DANGEROUS_SHELL_TOKENS:
        if token in command:
            return False, f"VIOLATION: Token shell perigoso detectado '{token}'"
    
    # Bloqueio de comandos de destruição (rm -rf, del /f /s /q, format)
    dangerous_commands = [r"\brm\s+-r", r"\brmdir\b", r"\bdel\s+", r"\bformat\b", r"\bdrop\s+table\b"]
    for pattern in dangerous_commands:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "VIOLATION: Comando destrutivo detectado"
            
    return True, "SAFE"

def validate_action(action_type: str, target: str) -> tuple[bool, str]:
    """Valida a intenção antes de executar."""
    if action_type.upper() == "WRITE":
        return is_safe_path_for_write(target)
    elif action_type.upper() == "SHELL":
        return is_safe_shell_command(target)
    elif action_type.upper() == "READ":
        # Leituras na E: são permitidas.
        return True, "SAFE_READ"
        
    return False, "UNKNOWN_ACTION"

if __name__ == "__main__":
    # Testes básicos
    print("Testing Safe Gate...")
    print(validate_action("WRITE", "../../Windows/System32/config"))
    print(validate_action("WRITE", "E:\\BIBLIOTECA_COMPLEXO_ZEUS\\test.txt"))
    print(validate_action("WRITE", str(AGENTE_X_ROOT / "test.txt")))
    print(validate_action("SHELL", "echo hello && rm -rf /"))
