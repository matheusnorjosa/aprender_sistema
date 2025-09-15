# Dados Extraídos das Planilhas Originais

Esta pasta contém todos os dados extraídos das planilhas originais do Sistema Aprender.

## Arquivos Incluídos

### Backups Completos
- `backup_sqlite_data.json` - Backup completo dos dados originais
- `backup_sqlite_data_utf8.json` - Backup com encoding UTF-8

### Dados Específicos (Formato JSON)
- `disponibilidades_exemplo.json` - Dados de disponibilidade dos formadores
- `municipios_exemplo.json` - Lista de municípios brasileiros
- `projetos_exemplo.json` - Projetos educacionais
- `tipos_evento_exemplo.json` - Tipos de eventos formativos

### Dados Específicos (Formato CSV)
- `disponibilidades_exemplo.csv` - Disponibilidades em formato CSV
- `municipios_exemplo.csv` - Municípios em formato CSV  
- `projetos_exemplo.csv` - Projetos em formato CSV
- `tipos_evento_exemplo.csv` - Tipos de evento em formato CSV

## Status Atual do Sistema

### ✅ Dados Reais Importados
- **123 usuários** (CPFs reais das planilhas)
- **82 formadores** (dados reais com emails válidos) 
- **59 municípios** (dados reais + exemplos brasileiros)
- **8 projetos** (projetos educacionais reais)
- **6 tipos de evento** (modalidades de formação)

### ❌ Dados de Teste Removidos
- **0 solicitações de teste** (todas removidas)
- **3 formadores de teste** (emails @local removidos)
- **1 usuário de teste** (diretoria_teste removido)

## Como Usar

1. **Para importar dados**: Use os comandos Django de importação
2. **Para backup**: Use os arquivos JSON completos  
3. **Para desenvolvimento**: Sistema agora usa apenas dados reais

## Data da Limpeza
- **Data**: 13/09/2025
- **Responsável**: Sistema automatizado
- **Status**: ✅ Dados limpos e organizados