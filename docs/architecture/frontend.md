# Frontend

## Stack

- **React 18** com hooks
- **Vite** para build e dev server
- **Ant Design** para componentes UI
- **Tailwind CSS** para utilitários

## Estrutura

```
src/
├── pages/              # Páginas da aplicação
│   ├── Aprovacoes/     # Tela de aprovações
│   ├── PreAgenda/      # Pré-agenda (publicação)
│   ├── Solicitacoes/   # Gestão de solicitações
│   ├── Dashboards/     # Dashboards e métricas
│   └── DATModule/      # Módulo DAT
├── components/         # Componentes reutilizáveis
├── api/                # Funções de chamada API
├── hooks/              # React hooks customizados
└── utils/              # Utilitários
```

## Páginas Principais

| Rota | Descrição |
|------|-----------|
| `/solicitacoes` | Lista de solicitações |
| `/solicitacoes/nova` | Nova solicitação |
| `/aprovacoes` | Aprovação (Superintendência) |
| `/pre-agenda` | Publicação no GCal (Controle) |
| `/dashboards` | Dashboards e métricas |
| `/controle/compras` | Compras do domínio Controle (`core_compra`) |
| `/dat/compras-materiais` | Compras de materiais DAT (`core_dat_compra`) |

## Autenticação

- Session-based authentication
- CSRF token em todas as requisições
- Sessão expira em 2 horas

## Componentes Chave

### RemoteSelect

Select com busca remota para entidades:

```jsx
<RemoteSelect
  fetchOptions={fetchMunicipios}
  renderLabel={(item) => item.nome}
  placeholder="Selecione um município"
/>
```

### MeetLink

Exibe link do Google Meet:

```jsx
<MeetLink href={solicitacao.meet_link} />
```
