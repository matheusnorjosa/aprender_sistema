# Teste de Credenciais Anthropic/Claude

## Status

- **anthropic disponível:** ✗ Não
- **Credenciais testadas:** ✗ Não
- **ANTHROPIC_API_KEY:** ✗ Não definida

## Resultado

ANTHROPIC_API_KEY não definida

## Próximos Passos


1. Obter API key em https://console.anthropic.com/
2. Definir variável de ambiente:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Instalar anthropic se necessário:
   ```bash
   pip install anthropic
   ```
4. Testar com chamada simples:
   ```python
   import anthropic
   client = anthropic.Anthropic()
   message = client.messages.create(
       model="claude-3-sonnet-20240229",
       max_tokens=100,
       messages=[{"role": "user", "content": "Hello"}]
   )
   print(message.content)
   ```
