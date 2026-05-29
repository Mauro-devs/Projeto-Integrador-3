# 📦 Projeto Integrador 3

## 💡 Ideia

Este sistema é uma plataforma de inteligência de mercado que apoia o ecossistema de microempreendedorismo no Espírito Santo, fornecendo análises espaciais e socioeconômicas para identificar oportunidades e otimizar estratégias de expansão.

É um sistema Web, atualmente utiliza dados abertos da receita federal para fazer as análises de dados.

## 🛠️ Atuais Funcionalidades

### Análise de Potencial de Escala

- Painel onde você passa o município, bairro, código CNAE e quantos meses a sua empresa está aberta.
- Ao receber estes dados o sistema consegue dizer a porcentagem de chance de você conseguir sair do MEI e ir para ME.

### Análise de Concorrência

- Painel onde você informa a atividade econômica e um município (ou o estado todo).
- Ele te devolve os bairros que possuem maior concorrência e menor concorrência.

## 🤩 Funcionalidades Futuras

### Mapa Interativo do ES

- Adicionar um mapa interativo utilizando o `streamlit-folium` no site que possa mostrar os insights de forma mais visual e precisa.
- Poder colocar mapas de calor no mapa (saturação de negócios).
- Pontos de interesse interessantes (pontos de ônibus, universidades, shoppings...)
- Pontos interativos no mapa com o nome da empresa, que ao passar o mouse me cima ele mostra a foto da empresa e as coordenadas para buscar no maps para ver avaliações.
- Mostrar quais bairros ou municípios concentram determinados tipos de negócios ex.:
  - Polos gastronômicos
  - Polos financeiros
  - Polos jurídicos
  - Polos de tecnologia

#### Requisitos para o mapa
- ```Geofabrik```: possui dados baixáveis do openstreetmap para não depender de APIs
- ```pyrosm``` : biblioteca do python para ler arquivos .pbf e devolver em objetos GeoDataFrame
- ```Folium``` + ```streamlit-folium```: mapa interativo estilo Leaflet.js que vai utilizar os objetos do pyrosm

## 🚀 Configuração do Ambiente

### 1. Criar um ambiente virtual

python -m venv .venv

### 2. Ativar o ambiente virtual

- **Windows:**

```bash
.venv\Scripts\activate
```

- **Linux/Mac:**

```bash
source .venv/bin/activate
```

---

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

---

## 🐳 Infraestrutura (Docker Nominatim)

Para a etapa de **Geocodificação (Script 3)**, utilizamos um servidor local do Nominatim rodando via Docker. Isso permite transformar os endereços em coordenadas (Latitude/Longitude) de forma totalmente offline, gratuita e sem bater em limites de requisição de APIs externas.

### Por que o Docker?

O Nominatim exige um banco de dados **PostgreSQL** pesado com a extensão **PostGIS** e a base de mapas do OpenStreetMap (OSM) indexada. O Docker encapsula toda essa complexidade em um único container pronto para uso.

### Como rodar:

1. **Local do Mapa:** Certifique-se de que o arquivo bruto "sudeste-latest.osm.pbf" está baixado e salvo dentro da pasta "data/raw/".
2. **Subir o container:** No diretório raiz do projeto (onde está o arquivo docker-compose.yml), execute:
   `docker compose up -d`
3. **Acompanhar a indexação (Apenas na primeira execução):** A primeira vez que o container subir, ele precisará indexar o mapa do Sudeste inteiro (o que leva tempo e bastante processamento). Acompanhe o andamento com:
   `docker compose logs -f`

---

## ▶️ Execução do Pipeline

Os scripts localizados na pasta "projects/" devem ser executados **na ordem numérica**, pois cada etapa depende dos arquivos ".parquet" gerados pela anterior.

### Exemplo de execução:

```bash
python projects/1_conversao.py # Converte os zips de latin1 para utf8
python projects/2_create_schema.py  #
python projects/3_geocodificar.py
```

---

## 📁 Fonte de Dados

Os arquivos csv base necessários da Receita Federal podem ser baixados no link abaixo:

🔗 https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9

> Após o download, certifique-se de extrair os arquivos no diretório "data/raw/" conforme esperado pelos scripts de conversão.
