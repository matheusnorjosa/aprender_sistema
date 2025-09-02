# ANÁLISE PRE-MIGRAÇÃO - PADRONIZAÇÃO DE DADOS

## PROBLEMA IDENTIFICADO

O command de migração está falhando porque:
1. **Modelo Usuario** herda de `AbstractUser` (campos Django padrão)
2. **Dados extraídos** têm estrutura das planilhas (campos customizados)
3. **Mapeamento incorreto** entre estruturas diferentes

## MODELO ATUAL vs DADOS EXTRAÍDOS

### Modelo Django Usuario (AbstractUser):
```python
class Usuario(AbstractUser):
    # Campos herdados do AbstractUser:
    - username (obrigatório, único)
    - first_name
    - last_name  
    - email (único)
    - is_active
    - is_staff
    - is_superuser
    - date_joined
    - last_login
    
    # Roles via Django Groups (não campo direto)
    - groups (ManyToMany)
```

### Dados das Planilhas:
```json
{
    "Nome": "João Silva",
    "Nome Completo": "João Silva Santos", 
    "CPF": "12345678901",
    "Email": "joao@email.com",
    "Telefone": "85999999999",
    "Município": "Fortaleza",
    "Perfil": "Coordenador",
    "Observações": "..."
}
```

## ESTRATÉGIA DE PADRONIZAÇÃO NECESSÁRIA

### 1. MAPEAMENTO CORRETO DOS CAMPOS:

| Campo Planilha | Campo Django | Transformação |
|----------------|--------------|---------------|
| Nome | first_name | Primeiro nome apenas |
| Nome Completo | first_name + last_name | Dividir em partes |
| Email | username + email | Email como username |
| CPF | ❌ Não existe | Precisa criar campo customizado |
| Telefone | ❌ Não existe | Precisa criar campo customizado |
| Perfil | groups | Criar/vincular Groups Django |
| Município | ❌ Não existe | Relação com Municipio |

### 2. DECISÕES DE DESIGN:

**Opção A: Estender AbstractUser**
```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True)
    telefone = models.CharField(max_length=15, blank=True)
    municipio = models.ForeignKey(Municipio, null=True, blank=True)
```

**Opção B: User Profile separado**
```python
class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=11, unique=True)
    telefone = models.CharField(max_length=15, blank=True) 
    municipio = models.ForeignKey(Municipio, null=True, blank=True)
```

## PIPELINE DE PRÉ-PROCESSAMENTO

### Etapa 1: Análise dos dados extraídos
- Verificar campos únicos (CPF, Email)
- Identificar dados faltantes
- Validar formatos (CPF, email, telefone)
- Mapear perfis para Groups Django

### Etapa 2: Limpeza e padronização
- Normalizar CPF (apenas números)
- Padronizar telefones (DDD + número)
- Dividir nome completo
- Limpar emails (lowercase, trim)

### Etapa 3: Validação cruzada
- CPFs duplicados
- Emails duplicados  
- Perfis inexistentes
- Municípios não cadastrados

### Etapa 4: Transformação para Django
- Criar usernames únicos (baseado em email)
- Mapear perfis para Groups
- Vincular municípios existentes
- Definir senhas padrão

## PROPOSTA DE IMPLEMENTAÇÃO

### 1. Estender modelo Usuario:
```python
class Usuario(AbstractUser):
    # Campos adicionais necessários
    cpf = models.CharField(max_length=11, unique=True, blank=True)
    telefone = models.CharField(max_length=15, blank=True)
    municipio = models.ForeignKey('Municipio', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Método para compatibilidade
    @property
    def nome_completo(self):
        return f"{self.first_name} {self.last_name}".strip()
```

### 2. Criar Groups Django:
```python
# Grupos baseados nos perfis das planilhas
GRUPOS_SISTEMA = [
    'superintendencia',
    'coordenador', 
    'formador',
    'admin'
]
```

### 3. Pipeline de transformação:
```python
def transform_usuario_data(record):
    nome_completo = record['Nome Completo']
    partes_nome = nome_completo.split()
    
    return {
        'username': record['Email'].lower(),
        'email': record['Email'].lower(),  
        'first_name': partes_nome[0] if partes_nome else record['Nome'],
        'last_name': ' '.join(partes_nome[1:]) if len(partes_nome) > 1 else '',
        'cpf': clean_cpf(record['CPF']),
        'telefone': clean_phone(record['Telefone']),
        'is_active': True,
        # Perfil será tratado via Groups após criação
    }
```

## PRÓXIMOS PASSOS RECOMENDADOS:

1. **Criar migração** para adicionar campos ao Usuario
2. **Criar Groups Django** para perfis do sistema  
3. **Implementar pipeline** de pré-processamento
4. **Validar dados** antes da importação
5. **Testar migração** com dados limpos

**PERGUNTA**: Prefere estender o modelo Usuario atual ou criar um profile separado?