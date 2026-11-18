# DW_FILMES — ETL

Carga do Data Warehouse de desempenho de filmes descrito em `docs/Documentacao_DW_Filmes_v4.docx`
(também em PDF na mesma pasta).

Trabalho da disciplina Tópicos Avançados em Banco de Dados (IFAL, Campus Maceió), prof. Luiz
Frederico Lopes de Oliveira. Grupo: Daniel Lage Cortez, Leonardo José Lucas Ferro Moreira e
Marcelo Alves Feitoza.

- **Fontes integradas:**
  - TMDB Movies (`tmdb-movies.csv`, 10.866 filmes, 1960–2015): filmes, orçamento, receita, gêneros e produtoras;
  - TMDB 5000 (`tmdb_5000_movies.csv`): orçamento e receita ausentes no TMDB Movies;
  - IMDb (`imdb.title.basics`, `title.ratings`, `title.principals`, `name.basics`): nota do público, diretores e elenco (`nconst`);
  - Rotten Tomatoes (`rotten_tomatoes_movies.csv`): nota da crítica e classificação indicativa;
  - Cinema Hall Ticket Sales (`cinema_hall_ticket_sales.csv`): venda de ingressos e perfil do espectador.
- **Banco:** PostgreSQL 16, schema `sch_dw_filmes` (usa a extensão `unaccent`).
- **ETL:** Pentaho Data Integration (PDI) 9.4.0.0-343, com Java 11.
- **Modelo:** constelação de fatos — `FT_DESEMPENHO_FILME` e `FT_VENDAS_INGRESSOS`, com `DIM_GENERO`
  compartilhada —, 7 dimensões e 2 tabelas-ponte.

## Estrutura

```
dw-filmes-etl/
├── docker-compose.yml               # PostgreSQL 16 em Docker (opção Linux/macOS)
├── data/                            # fontes (os arquivos do IMDb somam cerca de 7,5 GB)
│   ├── tmdb-movies.csv
│   ├── tmdb_5000_movies.csv
│   ├── imdb.title.basics.csv, imdb.title.ratings.csv
│   ├── imdb.title.principals.csv, imdb.name.basics.csv
│   ├── rotten_tomatoes_movies.csv
│   └── cinema_hall_ticket_sales.csv
├── sql/
│   ├── 01_ddl_postgres.sql          # schema sch_dw_filmes
│   ├── 02_consultas_verificacao.sql # contagens e verificação de duplicados
│   ├── 03_validacao_meta_smart.sql  # indicador da Meta SMART (Apêndice C)
│   └── 04_views_perguntas.sql       # views das 12 perguntas e da Meta SMART
├── graficos/
│   ├── gerar_graficos.py            # lê as views e gera um PNG por pergunta
│   ├── figura_modelo.py             # diagrama do modelo dimensional (lê o catálogo do banco)
│   ├── figura_fluxos_etl.py         # fluxos das transformações e do job (lê os .ktr/.kjb)
│   ├── figura_transformacoes_sql.py # origem, operação e destino dos steps SQL
│   ├── requirements.txt
│   ├── claro/                       # fundo branco (documentação)
│   └── escuro/                      # fundo preto e amarelo (slides)
├── resultados/
│   └── p01_...csv ... meta_smart.csv # conteúdo de cada view na carga registrada
├── etl/
│   ├── tr_01 ... tr_10              # stagings das fontes e casamento TMDB x Rotten Tomatoes
│   ├── tr_11 ... tr_17              # dimensões
│   ├── tr_18, tr_19                 # tabelas-ponte
│   ├── tr_20, tr_21                 # tabelas fato
│   ├── tr_22_pos_carga.ktr          # IND_ATUAL, ROI normalizado e ISI
│   └── jb_carga_dw_filmes.kjb       # job mestre (22 transformações em sequência)
├── eda/
│   ├── analise_exploratoria.py      # análise exploratória sobre a vw_filme
│   ├── resumo_eda.md                # resultados numéricos da análise
│   └── figuras/                     # eda_01 ... eda_06
├── scripts/
│   └── executar_job.bat             # roda o job no Windows (Kitchen)
├── logs/
│   ├── execucao_01_primeira_carga.log
│   ├── execucao_02_reexecucao.log
│   └── execucao_03_reexecucao.log
└── docs/
    ├── Documentacao_DW_Filmes_v4.docx / .pdf  # documentação final
    └── versoes_anteriores/          # v3, versão completa antiga, roteiro do vídeo
```

