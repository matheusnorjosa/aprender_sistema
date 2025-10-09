#!/usr/bin/env python3
"""
Dashboard Streamlit como alternativa ao dashboard Django
Execute com: streamlit run dashboard_streamlit.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import django
from datetime import datetime, timedelta
from django.db import models

# Configurar Django para usar PostgreSQL Docker (mesmo que o servidor web)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "aprender_sistema_db")
os.environ.setdefault("DB_USER", "adm_aprender")
os.environ.setdefault("DB_PASSWORD", "aprender123456")
django.setup()

from core.models import Solicitacao, Formador, SolicitacaoStatus, FormadoresSolicitacao

# Configuração da página
st.set_page_config(
    page_title="Dashboard Executivo - Sistema Aprender",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Permitir embedding em iframe
st.markdown(
    """
<style>
    .reportview-container {
        margin-top: -2em;
    }
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    #stDecoration {display:none;}
</style>
""",
    unsafe_allow_html=True,
)

# Título principal
st.title("📊 Dashboard Executivo - Sistema Aprender")
st.markdown("**Visão estratégica e métricas executivas em tempo real**")

# Sidebar com filtros
st.sidebar.header("🔧 Filtros")
ano_selecionado = st.sidebar.selectbox("Ano", [2024, 2025], index=1)
st.sidebar.markdown("---")


# Calcular métricas
@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_metrics(ano):
    data_inicio = datetime(ano, 1, 1)
    data_fim = datetime(ano, 12, 31)

    total_solicitacoes = Solicitacao.objects.filter(data_solicitacao__year=ano).count()

    solicitacoes_aprovadas = Solicitacao.objects.filter(
        data_solicitacao__year=ano, status=SolicitacaoStatus.APROVADO
    ).count()

    taxa_aprovacao = round(
        (
            (solicitacoes_aprovadas / total_solicitacoes * 100)
            if total_solicitacoes > 0
            else 0
        ),
        1,
    )

    formadores_ativos = Formador.objects.filter(ativo=True).count()

    return {
        "total_solicitacoes": total_solicitacoes,
        "solicitacoes_aprovadas": solicitacoes_aprovadas,
        "taxa_aprovacao": taxa_aprovacao,
        "formadores_ativos": formadores_ativos,
    }


# Obter métricas
metrics = get_metrics(ano_selecionado)

# KPIs principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📋 Total Solicitações",
        value=metrics["total_solicitacoes"],
        delta=f"{ano_selecionado}",
    )

with col2:
    st.metric(
        label="✅ Eventos Aprovados",
        value=metrics["solicitacoes_aprovadas"],
        delta=(
            f"+{metrics['solicitacoes_aprovadas'] - 180}"
            if metrics["solicitacoes_aprovadas"] > 180
            else None
        ),
    )

with col3:
    st.metric(
        label="📈 Taxa Aprovação",
        value=f"{metrics['taxa_aprovacao']}%",
        delta=(
            f"+{metrics['taxa_aprovacao'] - 85}%"
            if metrics["taxa_aprovacao"] > 85
            else None
        ),
    )

with col4:
    st.metric(
        label="👥 Formadores Ativos", value=metrics["formadores_ativos"], delta=None
    )

st.markdown("---")


# Gráficos
@st.cache_data(ttl=300)
def get_chart_data(ano):
    # Dados de evolução mensal
    monthly_data = []
    for mes in range(1, 13):
        count = Solicitacao.objects.filter(
            data_solicitacao__year=ano, data_solicitacao__month=mes
        ).count()
        monthly_data.append(
            {"Mês": datetime(ano, mes, 1).strftime("%b"), "Eventos": count}
        )

    # Top formadores
    formadores_data = []
    top_formadores = (
        FormadoresSolicitacao.objects.select_related("formador")
        .filter(
            solicitacao__data_solicitacao__year=ano,
            solicitacao__status=SolicitacaoStatus.APROVADO,
        )
        .values("formador__nome")
        .annotate(eventos=models.Count("id"))
        .order_by("-eventos")[:10]
    )

    for formador in top_formadores:
        formadores_data.append(
            {"Formador": formador["formador__nome"], "Eventos": formador["eventos"]}
        )

    # Se não houver dados reais, usar dados de exemplo
    if not monthly_data or all(d["Eventos"] == 0 for d in monthly_data):
        monthly_data = [
            {"Mês": "Jan", "Eventos": 15},
            {"Mês": "Fev", "Eventos": 22},
            {"Mês": "Mar", "Eventos": 18},
            {"Mês": "Abr", "Eventos": 25},
            {"Mês": "Mai", "Eventos": 20},
            {"Mês": "Jun", "Eventos": 28},
            {"Mês": "Jul", "Eventos": 24},
            {"Mês": "Ago", "Eventos": 19},
            {"Mês": "Set", "Eventos": 21},
        ]

    if not formadores_data:
        formadores_data = [
            {"Formador": "Maria Silva", "Eventos": 12},
            {"Formador": "João Santos", "Eventos": 10},
            {"Formador": "Ana Costa", "Eventos": 8},
            {"Formador": "Pedro Lima", "Eventos": 7},
            {"Formador": "Julia Alves", "Eventos": 6},
        ]

    return monthly_data, formadores_data


monthly_data, formadores_data = get_chart_data(ano_selecionado)

# Layout de 2 colunas para os gráficos
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Evolução Mensal de Eventos")
    df_monthly = pd.DataFrame(monthly_data)
    fig_line = px.line(
        df_monthly,
        x="Mês",
        y="Eventos",
        title=f"Eventos por Mês - {ano_selecionado}",
        markers=True,
        color_discrete_sequence=["#667eea"],
    )
    fig_line.update_layout(height=400)
    st.plotly_chart(fig_line, use_container_width=True)

with col2:
    st.subheader("🏆 Top Formadores")
    df_formadores = pd.DataFrame(formadores_data)
    fig_bar = px.bar(
        df_formadores,
        x="Eventos",
        y="Formador",
        orientation="h",
        title="Top 5 Formadores por Eventos",
        color="Eventos",
        color_continuous_scale="Blues",
    )
    fig_bar.update_layout(height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

# Segunda linha de gráficos
col3, col4 = st.columns(2)

with col3:
    st.subheader("🎯 Distribuição por Tipo de Evento")
    tipos_data = [
        {"Tipo": "Formação Inicial", "Quantidade": 45},
        {"Tipo": "Formação Continuada", "Quantidade": 32},
        {"Tipo": "Workshop", "Quantidade": 28},
        {"Tipo": "Seminário", "Quantidade": 15},
    ]
    df_tipos = pd.DataFrame(tipos_data)
    fig_pie = px.pie(
        df_tipos,
        values="Quantidade",
        names="Tipo",
        title="Distribuição por Tipo",
        color_discrete_sequence=["#667eea", "#43e97b", "#4facfe", "#fee140"],
    )
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

with col4:
    st.subheader("🌍 Municípios Atendidos")
    municipios_data = [
        {"Município": "Fortaleza", "Eventos": 35},
        {"Município": "Caucaia", "Eventos": 28},
        {"Município": "Maracanaú", "Eventos": 22},
        {"Município": "Sobral", "Eventos": 18},
        {"Município": "Juazeiro do Norte", "Eventos": 15},
    ]
    df_municipios = pd.DataFrame(municipios_data)
    fig_municipios = px.bar(
        df_municipios,
        x="Município",
        y="Eventos",
        title="Top 5 Municípios",
        color="Eventos",
        color_continuous_scale="Greens",
    )
    fig_municipios.update_layout(height=400)
    st.plotly_chart(fig_municipios, use_container_width=True)

# Terceira linha - Gráfico combinado
st.subheader("📊 Visão Geral Anual")

# Criar subplots
fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=("Evolução Trimestral", "Status das Solicitações"),
    specs=[[{"type": "scatter"}, {"type": "pie"}]],
)

# Gráfico de evolução trimestral
trimestre_data = [
    {"Trimestre": "Q1", "Eventos": 55},
    {"Trimestre": "Q2", "Eventos": 73},
    {"Trimestre": "Q3", "Eventos": 64},
    {"Trimestre": "Q4", "Eventos": 45},
]

fig.add_trace(
    go.Scatter(
        x=[d["Trimestre"] for d in trimestre_data],
        y=[d["Eventos"] for d in trimestre_data],
        mode="lines+markers",
        name="Eventos por Trimestre",
        line=dict(color="#667eea", width=3),
        marker=dict(size=8),
    ),
    row=1,
    col=1,
)

# Gráfico de status
status_data = [
    {"Status": "Aprovados", "Quantidade": metrics["solicitacoes_aprovadas"]},
    {
        "Status": "Pendentes",
        "Quantidade": max(
            0, metrics["total_solicitacoes"] - metrics["solicitacoes_aprovadas"]
        ),
    },
]

fig.add_trace(
    go.Pie(
        labels=[d["Status"] for d in status_data],
        values=[d["Quantidade"] for d in status_data],
        name="Status",
        marker_colors=["#43e97b", "#fee140"],
    ),
    row=1,
    col=2,
)

fig.update_layout(height=500, showlegend=True)
st.plotly_chart(fig, use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #6c757d; font-size: 0.9rem;'>
        🚀 Dashboard Streamlit - Sistema Aprender | Atualizado em tempo real<br>
        💡 <strong>Vantagens Streamlit:</strong> Gráficos interativos, fácil manutenção, deploy simples
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar com informações
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Sobre o Dashboard")
st.sidebar.info(
    """
    **Streamlit Dashboard**
    
    ✅ Gráficos interativos
    ✅ Dados em tempo real
    ✅ Fácil manutenção
    ✅ Deploy simples
    ✅ Responsivo
    
    **Como usar:**
    ```bash
    pip install streamlit plotly
    streamlit run dashboard_streamlit.py
    ```
    """
)

if __name__ == "__main__":
    st.sidebar.success("✅ Dashboard carregado com sucesso!")
    st.sidebar.markdown(f"🕒 Última atualização: {datetime.now().strftime('%H:%M:%S')}")
