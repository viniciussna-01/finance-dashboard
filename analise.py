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
tickers = ['^BVSP', 'VALE3.SA', 'PETR4.SA', 'PRIO3.SA', 'WEGE3.SA']
today = datetime.datetime.now()
fixed_year = 2024
jan_1 = datetime.date(fixed_year, 1, 1)
dec_31 = datetime.date(fixed_year, 12, 31)


# ----- Cached data loaders --------
@st.cache_data(ttl=3600)
def load_currency_data(start_date, end_date):
    return currency.get(LISTA_MOEDAS, start=start_date, end=end_date)

@st.cache_data(ttl=3600)
def load_selic_data(start_date, end_date):
    try:
        start_str = pd.Timestamp(start_date).strftime("%Y-%m-%d")
        end_str = pd.Timestamp(end_date).strftime("%Y-%m-%d")
        return sgs.get({'SELIC': 1178}, start=start_str, end=end_str)
    except Exception as e:
        st.warning(f"Erro ao carregar dados da SELIC: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_ipca_data(start_date, end_date):
    try:
        start_str = pd.Timestamp(start_date).strftime("%Y-%m-%d")
        end_str = pd.Timestamp(end_date).strftime("%Y-%m-%d")
        return sgs.get({'IPCA': 433}, start=start_str, end=end_str)
    except Exception as e:
        st.warning(f"Erro ao carregar dados do IPCA: {e}")
        return pd.DataFrame()

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
    if isinstance(dados.columns, pd.MultiIndex):
        dados.columns = [col[0] for col in dados.columns]
    return dados


# ----- Sidebar -----
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
moedas = load_currency_data(start_date, end_date)
selic = load_selic_data(start_date, end_date)
# Carrega IPCA com 12 meses extras antes do início para garantir a janela móvel
ipca_start = (pd.Timestamp(start_date) - pd.DateOffset(months=12)).date()
ipca = load_ipca_data(ipca_start, end_date)


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

    # --- Gráfico SELIC divulgada x IPCA acumulado x Juros Real ---
    if not selic.empty and not ipca.empty:

        # SELIC: taxa % a.a. divulgada (série já vem em % a.a.)
        selic_aa = selic["SELIC"].copy()
        selic_aa.index = pd.to_datetime(selic_aa.index)

        # IPCA acumulado: soma dos últimos 12 meses (janela móvel)
        ipca_mensal = ipca["IPCA"].copy()
        ipca_mensal.index = pd.to_datetime(ipca_mensal.index)
        ipca_acum = ipca_mensal.rolling(window=12, min_periods=12).sum()

        # Alinha IPCA ao índice da SELIC (forward fill para dias sem divulgação)
        ipca_reindexado = ipca_acum.reindex(selic_aa.index, method="ffill")

        # Juros Real = SELIC % a.a. − IPCA acumulado no período
        juros_real = selic_aa - ipca_reindexado

        df_macro = pd.DataFrame({
            "Data": selic_aa.index,
            "SELIC % a.a.": selic_aa.values,
            "IPCA Acumulado (%)": ipca_reindexado.values,
            "Juros Real (%)": juros_real.values,
        })

        fig_macro = go.Figure()

        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["SELIC % a.a."],
            name="SELIC (% a.a.)", mode="lines",
            line=dict(color="#1565C0", width=2.5)
        ))
        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["IPCA Acumulado (%)"],
            name="IPCA Acumulado (%)", mode="lines",
            line=dict(color="#D32F2F", width=2.5)
        ))
        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["Juros Real (%)"],
            name="Juro Real", mode="lines",
            line=dict(color="#FFFFFF", width=2.5)
        ))

        fig_macro.add_hline(y=0, line_dash="solid", line_color="red", opacity=0.6, line_width=1)

        fig_macro.update_layout(
            title="SELIC (% a.a.) × IPCA Acumulado × Juros Real no Período",
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(tickformat=".0f", ticksuffix="%", gridcolor="#e0e0e0",showgrid=False),
            xaxis=dict(gridcolor="#e0e0e0", showgrid=False),
            height=480,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="center", x=0.5,
                bgcolor="rgba(0,0,0,0)",
                borderwidth=1,
                bordercolor="#ccc"
            ),
            hovermode="x unified",
            margin=dict(l=40, r=40, t=60, b=40)
        )

        st.plotly_chart(fig_macro, use_container_width=True)

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
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(
                x=dados_plot["Date"],
                y=dados_plot["Volume"],
                name="Volume"
            ),
            row=2, col=1
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

    ativos_selecionados = st.multiselect(
        "Selecione o(s) ativo(s) para comparar:",
        options=tickers,
        default=["VALE3.SA", "PETR4.SA"]
    )

    if ativos_selecionados:
        rentabilidade = pd.DataFrame()

        for ticker in ativos_selecionados:
            dados_ativo = load_acoes_data(ticker, start_date, end_date)
            if not dados_ativo.empty:
                if "Close" in dados_ativo.columns:
                    preco = dados_ativo["Close"].squeeze()
                else:
                    preco = dados_ativo.iloc[:, 0].squeeze()
                preco = preco.dropna()
                if len(preco) > 0:
                    retorno = (preco / preco.iloc[0] - 1) * 100
                    rentabilidade[ticker] = retorno

        rentabilidade.index = pd.to_datetime(rentabilidade.index)

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
                y=rentabilidade.columns[1:],
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

    st.title("🌳 Treemap de Ações — Ibovespa")

    # Lista completa das ações do Ibovespa
    IBOV_TICKERS = [
        "ABEV3","ALOS3","ASAI3","AZUL4","B3SA3","BBAS3","BBDC3","BBDC4","BBSE3",
        "BPAC11","BRAP4","BRFS3","BRKM5","CASH3","CCRO3","CIEL3","CMIG4","CMIN3",
        "COGN3","CPFE3","CPLE6","CRFB3","CSAN3","CSMG3","CSNA3","CVCB3","CYRE3",
        "DXCO3","ECOR3","EGIE3","ELET3","ELET6","EMBR3","ENEV3","ENGI11","EQTL3",
        "EZTC3","FLRY3","GGBR4","GOAU4","GOLL4","HAPV3","HYPE3","IGTI11","IRBR3",
        "ITSA4","ITUB4","JBSS3","KLBN11","LREN3","LWSA3","MGLU3","MRFG3","MRVE3",
        "MULT3","NTCO3","PCAR3","PETR3","PETR4","PETZ3","PRIO3","QUAL3","RADL3",
        "RAIL3","RAIZ4","RDOR3","RENT3","RRRP3","SANB11","SBSP3","SLCE3","SMTO3",
        "SOMA3","SUZB3","TAEE11","TIMS3","TOTS3","UGPA3","USIM5","VALE3","VBBR3",
        "VIVT3","WEGE3","YDUQ3"
    ]

    # Seletor de período — botões rápidos
    today_tree = datetime.date.today()
    periodos = {
        "1M":  today_tree - datetime.timedelta(days=30),
        "3M":  today_tree - datetime.timedelta(days=90),
        "6M":  today_tree - datetime.timedelta(days=180),
        "YTD": datetime.date(today_tree.year, 1, 1),
        "1A":  today_tree - datetime.timedelta(days=365),
        "2A": today_tree - datetime.timedelta(days=730),
    }

    col_btns = st.columns(len(periodos))
    periodo_selecionado = st.session_state.get("periodo_treemap", "YTD")

    for i, (label, _) in enumerate(periodos.items()):
        if col_btns[i].button(label, key=f"btn_{label}", use_container_width=True):
            periodo_selecionado = label
            st.session_state["periodo_treemap"] = label

    tree_start = periodos[periodo_selecionado]
    tree_end   = today_tree

    st.caption(f"Período: {tree_start.strftime('%d/%m/%Y')} → {tree_end.strftime('%d/%m/%Y')}")

    # Carrega dados e calcula retorno
    with st.spinner("Carregando dados do Ibovespa..."):
        dados_treemap = []
        tickers_sa = [t + ".SA" for t in IBOV_TICKERS]

        try:
            # Baixa todos de uma vez para ser mais rápido
            raw = yf.download(
                tickers_sa,
                start=tree_start,
                end=tree_end,
                progress=False,
                auto_adjust=True,
                group_by="ticker"
            )

            for ticker in IBOV_TICKERS:
                ticker_sa = ticker + ".SA"
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        close = raw[ticker_sa]["Close"].dropna()
                    else:
                        close = raw["Close"].dropna()

                    if len(close) >= 2:
                        retorno = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2)
                        dados_treemap.append({
                            "Ativo": ticker,
                            "Retorno (%)": retorno,
                            "Tamanho": abs(retorno) if retorno != 0 else 0.1
                        })
                except Exception:
                    continue

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    if dados_treemap:
        df_treemap = pd.DataFrame(dados_treemap)

        fig_tree = px.treemap(
            df_treemap,
            path=["Ativo"],
            values="Tamanho",
            color="Retorno (%)",
            color_continuous_scale=[
                [0.0, "#8B0000"],
                [0.5, "#1a1a1a"],
                [1.0, "#AAFF00"],
            ],
            color_continuous_midpoint=0,
            custom_data=["Retorno (%)"]
        )

        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]:.2f}%",
            textfont=dict(size=14)
        )

        fig_tree.update_layout(
            title=f"Performance Ibovespa — {periodo_selecionado} (%)",
            height=650,
            coloraxis_colorbar=dict(title="Retorno (%)"),
        )

        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.warning("Não foi possível carregar os dados. Tente novamente.")


#---------------------------
# PÁGINA FINAL
#---------------------------
elif menu == "📌 FIM":

    st.title("Encerramento")

    st.success("Projeto desenvolvido para disciplina de Visualização de Dados.")

    st.write("Aluno: Vinícius Magalhães de Souza Sena")
    st.write("Ano: 2025")
