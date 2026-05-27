"""
AGENTE-X | Relatórios Automáticos de Governança
Zero Ghost: Usa hashlib e SQLite reais para provar resultados.
"""
import hashlib
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

class ReportGenerator:
    def __init__(self):
        self.reports_dir = _ROOT / "06_REPORTS"
        self.evidence_dir = _ROOT / "10_EVIDENCE"
        self.reports_dir.mkdir(exist_ok=True)
        self.evidence_dir.mkdir(exist_ok=True)

    def generate_mission_report(self, mission_code: str, status: str, results: list):
        # Gerar SHA256 do resultado para integridade Zero Ghost
        raw_data = json.dumps(results, sort_keys=True).encode("utf-8")
        evidence_hash = hashlib.sha256(raw_data).hexdigest()
        
        report_content = f"""# MISSION REPORT: {mission_code}
**Status Final:** {status}
**Evidência SHA256:** {evidence_hash}
**Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Resultados
```json
{json.dumps(results, indent=2)}
```

## Próximas Ações
- Validar logs em 09_LOGS correspondentes a {mission_code}.
"""
        # Salvar em 06_REPORTS
        report_path = self.reports_dir / f"{mission_code}_report.md"
        report_path.write_text(report_content, encoding="utf-8")
        
        # Salvar evidência
        evidence_path = self.evidence_dir / f"{mission_code}_{evidence_hash[:8]}.json"
        evidence_path.write_text(json.dumps({"hash": evidence_hash, "data": results}), encoding="utf-8")
        
        return str(report_path)
