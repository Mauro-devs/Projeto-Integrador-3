import streamlit as st
import pandas as pd
import polars as pl
import joblib
from pathlib import Path

# APENAS PROCESSED_DIR AGORA (Arquitetura 100% limpa)
from project.config import PROCESSED_DIR

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Radar Competitivo MEI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Caminhos absolutos
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "data" / "models"

# ==========================================
# FUNÇÕES DE CARREGAMENTO (Com Cache)
# ==========================================
@st.cache_resource
def carregar_modelos():
    try:
        modelo = joblib.load(MODELS_DIR / "modelo_crescimento.joblib")
        le_cnae = joblib.load(MODELS_DIR / "le_cnae.joblib")
        le_municipio = joblib.load(MODELS_DIR / "le_municipio.joblib")
        le_bairro = joblib.load(MODELS_DIR / "le_bairro.joblib")
        return modelo, le_cnae, le_municipio, le_bairro
    except FileNotFoundError:
        st.error("Modelos da IA não encontrados. Rode o script 4_modelagem_ml.py primeiro.")
        st.stop()

@st.cache_data
def carregar_dados():
    try:
        dim_loc = pl.read_parquet(PROCESSED_DIR / "dim_localidades.parquet")
        fato_op = pl.read_parquet(PROCESSED_DIR / "fato_oportunidades.parquet")
        dim_ativ = pl.read_parquet(PROCESSED_DIR / "dim_atividades_economicas.parquet")
        
        df_oportunidades = fato_op.join(
            dim_ativ, left_on="ID_ATIVIDADE", right_on="ID_ATIVIDADE", how="left"
        ).to_pandas()
        
        return dim_loc.to_pandas(), df_oportunidades
    except FileNotFoundError:
        st.error("Bases de dados não encontradas. Rode os scripts ETL primeiro.")
        st.stop()

@st.cache_data
def carregar_dicionario_cnae():
    """Lê o dicionário direto da Dimensão do Star Schema (Arquitetura Otimizada)"""
    try:
        dim_ativ = pl.read_parquet(PROCESSED_DIR / "dim_atividades_economicas.parquet").to_pandas()
        # Remove duplicatas para garantir um dicionário limpo
        df_unico = dim_ativ.drop_duplicates(subset=["CNAE_FISCAL_PRINCIPAL"])
        # Cria um dicionário { "Descrição": "Código" }
        return dict(zip(df_unico["CNAE_FISCAL_PRINCIPAL"], df_unico["CODIGO_CNAE"]))
    except Exception as e:
        return {}

# Carregando tudo para a memória
modelo, le_cnae, le_municipio, le_bairro = carregar_modelos()
df_loc, df_oportunidades = carregar_dados()
dict_cnae_codigos = carregar_dicionario_cnae()

# ==========================================
# PREPARAÇÃO DAS LISTAS PARA A TELA
# ==========================================
lista_municipios = sorted(df_loc["MUNICIPIO"].dropna().unique())

# Cria a lista formatada "CÓDIGO - DESCRIÇÃO" para a ABA 1
lista_cnaes_formatada = []
for desc in sorted(le_cnae.classes_):
    codigo = dict_cnae_codigos.get(desc, "")
    if codigo:
        lista_cnaes_formatada.append(f"{codigo} - {desc}")
    else:
        lista_cnaes_formatada.append(desc)

# Cria a lista formatada "CÓDIGO - DESCRIÇÃO" para a ABA 2
cnaes_analisados_bruto = sorted(df_oportunidades["CNAE_FISCAL_PRINCIPAL"].dropna().unique())
lista_cnaes_aba2_formatada = []
for desc in cnaes_analisados_bruto:
    codigo = dict_cnae_codigos.get(desc, "")
    if codigo:
        lista_cnaes_aba2_formatada.append(f"{codigo} - {desc}")
    else:
        lista_cnaes_aba2_formatada.append(desc)

# ==========================================
# CABEÇALHO DO APLICATIVO
# ==========================================
st.title("🌍 Radar Competitivo para MEIs")
st.markdown("Plataforma de Inteligência de Mercado baseada em **Machine Learning** e **Quociente Locacional**.")

tab1, tab2 = st.tabs(["📊 Analisar Minha Empresa (Previsão de Sucesso)", "📍 Onde Abrir? (Oceanos Azuis)"])

