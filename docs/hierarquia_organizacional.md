# Hierarquia Organizacional - Sistema Aprender

## 📊 **Estrutura Organizacional Atual**

### 🏢 **Modelo de Setores**
O sistema utiliza o modelo `Setor` para representar a estrutura organizacional:

```python
class Setor(models.Model):
    nome = CharField(max_length=100, unique=True)
    sigla = CharField(max_length=20, unique=True) 
    vinculado_superintendencia = BooleanField(default=False)
    ativo = BooleanField(default=True)
```

**Campos principais:**
- `vinculado_superintendencia`: Define se projetos do setor requerem aprovação
- `sigla`: Abreviação para identificação (ex: SUPER, VIDAS, LOC)

### 🎯 **Setores Cadastrados**

#### **Superintendência** (vinculado_superintendencia=True)
- **Sigla**: SUPER
- **Característica**: Projetos requerem aprovação da superintendência
- **Projetos**: AMMA, CATAVENTOS, CIRANDAR, ESCREVER COMUNICAR E SER, Lendo e Escrevendo, MIUDEZAS, Novo Lendo, TEMA, TRÂNSITO LEGAL (todos), UNI DUNI TÊ

#### **Setores Não-Superintendência** (vinculado_superintendencia=False)
1. **Vidas** (VIDAS) - Vida e Matemática, Vida e Ciências, Vida e Linguagem
2. **ACerta** (ACERTA) - ACerta Matemática, ACerta Língua Portuguesa  
3. **Brincando e Aprendendo** (BRINC) - Brincando e Aprendendo
4. **Fluir das Emoções** (FLUIR) - Fluir
5. **IDEB 10** (IDEB) - IDEB 10
6. **Ler, Ouvir e Contar** (LOC) - A Cor da Gente, Avançando Juntos, Educação Financeira, Ler Ouvir e Contar, Sou da Paz

## 👥 **Estrutura Hierárquica por Setor**

### **Hierarquia Padrão (Cada Setor)**
```
Setor
├── Gerente(s)
│   ├── Coordenador(es)  
│   │   ├── Apoio(s) de Coordenação
│   │   └── Formador(es)
│   └── Formador(es) (vinculação direta)
└── Usuários Administrativos (Controle, RH, etc.)
```

### **Modelo Usuario - Campos Organizacionais**
```python
class Usuario(AbstractUser):
    setor = ForeignKey("Setor", null=True, blank=True)
    cargo = CharField(choices=CARGO_CHOICES)
    municipio = ForeignKey("Municipio", null=True, blank=True)
    
CARGO_CHOICES = [
    ("gerente", "Gerente"),
    ("coordenador", "Coordenador"), 
    ("apoio_coordenacao", "Apoio de Coordenação"),
    ("formador", "Formador"),
    ("controle", "Controle"),
    ("admin", "Administrador"),
    ("outros", "Outros"),
]
```

## 🎭 **Papéis Funcionais vs Grupos Django**

### **Relação Cargo ↔ Grupos**
- **cargo**: Campo informativo no modelo Usuario
- **groups**: Sistema de permissões Django (grupos de autorização)

**Um usuário pode ter:**
- 1 cargo funcional (ex: "coordenador") 
- Múltiplos grupos Django (ex: "coordenador" + "admin")

### **Grupos Ativos no Sistema**
1. **coordenador** (37 usuários) - Pode criar solicitações
2. **superintendencia** (10 usuários) - Aprova/reprova solicitações
3. **controle** (1 usuário) - Gerencia pré-agenda e Google Calendar
4. **formador** (73 usuários) - Visualiza eventos próprios, cria bloqueios
5. **diretoria** (1 usuário) - Visualiza relatórios
6. **admin** (1 usuário) - Acesso administrativo completo
7. **gerente** (10 usuários) - Supervisiona disponibilidade e solicitações
8. **apoio_coordenacao** (0 usuários) - Sem permissões específicas
9. **gerente_aprender** (0 usuários) - Sem permissões específicas

### **Novos Grupos Organizacionais** (Preparados para expansão)
- **rh** (0 usuários) - Recursos Humanos
- **logistica** (0 usuários) - Logística  
- **financeiro** (0 usuários) - Financeiro
- **editorial** (0 usuários) - Editorial

## 🔄 **Fluxo Organizacional**

### **Processo de Solicitação**
1. **Coordenador** cria solicitação para projeto específico
2. **Sistema verifica**: `projeto.setor.vinculado_superintendencia`
3. **Se vinculado à superintendência**: → Aprovação pelos **gerentes da superintendência**
4. **Se não vinculado**: → Direto para **pré-agenda (grupo controle)**
5. **Controle** cria evento no Google Calendar
6. **Formadores** visualizam eventos alocados

### **Validação das Regras**
✅ **Implementado corretamente** no código:
```python
# core/views/solicitacao_views.py linha 114-118
def _requer_aprovacao_superintendencia(self, solicitacao):
    if solicitacao.projeto.setor:
        return solicitacao.projeto.setor.vinculado_superintendencia
    return solicitacao.projeto.vinculado_superintendencia  # fallback
```

## 📈 **Estatísticas Atuais**
- **Total de usuários**: 123 (distribuídos em 13 grupos)
- **Formadores cadastrados**: 73 usuários no grupo + 2 registros na tabela Formador
- **Projetos total**: 27 projetos
  - **Vinculados à superintendência**: 14 projetos
  - **Não vinculados**: 13 projetos
- **Setores ativos**: 7 setores

## ✅ **Conclusões**
1. **Estrutura hierárquica**: Totalmente representável no modelo atual
2. **Separação papéis/grupos**: Clara distinção entre função (cargo) e autorização (groups)  
3. **Fluxo de aprovação**: Implementado corretamente com base em `setor.vinculado_superintendencia`
4. **Formadores**: Permissões adequadas (apenas visualização + bloqueios)
5. **Expansibilidade**: Novos grupos organizacionais já criados para futuras funcionalidades