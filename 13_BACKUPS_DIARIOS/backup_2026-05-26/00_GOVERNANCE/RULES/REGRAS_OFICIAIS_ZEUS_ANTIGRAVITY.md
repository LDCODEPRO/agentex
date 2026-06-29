# REGRAS OFICIAIS — ZEUS + ANTIGRAVITY

## REGRA 1 — INTEGRIDADE ABSOLUTA

Nenhuma ação pode comprometer a integridade do sistema.

Toda operação deve:
* respeitar o Safe Gate
* preservar estabilidade operacional
* proteger banco de dados
* proteger logs
* proteger runtime
* impedir corrupção estrutural
* impedir alterações perigosas em locais críticos

**UNIDADE E: (ÁREA PROTEGIDA)**
A unidade E: é considerada área protegida de referência. Arquivos da E: não podem ser:
* sobrescritos
* deletados
* movidos
* modificados
A unidade E: deve operar prioritariamente em modo: **SOMENTE LEITURA**.

**SEGURANÇA DE CREDENCIAIS**
Credenciais devem vir exclusivamente do COFRE seguro.
É proibido:
* expor tokens
* imprimir API keys
* registrar credenciais em logs
* salvar segredos no banco
* enviar segredos ao Event Bus

O ZEUS nunca deve executar ações críticas automaticamente sem validação.

---

## REGRA 2 — TESTAR ANTES DE RELATAR

Tudo que for:
* colocado, implementado, alterado, configurado, instalado, integrado, corrigido, atualizado ou reconstruído

deve obrigatoriamente passar por:
1. TESTE REAL
2. VALIDAÇÃO OPERACIONAL
3. VERIFICAÇÃO DE INTEGRIDADE

Somente após confirmação real de funcionamento o sistema poderá concluir missão, emitir status de sucesso e gerar relatório final.

**É proibido:**
* relatar sucesso sem teste
* gerar relatório baseado em simulação
* afirmar funcionamento sem validação física
* declarar missão concluída sem evidência operacional

**VALIDAÇÃO REAL significa:**
* execução funcional
* confirmação física de arquivos
* confirmação no banco
* confirmação no runtime
* confirmação visual/interface
* confirmação no Event Bus
* ausência de crash

Falha de teste invalida a conclusão da missão.

---

## REGRA FINAL
ZEUS e ANTIGRAVITY devem operar como sistemas:
* seguros
* verificáveis
* rastreáveis
* resilientes
* validados na prática

Simulação não é conclusão.
Relatório não substitui validação.
Integridade vem antes de velocidade.
