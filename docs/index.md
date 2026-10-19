# Aprender Sistema v2

Plataforma web para gestão de eventos, formações e solicitações do programa Aprender.

## Visão Geral

O **Aprender Sistema (AS) v2** substitui planilhas Google/Excel por uma plataforma web automatizada, oferecendo:

- **Gestão de Solicitações**: Criação, aprovação e acompanhamento de eventos
- **Verificação de Conflitos**: Validação automática de disponibilidade de formadores
- **Integração Google Calendar**: Publicação automática de eventos com Google Meet
- **RBAC por capabilities**: Usuário → Lotação (gerência + papel) → pacote do perfil da gerência + direitos do papel → Capabilities → Policies nas rotas. O grupo Django é etiqueta; só soma poder em `RBAC_FONTE=uniao`, a volta de emergência
- **Auditoria**: Trilha de `AuditLog` nas operações sensíveis

## Stack Tecnológica

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.12, Django 5.2 LTS, DRF 3.17, Celery 5.5 |
| **Frontend** | React 19, TypeScript 5, Vite 7, Tailwind CSS 3, Ant Design 5 |
| **Banco de Dados** | PostgreSQL 15 |
| **Cache/Filas** | Redis 7 |
| **Infraestrutura** | Docker, Docker Compose |

## Links Rápidos

- [Instalação](getting-started/installation.md)
- [Arquitetura](architecture/overview.md)
- [Regras de Negócio](business-rules/clausulas-petreas.md)
- [RBAC e Permissões](guides/rbac.md)
- [API Reference](api/models.md)
- [Decisões Arquiteturais (ADRs)](architecture/project-decisions/README.md)
- [Deploy](operations/deploy.md)

## Repositório

[:fontawesome-brands-github: GitHub](https://github.com/matheusnorjosa/aprender_sistema){ .md-button }
