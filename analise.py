import pandas as pd
import streamlit as st
import plotly.express as px
from bcb import currency, sgs
import datetime
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="Dashboard Financeiro")

# cores que escolhi pro dashboard - paleta azul
blue_palette = [
    "#071D3D", "#102E5E", "#1E4A8A", "#2E63A8", "#3E79C2",
    "#5590D8", "#6FA5E6", "#8AB8EE", "#A9C9F2", "#C5D7F5", "#D9D9D9"
]

LISTA_MOEDAS = ['USD', 'EUR', 'GBP', 'CHF', 'CAD']

tickers = [
    '^BVSP', 'VALE3.SA', 'PETR4.SA', 'PRIO3.SA', 'WEGE3.SA',
    "ABEV3.SA","ALOS3.SA","ASAI3.SA","AZUL4.SA","B3SA3.SA","BBAS3.SA","BBDC3.SA","BBDC4.SA","BBSE3.SA",
    "BPAC11.SA","BRAP4.SA","BRFS3.SA","BRKM5.SA","CASH3.SA","CCRO3.SA","CIEL3.SA","CMIG4.SA","CMIN3.SA",
    "COGN3.SA","CPFE3.SA","CPLE6.SA","CRFB3.SA","CSAN3.SA","CSMG3.SA","CSNA3.SA","CVCB3.SA","CYRE3.SA",
    "DXCO3.SA","ECOR3.SA","EGIE3.SA","ELET3.SA","ELET6.SA","EMBR3.SA","ENEV3.SA","ENGI11.SA","EQTL3.SA",
    "EZTC3.SA","FLRY3.SA","GGBR4.SA","GOAU4.SA","GOLL4.SA","HAPV3.SA","HYPE3.SA","IGTI11.SA","IRBR3.SA",
    "ITSA4.SA","ITUB4.SA","JBSS3.SA","KLBN11.SA","LREN3.SA","LWSA3.SA","MGLU3.SA","MRFG3.SA","MRVE3.SA",
    "MULT3.SA","NTCO3.SA","PCAR3.SA","PETR3.SA","PETZ3.SA","QUAL3.SA","RADL3.SA",
    "RAIL3.SA","RAIZ4.SA","RDOR3.SA","RENT3.SA","RRRP3.SA","SANB11.SA","SBSP3.SA","SLCE3.SA","SMTO3.SA",
    "SOMA3.SA","SUZB3.SA","TAEE11.SA","TIMS3.SA","TOTS3.SA","UGPA3.SA","USIM5.SA","VBBR3.SA",
    "VIVT3.SA","YDUQ3.SA"
]

today = datetime.datetime.now()
fixed_year = 2024


# funções pra carregar os dados com cache
@st.cache_data(ttl=3600)
def load_currency_data(start_date, end_date):
    return currency.get(LISTA_MOEDAS, start=start_date, end=end_date)

@st.cache_data(ttl=3600)
def load_selic_data(start_date, end_date):
    # precisei converter pra string senão a API do bcb dava erro
    s = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    e = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return sgs.get({'SELIC': 1178}, start=s, end=e)

@st.cache_data(ttl=3600)
def load_ipca_data(start_date, end_date):
    s = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    e = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return sgs.get({'IPCA': 433}, start=s, end=e)

@st.cache_data(ttl=3600)
def load_acoes_data(ticker, start_date, end_date):
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        progress=False,
        auto_adjust=True,
        group_by="column"
    )
    # corrige multiindex que o yfinance as vezes retorna
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    return df


# sidebar
with st.sidebar:
    st.image(
        "data_atvd3/logo1.png",
        caption="Construindo Investimentos",
        use_container_width=True
    )
    st.markdown("---")
    menu = st.radio("Navegação", ["INÍCIO", "Análises Gráficas", "Treemap de Ações", "FIM"])
    st.markdown("---")
    start_date, end_date = st.date_input(
        "Selecione o intervalo da análise:",
        (datetime.date(2024, 1, 1), datetime.date.today())
    )

# carrega os dados principais
moedas = load_currency_data(start_date, end_date)
selic  = load_selic_data(start_date, end_date)

# ipca precisa de 12 meses antes pra janela movel funcionar
ipca_start = (pd.Timestamp(start_date) - pd.DateOffset(months=12)).date()
ipca = load_ipca_data(ipca_start, end_date)


# INÍCIO
if menu == "INÍCIO":

    st.title("Dashboard de Indicadores Econômicos")

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


