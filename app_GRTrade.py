import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuração da Página
st.set_page_config(
    page_title="Day Trade Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS para aproximar ao layout escuro/verde das imagens
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    div[data-testid="metric-container"] {
        background-color: #161a22;
        border: 1px solid #242b35;
        padding: 15px;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #00c853;
        color: white;
        border-radius: 8px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSÃO DE AUTENTICAÇÃO -----------------
def login():
    st.markdown("<h2 style='text-align: center;'>Day Trade Dashboard - Login</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if username == st.secrets["credentials"]["username"] and password == st.secrets["credentials"]["password"]:
                st.session_state["logged_in"] = True
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ----------------- CONEXÃO COM O GOOGLE SHEETS -----------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="operacoes", ttl="0s")
    # Se a planilha estiver vazia (só com cabeçalhos) ou sem linhas
    if df.empty or len(df) == 0:
        # Cria um DataFrame vazio com as colunas corretas e tipos definidos
        df = pd.DataFrame(columns=['data', 'ativo', 'lado', 'contratos', 'resultado', 'observacoes'])
        df['data'] = pd.to_datetime(df['data'])
        df['resultado'] = pd.to_numeric(df['resultado'])
        return df
    
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    df['resultado'] = pd.to_numeric(df['resultado'], errors='coerce').fillna(0.0)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar os dados. Verifique a estrutura da planilha ou credenciais. Detalhe: {e}")
    st.stop()

# ----------------- SIDEBAR & FILTROS -----------------
st.sidebar.title("Navegação & Filtros")

# Garante que as colunas auxiliares existam mesmo se o df estiver vazio
if not df.empty and df['data'].notna().any():
    df['ano'] = df['data'].dt.year
    df['mes_nome'] = df['data'].dt.strftime('%b')
    df['mes_num'] = df['data'].dt.month
    anos_disponiveis = sorted(df['ano'].dropna().unique(), reverse=True)
else:
    df['ano'] = datetime.today().year
    df['mes_nome'] = datetime.today().strftime('%b')
    df['mes_num'] = datetime.today().month
    anos_disponiveis = [datetime.today().year]

ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis)

# Tipo de Filtro Temporal
tipo_filtro = st.sidebar.radio("Período", ["Ano Inteiro", "Mês Específico", "Período Personalizado (Estratégia)"])

# Aplicação dos filtros de data
if not df.empty and df['data'].notna().any():
    df_filtrado = df[df['ano'] == ano_selecionado]
else:
    df_filtrado = df.copy()

if tipo_filtro == "Mês Específico" and not df_filtrado.empty:
    meses_nomes = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
    mes_selecionado = st.sidebar.selectbox("Mês", list(meses_nomes.keys()))
    df_filtrado = df_filtrado[df_filtrado['data'].dt.month == meses_nomes[mes_selecionado]]

elif tipo_filtro == "Período Personalizado (Estratégia)" and not df_filtrado.empty:
    data_inicio = st.sidebar.date_input("Início", df['data'].min() if df['data'].notna().any() else datetime.today())
    data_fim = st.sidebar.date_input("Fim", df['data'].max() if df['data'].notna().any() else datetime.today())
    df_filtrado = df_filtrado[(df_filtrado['data'].dt.date >= data_inicio) & (df_filtrado['data'].dt.date <= data_fim)]

# Ordenar por data
if not df_filtrado.empty:
    df_filtrado = df_filtrado.sort_values(by='data')

# ----------------- CÁLCULO DE MÉTRICAS (KPIs) -----------------
total_resultado = df_filtrado['resultado'].sum() if not df_filtrado.empty else 0.0
total_operacoes = len(df_filtrado)

if total_operacoes > 0:
    vitoriosas = df_filtrado[df_filtrado['resultado'] > 0]
    derrotas = df_filtrado[df_filtrado['resultado'] < 0]
    win_rate = (len(vitoriosas) / total_operacoes * 100)
    media_ganho = vitoriosas['resultado'].mean() if len(vitoriosas) > 0 else 0.0
    media_perda = derrotas['resultado'].mean() if len(derrotas) > 0 else 0.0
else:
    win_rate = 0.0
    media_ganho = 0.0
    media_perda = 0.0

# ----------------- CABEÇALHO DO DASHBOARD -----------------
st.title("📈 Day Trade Dashboard")
st.caption("Registro diário e performance por mês e ano")

# Linha de KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("RESULTADO", f"R$ {total_resultado:,.2f}")
col2.metric("OPERAÇÕES", f"{total_operacoes}")
col3.metric("WIN RATE", f"{win_rate:.1f}%")
col4.metric("MÉDIA GANHO / PERDA", f"R$ {media_ganho:.2f} / R$ {media_perda:.2f}")

st.markdown("---")

# ----------------- SEÇÃO DE GRÁFICOS -----------------
g1, g2 = st.columns(2)

with g1:
    st.subheader("Performance mensal")
    if total_operacoes > 0:
        df_mensal = df_filtrado.groupby('mes_nome')['resultado'].sum().reset_index()
        ordem_meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_mensal['mes_nome'] = pd.Categorical(df_mensal['mes_nome'], categories=ordem_meses, ordered=True)
        df_mensal = df_mensal.sort_values('mes_nome')
        
        fig_barra = px.bar(
            df_mensal, x='mes_nome', y='resultado',
            color_discrete_sequence=['#00c853'],
            template='plotly_dark'
        )
        fig_barra.update_layout(yaxis_title=None, xaxis_title=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_barra, use_container_width=True)
    else:
        st.info("Sem dados para exibir gráfico mensal.")

with g2:
    st.subheader("Curva de capital")
    if total_operacoes > 0:
        df_filtrado['acumulado'] = df_filtrado['resultado'].cumsum()
        fig_linha = px.line(
            df_filtrado, x='data', y='acumulado',
            color_discrete_sequence=['#00c853'],
            template='plotly_dark'
        )
        fig_linha.update_layout(yaxis_title=None, xaxis_title=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_linha, use_container_width=True)
    else:
        st.info("Sem operações no período para gerar a curva de capital.")

st.markdown("---")

# ----------------- FORMULÁRIO DE REGISTRO & TABELA DE OPERAÇÕES -----------------
f1, f2 = st.columns([1, 2])

with f1:
    st.subheader("Registrar operação")
    with st.form("registro_form", clear_on_submit=True):
        data_op = st.date_input("Data", datetime.today())
        ativo_op = st.text_input("Ativo (Ex: WIN, WDO, PETR4...)")
        lado_op = st.selectbox("Lado", ["Compra", "Venda"])
        contratos_op = st.number_input("Contratos", min_value=1, step=1)
        resultado_op = st.number_input("Resultado (R$)", step=1.0)
        obs_op = st.text_area("Observações")
        
        submit_op = st.form_submit_button("Adicionar operação")
        
        if submit_op:
            if ativo_op:
                nova_linha = pd.DataFrame([{
                    "data": data_op.strftime('%d/%m/%Y'),
                    "ativo": ativo_op,
                    "lado": lado_op,
                    "contratos": int(contratos_op),
                    "resultado": float(resultado_op),
                    "observacoes": obs_op
                }])
                
                df_original = conn.read(worksheet="operacoes")
                
                # Se a planilha original estiver vazia de verdade, substitui o df
                if df_original.empty or (len(df_original) == 1 and df_original.iloc[0].isna().all()):
                    df_atualizado = nova_linha
                else:
                    df_atualizado = pd.concat([df_original, nova_linha], ignore_index=True)
                
                conn.update(worksheet="operacoes", data=df_atualizado)
                st.success("Operação adicionada com sucesso!")
                st.rerun()
            else:
                st.error("Por favor, preencha o campo Ativo.")

with f2:
    st.subheader(f"Operações de {ano_selecionado}")
    if total_operacoes > 0:
        df_exibicao = df_filtrado[['data', 'ativo', 'lado', 'resultado', 'observacoes']].sort_values(by='data', ascending=False)
        df_exibicao['data'] = df_exibicao['data'].dt.strftime('%d/%m/%Y')
        
        st.dataframe(
            df_exibicao,
            column_config={
                "resultado": st.column_config.NumberColumn("Resultado", format="R$ %.2f"),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma operação registrada ainda.")