# ==========================================
# ABA 1: CALCULADORA DE SUCESSO (IA)
# ==========================================
with tab1:
    st.header("Descubra o Potencial de Escala da sua Empresa")
    st.write("Nossa IA analisou o estado inteiro para descobrir as características que levam um MEI a crescer e virar Microempresa (ME).")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Onde você está?")
        municipio_selecionado = st.selectbox("Selecione o Município:", lista_municipios)
        
        bairros_do_municipio = sorted(df_loc[df_loc["MUNICIPIO"] == municipio_selecionado]["BAIRRO"].dropna().unique())
        bairro_selecionado = st.selectbox("Selecione o Bairro:", bairros_do_municipio)

    with col2:
        st.subheader("2. O que você faz?")
        cnae_selecionado_display = st.selectbox("Busque pelo Código CNAE ou Nome:", lista_cnaes_formatada)
        
        if " - " in cnae_selecionado_display:
            cnae_selecionado = cnae_selecionado_display.split(" - ", 1)[1]
        else:
            cnae_selecionado = cnae_selecionado_display
        
        idade_meses = st.slider("Há quantos meses a empresa está aberta?", min_value=0, max_value=120, value=12, step=1)
        idade_dias = idade_meses * 30

    st.write("---")
    if st.button("🧠 Analisar com Inteligência Artificial", type="primary", use_container_width=True):
        with st.spinner('A IA está processando o padrão de mercado...'):
            try:
                cnae_cod = le_cnae.transform([cnae_selecionado])[0]
                mun_cod = le_municipio.transform([municipio_selecionado])[0]
                bairro_cod = le_bairro.transform([bairro_selecionado])[0]
                
                df_entrada = pd.DataFrame([{
                    "IDADE_DIAS": idade_dias,
                    "CNAE_COD": cnae_cod,
                    "MUNICIPIO_COD": mun_cod,
                    "BAIRRO_COD": bairro_cod
                }])
                
                predicao = modelo.predict(df_entrada)[0]
                probabilidades = modelo.predict_proba(df_entrada)[0]
                chance_sucesso = probabilidades[1] * 100
                
                st.subheader("Veredito da Inteligência Artificial")
                
                res_col1, res_col2 = st.columns([1, 2])
                with res_col1:
                    st.metric(label="Score de Potencial", value=f"{chance_sucesso:.1f}%")
                
                with res_col2:
                    if predicao == 1 or chance_sucesso >= 25:
                        st.success("✅ **ALTO POTENCIAL DE ESCALA:** O perfil geográfico e o tempo de maturação indicam um forte padrão de empresas que ultrapassam o teto do MEI (R$ 81 mil/ano).")
                    elif chance_sucesso >= 8:
                        st.warning("🟡 **POTENCIAL MODERADO (ESTÁVEL):** O negócio tem um score dentro da média do mercado capixaba. Pode ser lucrativo, mas estatisticamente tende a se manter dentro do limite de faturamento do MEI.")
                    else:
                        st.error("🔴 **ALTO RISCO OU ESTAGNAÇÃO:** Empresas com essa exata combinação (Setor + Idade + Bairro) raramente escalam para Microempresa. Se for antiga, a IA entende que o faturamento já estabilizou no teto do MEI.")
                
            except Exception as e:
                st.error("Este bairro ainda não foi mapeado pela IA ou não há dados suficientes para ele.")

# ==========================================
# ABA 2: MAPA DE OPORTUNIDADES (OCEANO AZUL)
# ==========================================
with tab2:
    st.header("Encontre os Oceanos Azuis (Menor Concorrência)")
    st.write("Descubra os bairros onde o seu serviço está em falta (alta oportunidade) e fuja dos locais saturados.")
    
    colA, colB = st.columns([2, 1])
    
    with colA:
        setor_alvo_display = st.selectbox("Qual negócio você quer abrir? (Digite Código ou Nome)", lista_cnaes_formatada, key="aba2_cnae")
        
        if " - " in setor_alvo_display:
            setor_alvo = setor_alvo_display.split(" - ", 1)[1]
        else:
            setor_alvo = setor_alvo_display
            
    with colB:
        cidade_filtro = st.selectbox("Filtrar por Cidade:", ["O Estado Inteiro"] + lista_municipios, key="aba2_cidade")
        
    if st.button("🔍 Mapear Oportunidades", use_container_width=True):
        
        if setor_alvo not in df_oportunidades["CNAE_FISCAL_PRINCIPAL"].values:
            st.write("---")
            st.warning("🟡 **MERCADO DE ALTÍSSIMO NICHO OU DEMANDA RESTRITA**")
            st.write(f"O setor de **{setor_alvo}** possui um volume de empresas muito baixo no estado, ou seu comportamento foge do consumo de varejo tradicional.")
            st.write("A inteligência de *Oceano Azul* funciona mapeando a concorrência de serviços de demanda contínua. Para negócios altamente específicos como este, a ausência de concorrência não garante demanda. Recomendamos um estudo de mercado tradicional e análise de público-alvo.")
        
        else:
            df_filtro = df_oportunidades[df_oportunidades["CNAE_FISCAL_PRINCIPAL"] == setor_alvo]
            
            if cidade_filtro != "O Estado Inteiro":
                df_filtro = df_filtro[df_filtro["MUNICIPIO"] == cidade_filtro]
                
            oceanos_azuis = df_filtro[df_filtro["INDICE_SATURACAO"] <= 0.6].sort_values("INDICE_SATURACAO", ascending=True).head(5)
            saturados = df_filtro[df_filtro["INDICE_SATURACAO"] >= 1.5].sort_values("INDICE_SATURACAO", ascending=False).head(5)
            
            st.write("---")
            
            col_resA, col_resB = st.columns(2)
            
            with col_resA:
                st.subheader("🌊 Melhores Bairros (Falta Concorrência)")
                if not oceanos_azuis.empty:
                    for idx, row in oceanos_azuis.iterrows():
                        st.info(f"**{row['BAIRRO']}** ({row['MUNICIPIO']})\n\nConcorrência {((1 - row['INDICE_SATURACAO']) * 100):.0f}% menor que a média. Tem {row['QTD_NO_BAIRRO']} ativas em um bairro de {row['TOTAL_NO_BAIRRO']} comércios.")
                else:
                    st.write("Nenhum bairro com falta severa deste serviço.")

            with col_resB:
                st.subheader("🔴 Evite Abrir Aqui (Muita Concorrência)")
                if not saturados.empty:
                    for idx, row in saturados.iterrows():
                        st.error(f"**{row['BAIRRO']}** ({row['MUNICIPIO']})\n\nSaturação de {row['INDICE_SATURACAO']}x a média estadual! Já existem {row['QTD_NO_BAIRRO']} negócios deste tipo aqui.")
                else:
                    st.write("Nenhum bairro criticamente saturado no momento.")
