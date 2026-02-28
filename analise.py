import pandas as pd
import streamlit as st
import plotly.express as px
from bcb import currency, sgs
import datetime
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configure page FIRST for better performance
st.set_page_config(layout="wide", page_title="Dashboard Financeiro")

# ------ codigo de cores do dashboard ----
blue_palette = [
    "#071D3D", "#102E5E", "#1E4A8A", "#2E63A8", "#3E79C2",
    "#5590D8", "#6FA5E6", "#8AB8EE", "#A9C9F2", "#C5D7F5", "#D9D9D9"
]

LISTA_MOEDAS = ['USD', 'EUR', 'GBP', 'CHF', 'CAD']
tickers = ['^BVSP','VALE3.SA','PETR4.SA','PRIO3.SA','WEGE3.SA']
today = datetime.datetime.now()
fixed_year = 2024
jan_1 = datetime.date(fixed_year, 1, 1)
dec_31 = datetime.date(fixed_year, 12, 31)


# ----- Cached data loaders --------
#@st.cache_data(ttl=3600)  # Cache for 1 hour
#def load_moto_data():
#    return pd.read_csv('data/Motos.csv')

@st.cache_data(ttl=3600)
def load_currency_data(start_date, end_date):
    return currency.get(LISTA_MOEDAS, start=start_date, end=end_date)

@st.cache_data(ttl=3600)
def load_selic_data(start_date, end_date):
    return sgs.get({'SELIC': 1178}, start=start_date, end=end_date)

@st.cache_data(ttl=3600)
def load_ipca_data(start_date, end_date):
    return sgs.get({'IPCA': 433}, start=start_date, end=end_date)

@st.cache_data(ttl=3600)
def load_acoes_data(ticker, start_date, end_date):
    dados = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        progress=False,
        auto_adjust=True,
        group_by="column"
    )

    # Se vier MultiIndex, achatar completamente
    if isinstance(dados.columns, pd.MultiIndex):
        dados.columns = [col[0] for col in dados.columns]

    return dados
    
# Sidebar

with st.sidebar:

    st.image(
        "data_atvd3/logo1.png",
        caption="Construindo Investimentos",
        use_container_width=True
    )

    st.markdown("---")
    menu = st.radio("Navegação", ["🏠 INÍCIO", "📊 Análises Gráficas", "🌳 Treemap de Ações", "📌 FIM"])
    
    st.markdown("---")
    start_date, end_date = st.date_input(
        "Selecione o intervalo da análise:",
        (datetime.date(2024, 1, 1), datetime.date.today())
    )
# Load data
#mdf = load_moto_data()
moedas = load_currency_data(start_date, end_date)
selic = load_selic_data(start_date, end_date)
ipca = load_ipca_data(start_date, end_date)



#--------------------------
# PÁGINA INICIAL
#--------------------------
if menu == "🏠 INÍCIO":

    st.title("📊 Dashboard de Indicadores Econômicos")

    st.markdown("""
    Este dashboard apresenta análises gráficas de indicadores econômicos brasileiros,
    permitindo visualizar tendências da economia e do mercado financeiro.
    """)

    st.image(
        "data_atvd3/logo.jpg",
        use_container_width=True
    )

    st.markdown("---")

    st.info("Utilize o menu lateral para acessar as análises gráficas.")

#--------------------------
# ANÁLISES GRÁFICAS
#--------------------------

elif menu == "📊 Análises Gráficas":

    st.title("📈 Análises Gráficas")

    st.header("Análise Macro - Brasil 🇧🇷")
    col1, col2 = st.columns(2)

    with col1:
        if not selic.empty:
            fig_selic = px.line(selic, y='SELIC', title='Taxa de Juros (SELIC)')
            st.plotly_chart(fig_selic, use_container_width=True)

    with col2:
        if not ipca.empty:
            fig_ipca = px.line(ipca, y='IPCA', title='Variação Mensal do IPCA')
            st.plotly_chart(fig_ipca, use_container_width=True)

    st.header("Análise de Ações - Brasil 🇧🇷")

    ativo = st.selectbox("Selecione o Ativo:", tickers)
    dados = load_acoes_data(ativo, start_date, end_date)

    if not dados.empty:

        dados_plot = dados.reset_index()
        fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
        )
        fig.add_trace(
        go.Scatter(
            x=dados_plot["Date"],
            y=dados_plot["Close"],
            name="Preço (R$)",
            mode="lines"
            ),
            row=1,
            col=1
        )
        fig.add_trace(
            go.Bar(
            x=dados_plot["Date"],
            y=dados_plot["Volume"],
            name="Volume"
            ),
            row=2,
            col=1
        )
        fig.update_layout(
            title=f"{ativo} - Preço e Volume",
            height=700,
            showlegend=True
        )
        fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_xaxes(title_text="Data", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)
    st.header("Rentabilidade Acumulada 📈")


