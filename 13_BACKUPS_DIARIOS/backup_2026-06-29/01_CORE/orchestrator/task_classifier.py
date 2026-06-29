# TASK CLASSIFIER — HYBRID COGNITIVE CLASSIFICATION SYSTEM
# Path: 01_CORE/llm_router/task_classifier.py

import re

class TaskClassifier:
    ALLOWED_TYPES = [
        "GENERAL_CHAT", "FAST_SUMMARY", "CLASSIFICATION", "ARCHITECTURE",
        "CODING", "FORENSIC", "PRIVACY", "OFFLINE", "DEBUGGING", "MISSION_EXECUTION",
        "GOVERNANCE", "MEMORY", "MONITORING", "SYNC"
    ]

    @staticmethod
    def classify(prompt, explicit_task=None):
        """
        Classifies a task using a hybrid pipeline (keywords, semantic hints, structure, risk).
        Returns a dictionary:
        {
          "task_type": str,
          "confidence": float,
          "reason": str
        }
        """
        if explicit_task:
            explicit_task = explicit_task.upper()
            if explicit_task in TaskClassifier.ALLOWED_TYPES:
                return {
                    "task_type": explicit_task,
                    "confidence": 1.0,
                    "reason": "Forçado explicitamente pelo chamador"
                }

        prompt_lower = prompt.lower()
        scores = {t: 0.0 for t in TaskClassifier.ALLOWED_TYPES}
        reasons = {t: [] for t in TaskClassifier.ALLOWED_TYPES}

        # --- 1. KEYWORD & SEMANTIC HINTS MATCHING ---
        keywords = {
            "SYNC": ["git", "sync", "commit", "push", "pull", "rebase", "branch", "repositório", "sincronizar", "upstream"],
            "MONITORING": ["monitor", "dashboard", "telemetria", "canvas", "métricas", "health", "gráfico", "port 4177", "servidor monitor"],
            "GOVERNANCE": ["governança", "governance", "política", "policy", "regra", "restrição", "crivo", "risk block", "bloquear", "permitido", "proibido"],
            "MEMORY": ["memória", "memory", "recall", "stm", "consolidar", "armazenar contexto", "esquecimento", "long-context"],
            "PRIVACY": ["sk-", ".env", "api_key", "secret", "senha", "password", "token", "cofre", "credenciais", "privacidade"],
            "FORENSIC": ["forense", "auditoria", "audit", "forensic", "veracidade", "evidência", "hash", "prova real", "vestígio"],
            "MISSION_EXECUTION": ["missão:", "missao:", "protocolo:", "prioridade:", "executar missão", "meta:", "task queue", "scheduler"],
            "ARCHITECTURE": ["arquitetura", "architecture", "diagrama", "mermaid", "design pattern", "estrutura lógica", "uml", "módulos"],
            "CODING": ["def ", "class ", "import ", "function", "código", "script", "refatorar", "python", "javascript", "html", "css"],
            "DEBUGGING": ["erro", "error", "bug", "traceback", "exception", "falha", "corrige", "resolva"],
            "FAST_SUMMARY": ["resuma", "resumo", "summarize", "summary", "tldr", "tldr;", "breve relato"],
            "CLASSIFICATION": ["classifique", "categorize", "liste as tags", "tipo de", "confidence score"]
        }

        for task, words in keywords.items():
            for w in words:
                if w in prompt_lower:
                    scores[task] += 0.25
                    reasons[task].append(f"keyword '{w}'")

        # --- 2. STRUCTURE DETECTION ---
        # Markdown title indicating a mission
        if re.search(r"^#+\s+miss[ãa]o:", prompt_lower, re.MULTILINE):
            scores["MISSION_EXECUTION"] += 0.4
            reasons["MISSION_EXECUTION"].append("Estrutura de Cabeçalho de Missão detectada")

        # Mermaid block indicates Architecture
        if "```mermaid" in prompt_lower:
            scores["ARCHITECTURE"] += 0.5
            reasons["ARCHITECTURE"].append("Bloco de diagrama Mermaid detectado")

        # Python exception pattern
        if "traceback (most recent call last)" in prompt_lower or re.search(r"\w+error:", prompt_lower):
            scores["DEBUGGING"] += 0.5
            reasons["DEBUGGING"].append("Padrão de Traceback/Exceção detectado")

        # --- 3. RISK DETECTION ---
        # Operations affecting the system config
        if any(w in prompt_lower for w in ["apagar", "deletar", "excluir", "modificar config", "alterar cofre"]):
            scores["GOVERNANCE"] += 0.3
            reasons["GOVERNANCE"].append("Termos de risco operacional detectados")

        # --- 4. SELECTION AND CONFIDENCE SCORING ---
        best_task = "GENERAL_CHAT"
        best_score = 0.0
        
        for task, score in scores.items():
            if score > best_score:
                best_score = score
                best_task = task

        # Normalize confidence (max out at 0.95 for heuristic model)
        confidence = min(0.95, round(best_score, 2))
        
        if confidence < 0.55 or best_task == "GENERAL_CHAT":
            best_task = "GENERAL_CHAT"
            confidence = max(0.50, confidence)
            reason = "Prompt geral sem intenção específica forte detectada"
        else:
            matched_triggers = ", ".join(reasons[best_task][:3])
            reason = f"Intenção detectada via: {matched_triggers}"

        return {
            "task_type": best_task,
            "confidence": confidence,
            "reason": reason
        }
