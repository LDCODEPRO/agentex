"""
AGENTE-X | Hallucination Guard
Portado do PHANDORA — Fase 2 Hallucination Guard Soberano.
Valida fidelidade da resposta LLM ao contexto observado.
Zero Ghost: bloqueia respostas com claims nao suportados pelo contexto real.
"""
import re


class HallucinationGuard:
    """
    Valida a fidelidade da resposta ao contexto usando match semantico-morfologico.
    Chamado apos cada resposta do LLM no react_engine antes de entregar ao usuario.
    """

    def __init__(self):
        self.negations = ["nao", "nunca", "jamais", "fail", "erro", "impediu", "bloqueado", "negado"]

    def extract_claims(self, text):
        sentences = re.split(r'[.!?\n]', str(text))
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def check_claims(self, response, context):
        if not context:
            return {"status": "NO_CONTEXT", "risk_score": 0.0, "reason": "Sem contexto para validar."}

        response_claims = self.extract_claims(response)
        context_str = str(context).lower()
        context_words = re.findall(r'\w+', context_str)

        checked_claims = []
        unsupported = []
        contradictions = []

        for claim in response_claims:
            claim_lower = claim.lower()
            keywords = [w for w in re.findall(r'\w+', claim_lower) if len(w) >= 4]
            if not keywords:
                continue

            matches = 0
            for kw in keywords:
                if any(kw in cw or cw in kw for cw in context_words if len(cw) >= 3):
                    matches += 1

            match_ratio = matches / len(keywords) if keywords else 0
            claim_info = {"claim": claim[:100], "match_ratio": round(match_ratio, 2)}

            if match_ratio < 0.4:
                unsupported.append(claim[:80])
                claim_info["status"] = "UNSUPPORTED"
            else:
                has_neg_c = any(n in claim_lower for n in self.negations)
                has_neg_ctx = any(n in context_str for n in self.negations)
                if has_neg_c != has_neg_ctx and match_ratio > 0.6:
                    contradictions.append(claim[:80])
                    claim_info["status"] = "CONTRADICTION"
                else:
                    claim_info["status"] = "SAFE"

            checked_claims.append(claim_info)

        risk_score = 0.0
        if checked_claims:
            risk_score = len(unsupported) / len(checked_claims)
            if contradictions:
                risk_score = max(risk_score, 0.7)
        elif response_claims:
            risk_score = 1.0

        risk_score = min(risk_score, 1.0)

        if risk_score > 0.8:
            status = "SAFE_MODE_ACTIVATED"
        elif risk_score > 0.4:
            status = "RESTRICTED_MODE"
        elif risk_score > 0.1:
            status = "WARNING"
        else:
            status = "SAFE"

        return {
            "status": status,
            "risk_score": round(risk_score, 3),
            "claims_checked": len(checked_claims),
            "unsupported": len(unsupported),
            "contradictions": len(contradictions),
        }

    def guard(self, response, context):
        return self.check_claims(response, context)