#-----------------------------------
#COMPARAR OUTROS ATIVOS SELECIONADOS
#-----------------------------------

    ativos_selecionados = st.multiselect(
    "Selecione o(s) ativo(s) para comparar:",
    options=tickers,
    default=["VALE3.SA", "PETR4.SA"]
)

    if ativos_selecionados:
        rentabilidade = pd.DataFrame()  # ✅ correto, inicializa uma vez

        for ticker in ativos_selecionados:
            dados_ativo = load_acoes_data(ticker, start_date, end_date)
            if not dados_ativo.empty:
                preco = dados_ativo["Close"]
                retorno = (preco / preco.iloc[0] - 1) * 100
                rentabilidade[ticker] = retorno  # ✅ acumula cada ticker

        # SELIC e IPCA ficam AQUI, fora do for mas dentro do if ativos_selecionados
        if not selic.empty:
            selic_diaria = selic["SELIC"] / 100 / 252
            selic_acum = ((1 + selic_diaria).cumprod() - 1) * 100
            selic_acum.index = pd.to_datetime(selic_acum.index)
            rentabilidade["SELIC"] = selic_acum.reindex(rentabilidade.index, method="ffill")

        if not ipca.empty:
            ipca_mensal = ipca["IPCA"] / 100
            ipca_acum = ((1 + ipca_mensal).cumprod() - 1) * 100
            ipca_acum.index = pd.to_datetime(ipca_acum.index)
            rentabilidade["IPCA"] = ipca_acum.reindex(rentabilidade.index, method="ffill")

        if not rentabilidade.empty:
            rentabilidade.index = pd.to_datetime(rentabilidade.index)
            rentabilidade = rentabilidade.reset_index()
            rentabilidade = rentabilidade.rename(columns={"index": "Data", "Date": "Data"})

            fig_rent = px.line(
                rentabilidade,
                x="Data",
                y=rentabilidade.columns[1:],  # todas as colunas exceto a data
                title="Rentabilidade Acumulada (%)",
                labels={"value": "Retorno (%)", "variable": "Ativo"},
                color_discrete_map={
                    "SELIC": "#AAFF00",
                    "IPCA": "#8B4513",
                    "^BVSP": blue_palette[-5],
                    "VALE3.SA": blue_palette[-4],
                    "PETR4.SA": blue_palette[-3],
                    "PRIO3.SA": blue_palette[-2],
                    "WEGE3.SA": blue_palette[-1],
                }
            )
            fig_rent.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_rent, use_container_width=True)

    else:
        st.warning("Selecione ao menos um ativo para visualizar.")


#---------------------------
# TREEMAP DE AÇÕES
#---------------------------
elif menu == "🌳 Treemap de Ações":

    st.title("🌳 Treemap de Ações")

    ativos_treemap = st.multiselect(
        "Selecione as ações para o Treemap:",
        options=tickers,
        default=tickers
    )

    ticker_custom = st.text_input(
        "Ou adicione um ticker manualmente (ex: ITUB4.SA, BBDC4.SA):",
        placeholder="Digite e pressione Enter"
    )

    if ticker_custom:
        extras = [t.strip().upper() for t in ticker_custom.split(",")]
        ativos_treemap = list(set(ativos_treemap + extras))

    if ativos_treemap:
        dados_treemap = []

        for ticker in ativos_treemap:
            dados_ativo = load_acoes_data(ticker, start_date, end_date)
            if not dados_ativo.empty:
                preco_inicio = dados_ativo["Close"].iloc[0]
                preco_fim = dados_ativo["Close"].iloc[-1]
                retorno = round((preco_fim / preco_inicio - 1) * 100, 2)
                dados_treemap.append({
                    "Ativo": ticker.replace(".SA", ""),
                    "Retorno (%)": retorno,
                    "Tamanho": abs(retorno) if retorno != 0 else 0.1  # tamanho proporcional ao retorno
                })

        if dados_treemap:
            df_treemap = pd.DataFrame(dados_treemap)

            fig_tree = px.treemap(
                df_treemap,
                path=["Ativo"],
                values="Tamanho",
                color="Retorno (%)",
                color_continuous_scale=[
                    [0.0, "#8B0000"],   # vermelho escuro (queda forte)
                    [0.5, "#1a1a1a"],   # neutro
                    [1.0, "#AAFF00"],   # verde limão (alta forte)
                ],
                color_continuous_midpoint=0,
                custom_data=["Retorno (%)"]
            )

            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>%{customdata[0]:.2f}%",
                textfont=dict(size=16)
            )

            fig_tree.update_layout(
                title="Performance dos Ativos no Período (%)",
                height=600,
                coloraxis_colorbar=dict(title="Retorno (%)"),
            )

            st.plotly_chart(fig_tree, use_container_width=True)

    else:
        st.warning("Selecione ou digite ao menos um ativo.")



#---------------------------
# PÁGINA FINAL
#---------------------------
elif menu == "📌 FIM":

    st.title("Encerramento")

    st.success("Projeto desenvolvido para disciplina de Visualização de Dados.")

    st.write("Aluno: Vinícius Magalhães de Souza Sena")
    st.write("Ano: 2025")
