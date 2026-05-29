import requests


def carregar_dados_cep(cep:str):
    try:

        #https://viacep.com.br/ - URL do site

        url_viafi_api_base = f"https://viacep.com.br/ws/{cep}/json/"


        response_viafi_api = requests.get(url_viafi_api_base).json()

        dados = {
                "logradouro": response_viafi_api['logradouro'],
                "bairro": response_viafi_api['bairro'],
        }

        return dados
    except Exception as error:
        raise Exception(f"Erro ao realizar a consulta e carregamento de dados do CEP | {error}")
    

if __name__ == "__main__":
    dados = carregar_dados_cep()