Os arquivos do IMDb e o `tmdb_ratings_export.csv` (notas de usuários do Letterboxd, que não se
ligam aos filmes do DW e não são usadas) não acompanham o repositório por causa do tamanho
(veja o `.gitignore`; `imdb.title.crew.csv` e `tmdb_5000_credits.csv` também não são usados):
baixe os arquivos do IMDb em https://developer.imdb.com/non-commercial-datasets/ e converta-os
de `.tsv.gz` para CSV com os nomes acima.

## Conexão do banco

Os `.ktr` e o `.kjb` usam esta conexão (nome `dw_filmes`):

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Porta | `55432` |
| Banco | `dw_filmes` |
| Usuário / senha | `dw_filmes` / `dw_filmes` |
| Schema | `sch_dw_filmes` |

## Execução no Windows

### Pré-requisitos

| Ferramenta | Onde obter | Observação |
|---|---|---|
| Java 11 | Eclipse Temurin JDK 11 (zip) | O PDI 9.4 não roda em Java 17 ou mais novo |
| PostgreSQL 16 | EnterpriseDB, pacote *binaries* (zip) | Não precisa de instalador |
| PDI 9.4.0.0-343 | `pdi-ce-9.4.0.0-343.zip` | SHA-1 `bd89671a9d6f95948d3fbbfd33102710f3e004e0` |

Defina, no terminal ou nas variáveis de ambiente do Windows:

```bat
set PENTAHO_JAVA_HOME=C:\caminho\jdk-11.0.33+10
set PDI_HOME=C:\caminho\data-integration
set PGBIN=C:\caminho\pgsql\bin
```

### 1. Criar e iniciar o banco (só na primeira vez)

```bat
"%PGBIN%\initdb.exe" -D C:\caminho\pgdata -U dw_filmes -W -A scram-sha-256 -E UTF8 --locale=C
"%PGBIN%\pg_ctl.exe" -D C:\caminho\pgdata -o "-p 55432" -l C:\caminho\pgdata\server.log start
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d postgres -c "CREATE DATABASE dw_filmes;"
```

O `initdb` pede a senha do usuário: use `dw_filmes`. Nas próximas vezes, basta o `pg_ctl ... start`.

### 2. Aplicar o schema

Pode ser repetido sempre que quiser voltar ao banco vazio:

```bat
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -c "DROP SCHEMA IF EXISTS sch_dw_filmes CASCADE;"
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -v ON_ERROR_STOP=1 -f sql\01_ddl_postgres.sql
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -v ON_ERROR_STOP=1 -f sql\04_views_perguntas.sql
```

As views de `04_views_perguntas.sql` (`vw_filme`, `vw_p01_...` a `vw_p12_...` e `vw_meta_smart`)
são a fonte dos gráficos da documentação e dos slides. Elas são
apagadas junto com o schema, então reaplique o arquivo sempre que recriar o schema.

### 3. Rodar a carga

