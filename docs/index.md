# Aprender Sistema v2

Plataforma web para gestão de eventos, formações e solicitações do programa Aprender.

## Visão Geral

O **Aprender Sistema (AS) v2** substitui planilhas Google/Excel por uma plataforma web automatizada, oferecendo:

- **Gestão de Solicitações**: Criação, aprovação e acompanhamento de eventos
- **Verificação de Conflitos**: Validação automática de disponibilidade de formadores
- **Integração Google Calendar**: Publicação automática de eventos com Google Meet
- **RBAC Completo**: Controle de acesso baseado em Setor + Função
- **Auditoria**: Logs completos de todas as operações

## Stack Tecnológica

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.12, Django 5.2 LTS, DRF 3.16, Celery |
| **Frontend** | React (Vite), Tailwind CSS, Ant Design |
| **Banco de Dados** | PostgreSQL 15 |
| **Cache/Filas** | Redis 7 |
| **Infraestrutura** | Docker, Docker Compose |

## Links Rápidos

- [Instalação](getting-started/installation.md)
- [Arquitetura](architecture/overview.md)
- [Regras de Negócio](business-rules/clausulas-petreas.md)
- [API Reference](api/models.md)

## Repositório

[:fontawesome-brands-github: GitHub](https://github.com/matheusnorjosa/aprender_sistema){ .md-button }
