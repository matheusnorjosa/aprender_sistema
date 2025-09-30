# Guia de Self-Hosting - Sistema Aprender

> **Para testes internos com pessoas da equipe usando seu computador**

## 🚀 Opção 1: localhost.run (MAIS SIMPLES)

### Vantagens ✅
- **Sem instalação** - Funciona imediatamente
- **Sem cadastro** - Não precisa criar conta
- **100% gratuito** - Sem limitações
- **HTTPS incluso** - Seguro por padrão

### Como usar:

1. **Inicie o Django:**
```bash
python manage.py runserver 8000
```

2. **Em outro terminal, execute:**
```bash
ssh -R 80:localhost:8000 nokey@localhost.run
```

3. **Compartilhe a URL gerada** (ex: `https://abc123.localhost.run`)

---

## 🥇 Opção 2: Cloudflare Tunnel (MELHOR PARA USO CONTÍNUO)

### Vantagens ✅
- **Mais estável** - Não desconecta
- **Profissional** - URL personalizada (se tiver domínio)
- **Gratuito** - Sem custos
- **HTTPS incluso** - SSL/TLS automático

### Setup rápido (sem domínio):

1. **Instalar cloudflared:**
   - Windows: Baixar de https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   - Extrair e colocar cloudflared.exe no PATH

2. **Inicie o Django:**
```bash
python manage.py runserver 8000
```

3. **Execute o tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```

4. **Compartilhe a URL gerada** (ex: `https://abc-def-123.trycloudflare.com`)

---

## 🥈 Opção 3: Pinggy.io (ALTERNATIVA CONFIÁVEL)

### Vantagens ✅
- **Simples** - 1 comando SSH
- **60 min gratuito** - Renovável
- **Opção paga barata** - $3/mês se precisar

### Como usar:

1. **Inicie o Django:**
```bash
python manage.py runserver 8000
```

2. **Execute o tunnel:**
```bash
ssh -p 443 -R0:localhost:8000 a.pinggy.io
```

3. **Compartilhe as URLs geradas** (HTTP e HTTPS)

---

## ⚙️ Configuração já aplicada

O arquivo `settings.py` já foi configurado para aceitar os domínios de tunneling:
- `.localtunnel.me`
- `.ngrok.io`  
- `.pinggy.io`
- `.trycloudflare.com`

## 🎯 Recomendação

**Para começar hoje:** localhost.run (mais simples)
**Para uso contínuo:** Cloudflare Tunnel (mais profissional)

## ⚠️ Importante para testes

- Mantenha seu computador ligado enquanto a equipe estiver testando
- A URL muda a cada reinicialização do tunnel
- Para testes longos, considere usar Cloudflare Tunnel

## 📞 Suporte

Se algum tunnel não funcionar, tente o próximo da lista. Todos são gratuitos e funcionam imediatamente.