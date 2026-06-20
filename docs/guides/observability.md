# Observabilidade

Monitoramento e logging do AS v2.

> **Importante:** Prometheus + Grafana são **locais/opcionais** (`make up-obs`) e **NÃO rodam em produção**. Em prod o app só expõe `/metrics` (gated por staff/IP interno) para scraping externo do provedor + Sentry **se** `SENTRY_DSN` estiver setado (atualmente OFF).
>
> **SSOT**: tabela dev × prod, versões da stack, mapa de portas e logging em **[OBSERVABILITY.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/OBSERVABILITY.md)**.