# ANÁLISES GRÁFICAS
elif menu == "Análises Gráficas":

    st.title("Análises Gráficas")
    st.header("Análise Macro - Brasil 🇧🇷")

    if not selic.empty and not ipca.empty:

        selic_aa = selic["SELIC"].copy()
        selic_aa.index = pd.to_datetime(selic_aa.index)

        # IPCA dos ultimos 12 meses (rolante)
        temp = ipca["IPCA"].copy()
        temp.index = pd.to_datetime(temp.index)
        ipca_12m = temp.rolling(window=12, min_periods=12).sum()

        # alinha com o indice da selic
        ipca_alinhado = ipca_12m.reindex(selic_aa.index, method="ffill")

        juros_real = selic_aa - ipca_alinhado

        df_macro = pd.DataFrame({
            "Data": selic_aa.index,
            "SELIC % a.a.": selic_aa.values,
            "IPCA Acumulado (%)": ipca_alinhado.values,
            "Juros Real (%)": juros_real.values,
        })

        fig_macro = go.Figure()

        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["SELIC % a.a."],
            name="Taxa Selic", mode="lines",
            line=dict(color="#1565C0", width=2.5)
        ))
        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["IPCA Acumulado (%)"],
            name="IPCA", mode="lines",
            line=dict(color="#D32F2F", width=2.5)
        ))
        fig_macro.add_trace(go.Scatter(
            x=df_macro["Data"], y=df_macro["Juros Real (%)"],
            name="Juro Real", mode="lines",
            line=dict(color="#FFFFFF", width=2.5)
        ))

        fig_macro.add_hline(y=0, line_dash="solid", line_color="red", opacity=0.6, line_width=1)

        fig_macro.update_layout(
            title="SELIC (% a.a.) × IPCA Acumulado × Juros Real<br>no Período",
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(tickformat=".0f", ticksuffix="%", gridcolor="#e0e0e0", showgrid=False),
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
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3]
        )
        fig.add_trace(
            go.Scatter(x=dados_plot["Date"], y=dados_plot["Close"],
                       name="Preço (R$)", mode="lines"),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=dados_plot["Date"], y=dados_plot["Volume"], name="Volume"),
            row=2, col=1
        )
        fig.update_layout(title=f"{ativo} - Preço e Volume", height=700, showlegend=True)
        fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_xaxes(title_text="Data", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

    st.header("Rentabilidade Acumulada")

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

        # adiciona selic e ipca como benchmark
        if not selic.empty:
            selic_d = selic["SELIC"] / 100 / 252
            selic_acum = ((1 + selic_d).cumprod() - 1) * 100
            selic_acum.index = pd.to_datetime(selic_acum.index)
            rentabilidade["SELIC"] = selic_acum.reindex(rentabilidade.index, method="ffill")

        if not ipca.empty:
            ipca_m = ipca["IPCA"] / 100
            ipca_acum = ((1 + ipca_m).cumprod() - 1) * 100
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


# TREEMAP
elif menu == "Treemap de Ações":

    st.title("Treemap de Ações — Ibovespa")

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

    today_tree = datetime.date.today()
    periodos = {
        "1M":  today_tree - datetime.timedelta(days=30),
        "3M":  today_tree - datetime.timedelta(days=90),
        "6M":  today_tree - datetime.timedelta(days=180),
        "YTD": datetime.date(today_tree.year, 1, 1),
        "1A":  today_tree - datetime.timedelta(days=365),
        "2A":  today_tree - datetime.timedelta(days=730),
    }

    cols = st.columns(len(periodos))
    periodo_selecionado = st.session_state.get("periodo_treemap", "YTD")

    for i, (label, _) in enumerate(periodos.items()):
        if cols[i].button(label, key=f"btn_{label}", use_container_width=True):
            periodo_selecionado = label
            st.session_state["periodo_treemap"] = label

    tree_start = periodos[periodo_selecionado]
    tree_end   = today_tree

    st.caption(f"Período: {tree_start.strftime('%d/%m/%Y')} → {tree_end.strftime('%d/%m/%Y')}")

    with st.spinner("Carregando dados do Ibovespa..."):
        lista_retornos = []
        tickers_sa = [t + ".SA" for t in IBOV_TICKERS]

        # baixa tudo de uma vez, mais rapido que um por um
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
                    ret = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2)
                    lista_retornos.append({
                        "Ativo": ticker,
                        "Retorno (%)": ret,
                        "Tamanho": abs(ret) if ret != 0 else 0.1
                    })
            except Exception:
                continue

    if lista_retornos:
        df_treemap = pd.DataFrame(lista_retornos)

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


# FIM
elif menu == "FIM":

    st.title("Encerramento")

    st.success("Projeto desenvolvido para disciplina de Análise e Visualização de Dados.")

    st.write("Aluno: Vinícius Magalhães de Souza Sena")
    st.write("Ano: 2025")
