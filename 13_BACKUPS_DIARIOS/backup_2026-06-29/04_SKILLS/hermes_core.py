"""
AGENTE-X | Hermes Core
Portado do Sistema Open Claude — nucleo de aprendizado autonomo.
Fornece: SOUL + MEMORY + SKILLS em formato Hermes para qualquer agente do ecossistema.

Baseado nos padroes do Hermes Agent (Nous Research) e adaptado para AGENTE-X.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

_ROOT       = Path(__file__).resolve().parent.parent.parent
_SOULS_DIR  = _ROOT / "12_CONFIG" / "souls"
_MEMORY_DIR = _ROOT / "02_MEMORY" / "agents"
_SKILLS_DIR = _ROOT / "04_SKILLS" / "skill_md"


def _ensure_dirs():
    for d in [_SOULS_DIR, _MEMORY_DIR, _SKILLS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── SOUL ──────────────────────────────────────────────────────────────────

def carregar_soul(agente_id: str = "agente_x") -> str:
    """Carrega SOUL.md do agente. Fallback para 12_CONFIG/SOUL.md principal."""
    _ensure_dirs()
    # Primeiro tenta soul especifica do agente
    soul_file = _SOULS_DIR / f"{agente_id}.md"
    if soul_file.exists():
        return soul_file.read_text(encoding="utf-8").strip()
    # Fallback: SOUL.md principal do AGENTE-X
    main_soul = _ROOT / "12_CONFIG" / "SOUL.md"
    if main_soul.exists():
        return main_soul.read_text(encoding="utf-8").strip()
    return ""


def salvar_soul(agente_id: str, conteudo: str) -> bool:
    """Cria ou atualiza a soul de um agente especifico."""
    _ensure_dirs()
    try:
        (_SOULS_DIR / f"{agente_id}.md").write_text(conteudo, encoding="utf-8")
        return True
    except Exception:
        return False


# ── MEMORY ────────────────────────────────────────────────────────────────

def carregar_memoria(agente_id: str = "agente_x") -> dict:
    """Carrega memoria persistente do agente (JSON em disco)."""
    _ensure_dirs()
    mem_file = _MEMORY_DIR / f"{agente_id}.json"
    if mem_file.exists():
        try:
            return json.loads(mem_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "agente": agente_id,
        "criado_em": datetime.now().isoformat(),
        "fatos": [],
        "padroes": [],
        "erros_conhecidos": [],
        "ultima_atualizacao": None,
    }


def salvar_memoria(agente_id: str, memoria: dict) -> bool:
    """Persiste memoria do agente. Cap: 500 fatos."""
    _ensure_dirs()
    try:
        mem_file = _MEMORY_DIR / f"{agente_id}.json"
        memoria["ultima_atualizacao"] = datetime.now().isoformat()
        if len(memoria.get("fatos", [])) > 500:
            memoria["fatos"] = memoria["fatos"][-400:]
        mem_file.write_text(
            json.dumps(memoria, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception:
        return False


def aprender_fato(agente_id: str, fato: str, categoria: str = "geral") -> bool:
    """Registra fato aprendido na memoria do agente."""
    mem = carregar_memoria(agente_id)
    mem.setdefault("fatos", []).append({
        "ts": datetime.now().isoformat(),
        "categoria": categoria,
        "fato": fato,
    })
    return salvar_memoria(agente_id, mem)


def registrar_erro_conhecido(agente_id: str, erro: str, solucao: str) -> bool:
    """Registra erro que o agente ja sabe resolver."""
    mem = carregar_memoria(agente_id)
    mem.setdefault("erros_conhecidos", []).append({
        "ts": datetime.now().isoformat(),
        "erro": erro,
        "solucao": solucao,
    })
    return salvar_memoria(agente_id, mem)


def resumo_memoria(agente_id: str = "agente_x", max_fatos: int = 10) -> str:
    """Retorna N fatos recentes como string para injetar no prompt."""
    mem = carregar_memoria(agente_id)
    fatos = mem.get("fatos", [])[-max_fatos:]
    if not fatos:
        return ""
    linhas = ["[MEMORIA PERSISTENTE]"]
    for f in fatos:
        linhas.append(f"- [{f.get('categoria','?')}] {f.get('fato','')}")
    erros = mem.get("erros_conhecidos", [])[-3:]
    if erros:
        linhas.append("[ERROS CONHECIDOS E SOLUCOES]")
        for e in erros:
            linhas.append(f"- ERRO: {e.get('erro','')} → SOLUCAO: {e.get('solucao','')}")
    return "\n".join(linhas)


# ── SKILLS (formato SKILL.md) ─────────────────────────────────────────────

def listar_skills(agente_id: str = "agente_x") -> list:
    """Lista skills SKILL.md do agente."""
    _ensure_dirs()
    skills_dir = _SKILLS_DIR / agente_id
    if not skills_dir.exists():
        return []
    skills = []
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                conteudo = skill_file.read_text(encoding="utf-8")
                descricao = ""
                for linha in conteudo.splitlines():
                    if linha.startswith("description:"):
                        descricao = linha.split(":", 1)[1].strip()
                        break
                skills.append({
                    "nome": skill_dir.name,
                    "descricao": descricao,
                    "arquivo": str(skill_file),
                })
    return skills


def carregar_skill(agente_id: str, skill_nome: str) -> str:
    """Carrega conteudo completo de uma skill SKILL.md."""
    skill_file = _SKILLS_DIR / agente_id / skill_nome / "SKILL.md"
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return ""


def criar_skill(agente_id: str, skill_nome: str, quando_usar: str,
                procedimento: str, armadilhas: str = "",
                verificacao: str = "", descricao: str = "") -> bool:
    """Cria nova SKILL.md para o agente. Chame apos resolver problema de 5+ tool calls."""
    _ensure_dirs()
    try:
        skill_dir = _SKILLS_DIR / agente_id / skill_nome
        skill_dir.mkdir(parents=True, exist_ok=True)
        conteudo = f"""---
