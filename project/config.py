from pathlib import Path



"""
    Caminhos do Projeto
"""
# Pasta raiz project/
BASE_DIR = Path(__file__).resolve().parent

# Pasta dos arquivos zips brutos
ZIP_DIR = BASE_DIR / "data" / "raw" / "zip"

# Pasta dos arquivos CSV brutos
CSV_DIR = BASE_DIR / "data" / "raw" / "csv"

# Pasta das dimensões e fatos do banco de dados
PROCESSED_DIR = BASE_DIR / "data" / "processed"



"""
    Regras de Negócio
"""

# Qual Unidade federativa será filtrada nos CSVs da Receita Federal
TARGET_UF = "ES"

# Traduções de Situação Cadastral da empresa
SITUACAO_MAPPING = {
    1: "NULA", 2: "ATIVA", 3: "SUSPENSA", 4: "INAPTA", 8: "BAIXADA"
}

# Traduções dos portes das empresas
PORTE_MAPPING = {
    0: "NAO INFORMADO", 1: "MICRO EMPRESA", 3: "EPP", 5: "DEMAIS"
}


"""
    Nomes das colunas no CSV
    (O csv da receita vem sem colunas)
"""

COLS_CNAES = ["codigo", "descricao"]

COLS_EMPRESAS = [
    "cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel", 
    "capital_social", "porte_empresa", "ente_federativo_responsavel"
]

COLS_ESTAB = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial", 
    "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral", 
    "motivo_situacao_cadastral", "nome_cidade_exterior", "pais", 
    "data_inicio_atividade", "cnae_principal", "cnaes_secundarios", 
    "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", 
    "cep", "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2", 
    "ddd_fax", "fax", "correio_eletronico", "situacao_especial", "data_situacao_especial"
]

COLS_SIMPLES = [
    "cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
    "opcao_mei", "data_opcao_mei", "data_exclusao_mei"
]

