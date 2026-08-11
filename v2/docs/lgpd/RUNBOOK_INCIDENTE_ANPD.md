# Runbook — Resposta a Incidente de Dados Pessoais (LGPD art. 48) — SCAFFOLD

> ⚠️ **Andaime.** Preencha os campos `[A PREENCHER]` (contatos, prazos internos, autoridade
> de decisão) com o Encarregado (DPO) e o jurídico. A LGPD não fixa um prazo numérico único;
> a comunicação à ANPD e aos titulares deve ser feita **em prazo razoável** — trate como
> **urgente** (referência operacional: iniciar em até **2 dias úteis** da ciência).

## Papéis

| Papel | Quem | Contato |
|-------|------|---------|
| Encarregado (DPO) | `[A PREENCHER]` | `[A PREENCHER]` |
| Responsável técnico (on-call) | `[A PREENCHER]` | `[A PREENCHER]` |
| Decisão/porta-voz (jurídico/diretoria) | `[A PREENCHER]` | `[A PREENCHER]` |

## Fluxo

### 1. Detecção e registro (imediato)
- Registrar: quem detectou, data/hora, como foi detectado, sistemas/dados aparentemente afetados.
- Abrir um registro do incidente (ticket/planilha de incidentes — `[A PREENCHER: onde]`).
- Acionar o Encarregado e o responsável técnico.

### 2. Contenção (horas)
- Estancar o vazamento/acesso indevido: revogar credenciais, isolar host, rotacionar segredos
  (`REDIS_PASSWORD`, `DB_PASSWORD`, chaves OAuth/Fernet), bloquear IP, etc.
- **Não** destruir evidências — preservar logs (AuditLog, logs de app, acesso do servidor).

### 3. Avaliação (1–2 dias)
- Quais **categorias de dados** e quantos **titulares**? (CPF, e-mail, telefone, cargo, agenda…)
- Houve **exposição efetiva** ou apenas risco? Dados estavam cifrados?
- **Risco aos titulares** (fraude, discriminação, dano). Isso define a extensão da comunicação.

### 4. Comunicação (prazo razoável — tratar como urgente)
- **À ANPD**: comunicar quando houver risco/dano relevante aos titulares. Canal e formulário
  oficiais da ANPD: `[A PREENCHER: link/procedimento vigente]`. Conteúdo mínimo: natureza dos
  dados, titulares envolvidos, medidas técnicas/de segurança, riscos e medidas adotadas/​propostas.
- **Aos titulares afetados**: comunicar quando houver risco/dano relevante, em linguagem clara.
  Canal: `[A PREENCHER]`.
- Aprovar o texto com jurídico/porta-voz antes de enviar.

### 5. Registro e prestação de contas (art. 37)
- Consolidar o registro do incidente: linha do tempo, decisão sobre notificar (com justificativa
  se **não** notificar), comunicações enviadas, evidências.
- Guardar por `[A PREENCHER: prazo de retenção do registro]`.

### 6. Pós-incidente (dias/semanas)
- Causa-raiz + ações corretivas (fechar a falha, não só o sintoma).
- Revisar controles: acesso, segredos, backup/restore, monitoramento.
- Lições aprendidas → atualizar este runbook e a base técnica.

## Comandos úteis (referência técnica)

- Trilha de auditoria: `AuditLog` (por usuário/ação/período). Export de um titular:
  `python manage.py lgpd_export --cpf=<cpf> --output=<arquivo>`.
- Rotação de segredos: via Portainer (produção) — ver `v2/docs/DEPLOY_CHECKLIST` / `project_prod_secrets`.
- Auditoria de compliance PA/RD: `python manage.py compliance_audit --days=<n> --format=json`.

## Referências

- LGPD arts. 46 (segurança), 48 (comunicação de incidente), 37 (registro), 18 (direitos).
- Base técnica de suporte: backups cifrados (`age`), TLS, RBAC, retenção automática, anonimização.
