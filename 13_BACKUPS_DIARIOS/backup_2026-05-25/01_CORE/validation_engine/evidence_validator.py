"""
AGENTE-X | Evidence Validator
Comprova integridade de arquivos de evidência via SHA256 e consistência de tamanho.
"""
import hashlib
from pathlib import Path

class EvidenceValidator:
    def validate_evidence(self, filepath: str, expected_hash: str = None) -> bool:
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            return False
            
        if expected_hash:
            # Calcular o hash real e comparar
            with open(path, "rb") as f:
                raw_bytes = f.read()
                file_hash = hashlib.sha256(raw_bytes).hexdigest()
            return file_hash == expected_hash
            
        return path.stat().st_size > 0