name: {skill_nome}
description: {descricao or quando_usar[:80]}
version: 1.0.0
author: {agente_id}
created: {datetime.now().strftime('%Y-%m-%d')}
metadata:
  tags: [{agente_id}, agente-x]
  category: {agente_id}
---

# {skill_nome.replace('-', ' ').title()}

## Quando Usar
{quando_usar}

## Procedimento
{procedimento}

## Armadilhas
{armadilhas if armadilhas else "- Nenhuma registrada ainda."}

## Verificacao
{verificacao if verificacao else "- Confirmar que o resultado esperado foi atingido."}
"""
        (skill_dir / "SKILL.md").write_text(conteudo, encoding="utf-8")
        aprender_fato(agente_id, f"Skill criada: '{skill_nome}' — {descricao}", "skill_criada")
        return True
    except Exception:
        return False


def atualizar_skill(agente_id: str, skill_nome: str, old_string: str, new_string: str) -> bool:
    """Atualiza (patch) skill existente — mais eficiente que reescrever."""
    skill_file = _SKILLS_DIR / agente_id / skill_nome / "SKILL.md"
    if not skill_file.exists():
        return False
    try:
        conteudo = skill_file.read_text(encoding="utf-8")
        if old_string not in conteudo:
            return False
        skill_file.write_text(conteudo.replace(old_string, new_string, 1), encoding="utf-8")
        return True
    except Exception:
        return False


def deletar_skill(agente_id: str, skill_nome: str) -> bool:
    """Remove skill obsoleta. Arquiva em .archive/ antes de deletar."""
    skill_dir = _SKILLS_DIR / agente_id / skill_nome
    if not skill_dir.exists():
        return False
    try:
        archive = _SKILLS_DIR / agente_id / ".archive" / skill_nome
        archive.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            shutil.move(str(skill_file), str(archive / "SKILL.md"))
        return True
    except Exception:
        return False


def indice_skills(agente_id: str = "agente_x") -> str:
    """Indice compacto de skills para injetar no prompt (progressive disclosure)."""
    skills = listar_skills(agente_id)
    if not skills:
        return ""
    linhas = [f"[SKILLS — {agente_id.upper()}]"]
    for s in skills:
        linhas.append(f"- {s['nome']}: {s['descricao']}")
    return "\n".join(linhas)


# ── CONTEXTO COMPLETO ─────────────────────────────────────────────────────

def contexto_hermes(agente_id: str = "agente_x", max_fatos: int = 8) -> str:
    """
    Monta contexto completo Hermes: SOUL + MEMORY + SKILLS INDEX.
    Injete no inicio do system prompt do agente.
    """
    partes = []
    soul = carregar_soul(agente_id)
    if soul:
        partes.append(soul)
    mem = resumo_memoria(agente_id, max_fatos)
    if mem:
        partes.append(mem)
    idx = indice_skills(agente_id)
    if idx:
        partes.append(idx)
    return "\n\n".join(partes)


# ── RELATORIO ─────────────────────────────────────────────────────────────

def relatorio_hermes(agentes: list = None) -> dict:
    """Saude do sistema de aprendizado autonomo."""
    agentes = agentes or ["agente_x"]
    relatorio = {"ts": datetime.now().isoformat(), "agentes": {}}
    for aid in agentes:
        skills = listar_skills(aid)
        mem = carregar_memoria(aid)
        relatorio["agentes"][aid] = {
            "soul": (_SOULS_DIR / f"{aid}.md").exists()
                    or (_ROOT / "12_CONFIG" / "SOUL.md").exists(),
            "skills_md": len(skills),
            "fatos": len(mem.get("fatos", [])),
            "erros_conhecidos": len(mem.get("erros_conhecidos", [])),
        }
    return relatorio


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(relatorio_hermes(), indent=2))