Pela linha de comando, a partir da raiz do projeto (o log é gravado em `logs\`):

```bat
scripts\executar_job.bat execucao_01_primeira_carga
```

Ou pelo Spoon (interface gráfica): rode `%PDI_HOME%\Spoon.bat` e abra `etl\jb_carga_dw_filmes.kjb`.

### 4. Conferir o resultado

```bat
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -f sql\02_consultas_verificacao.sql
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -f sql\03_validacao_meta_smart.sql
"%PGBIN%\psql.exe" -h localhost -p 55432 -U dw_filmes -d dw_filmes -c "SELECT * FROM sch_dw_filmes.vw_p01_dupla_diretor_ator LIMIT 10;"
```

### 5. Gerar os gráficos

Requer Python 3.10 ou mais novo. Os gráficos são lidos direto das views, então rode depois da carga:

```bat
python -m venv .venv
.venv\Scripts\pip install -r graficos\requirements.txt
.venv\Scripts\python graficos\gerar_graficos.py
.venv\Scripts\python graficos\figura_modelo.py
.venv\Scripts\python graficos\figura_fluxos_etl.py
.venv\Scripts\python graficos\figura_transformacoes_sql.py
.venv\Scripts\python eda\analise_exploratoria.py
```

A análise exploratória grava as figuras em `eda/figuras/` e o resumo numérico em `eda/resumo_eda.md`.

### 6. Rodar de novo

Repita o passo 3 sem recriar o schema: a carga é idempotente e não duplica dados. Cada execução
leva cerca de 3,5 minutos, a maior parte na leitura do `imdb.title.principals.csv` (4,9 GB).

## Execução no Linux/macOS (Docker)

```bash
docker compose up -d
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes -c "DROP SCHEMA IF EXISTS sch_dw_filmes CASCADE;"
docker exec -i dw_filmes_pg psql -v ON_ERROR_STOP=1 -U dw_filmes -d dw_filmes < sql/01_ddl_postgres.sql
docker exec -i dw_filmes_pg psql -v ON_ERROR_STOP=1 -U dw_filmes -d dw_filmes < sql/04_views_perguntas.sql
cd "$PDI_HOME" && ./kitchen.sh -file="$OLDPWD/etl/jb_carga_dw_filmes.kjb" -level=Basic
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes < sql/02_consultas_verificacao.sql
```

## Resultado esperado

| Tabela | Linhas |
|---|---|
| `stg_tmdb_movies` | 3.888 (3.807 do TMDB Movies + 81 recuperados pelo TMDB 5000) |
| `stg_ponte_rt` | 3.572 filmes casados com o Rotten Tomatoes |
| `dim_filme` | 3.889 (3.888 + membro zero) |
| `dim_diretor` | 1.753 (1.752 + membro zero) |
| `dim_ator` | 7.203 |
| `dim_produtora` | 3.325 (3.324 + membro zero) |
| `dim_genero` | 20 |
| `dim_tempo` | 20.287 (15/06/1960 a 30/12/2015) |
| `dim_cliente` | 105 |
| `br_filme_genero` | 10.413 |
| `br_filme_ator` | 18.828 |
| `ft_desempenho_filme` | 3.888 |
| `ft_vendas_ingressos` | 1.440 |

As consultas de duplicados de `02_consultas_verificacao.sql` devem retornar 0 linhas, e
`03_validacao_meta_smart.sql` deve retornar três linhas (lançamentos de 2011 a 2015, com
recomendações geradas só com 1960–2010):

| Grupo | Filmes | Prejuízo | Nota do público | Cumpre a meta |
|---|---|---|---|---|
| Linha de base | 865 | 27,4% | 63,72 | — |
| Regra inicial (só taxa de prejuízo) | 198 | 20,7% | 61,70 (−2,02) | não |
| Regra final (prejuízo e nota histórica) | 75 | 18,7% | 64,53 (+0,82) | sim |

A meta exige prejuízo de no máximo 21,9% (20% abaixo da linha de base) sem que a nota caia
mais de 2 pontos. A regra inicial reduz o prejuízo, mas a nota cai 2,02 pontos e viola a
restrição. A regra final acrescenta um critério de qualidade: a nota média histórica do
público na combinação precisa ser pelo menos igual à média histórica geral. Com ele, a regra
cumpre as duas metas.

## Tratamento histórico (SCD)

| Dimensão | Tipo | Carga |
|---|---|---|
| `DIM_FILME` | SCD 2 (chave natural `id_imdb`) | `tr_11`, step Dimension Lookup/Update |
| `DIM_PRODUTORA` | SCD 1 (chave natural: nome) | `tr_12`, `INSERT ... WHERE NOT EXISTS` |
| `DIM_GENERO` | SCD 1 | `tr_13` (gêneros do TMDB e da base de vendas) |
| `DIM_DIRETOR`, `DIM_ATOR` | SCD 1 (chave natural: `nconst` do IMDb) | `tr_14` e `tr_15`, inserem os novos e sobrescrevem nome e ano de nascimento |
| `DIM_TEMPO` | SCD 1 | `tr_16`, que também reclassifica a janela de mercado das datas já existentes |
| `DIM_CLIENTE` | SCD 1 (combinação de faixa etária, assento e grupo) | `tr_17` |

Nenhuma fonte traz identificador estável de empresas, então a produtora não é versionada: uma
mudança de nome seria lida como uma nova empresa. Diretores e atores são identificados pelo
`nconst` do IMDb, o que separa homônimos (por exemplo, os dois diretores chamados George Miller).
