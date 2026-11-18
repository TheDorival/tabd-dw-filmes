# DOCUMENTAÇÃO DO PROJETO — PARTE 2

## Execução do ETL — Análise multidimensional do desempenho de filmes

Instituto Federal de Alagoas — Campus Maceió
Bacharelado em Sistemas de Informação — Tópicos Avançados em Bancos de Dados
Continuação de *Documentação do Projeto — Modelagem de um Data Warehouse* (Parte 1 / primeira nota)

---

## 9. Escopo desta fase

A Parte 1 definiu um modelo dimensional completo com duas tabelas fato (FT_DESEMPENHO_FILME e
FT_VENDAS_INGRESSOS) e nove dimensões/tabelas-ponte, alimentadas por quatro fontes: TMDB, IMDb,
Rotten Tomatoes e uma base transacional de venda de ingressos.

### 9.1 Ajuste de escopo em relação à Parte 1

No momento de implementar os planos de ETL, confirmou-se que apenas uma fonte estava
efetivamente disponível para esta fase: o dataset **TMDB Movies** (`tmdb-movies.csv`, 10.866
filmes, uma linha por filme, já consolidado a partir da API do TMDB por terceiros e incluindo
valores de orçamento e receita já ajustados por inflação — colunas `budget_adj`/`revenue_adj`).
Não havia, no momento da execução, um extrato de Rotten Tomatoes nem uma base de venda de
ingressos de cinema compatível com o dicionário de dados definido na Parte 1.

Diante disso, o escopo desta Parte 2 foi deliberadamente reduzido ao **data mart de desempenho**:

| Objeto do modelo (Parte 1) | Nesta fase |
|---|---|
| FT_DESEMPENHO_FILME | **Implementado e carregado** |
| DIM_FILME, DIM_DIRETOR, DIM_ATOR, DIM_PRODUTORA, DIM_GENERO, DIM_TEMPO | **Implementadas e carregadas** |
| BR_FILME_ATOR, BR_FILME_GENERO | **Implementadas e carregadas** |
| FT_VENDAS_INGRESSOS, DIM_SESSAO, DIM_CLIENTE | **Fora do escopo.** Criadas no script de implantação física (vazias), preservando a fidelidade ao modelo completo da Parte 1, e permanecem como trabalho futuro — a mesma limitação já registrada na seção 8 da Parte 1 ("a base de venda de ingressos não cobre a totalidade dos títulos"), agora estendida à ausência de dados de Rotten Tomatoes. |

Consequência direta: a coluna `NOTA_CRITICA` de FT_DESEMPENHO_FILME permanece `NULL` para todos
os registros (nenhuma fonte de crítica foi integrada nesta fase) e o Índice de Sucesso Integrado
foi **renormalizado** (seção 13.3) para usar apenas ROI (40%) e nota do público (30%), dividindo
o resultado por 0,70.

### 9.2 Ambiente e ferramentas desta fase

| Item | Escolha | Observação |
|---|---|---|
| Banco de dados | PostgreSQL 16 (container Docker) | A Parte 1 especificou Oracle; o DDL foi reescrito para PostgreSQL (seção 9.3) por viabilidade de execução/reprodução no ambiente de desenvolvimento. |
| Ferramenta de ETL | Pentaho Data Integration (Kettle) 9.4.0.0-343 | Mesma ferramenta prevista na Parte 1 (Quadro 2). |
| Orquestração | Job mestre `jb_carga_dw_filmes.kjb` encadeando 11 transformations | Execução via Spoon (GUI) ou Kitchen (linha de comando). |

### 9.3 Adaptação do DDL (Oracle → PostgreSQL)

O script `sql/01_ddl_postgres.sql` recria integralmente o schema `sch_dw_filmes` definido no
Anexo A da Parte 1, com as seguintes adaptações mecânicas: `NUMBER(p)` → `NUMERIC(p)`/`INTEGER`,
`NUMBER(1)` com `CHECK IN (0,1)` → `SMALLINT`, `VARCHAR2` → `VARCHAR`, `TO_DATE('31/12/9999', ...)`
→ `DATE '9999-12-31'`, remoção de `TABLESPACE`/`LOGGING` (conceitos específicos de Oracle), e
sequências Oracle recriadas como `CREATE SEQUENCE` nativo do PostgreSQL com os mesmos nomes
(`seq_dim_*`). Estrutura de tabelas, chaves primárias/estrangeiras e `CHECK`s foram preservados.

Duas adições técnicas, não previstas no dicionário de dados da Parte 1, foram necessárias:

- **Coluna `versao` em DIM_FILME e DIM_PRODUTORA**: exigida pelo step *Dimension Lookup/Update*
  do Pentaho para numerar as versões de uma dimensão SCD Tipo 2 (contador 1, 2, 3...,
  independente de `DAT_INICIO_VIGENCIA`/`DAT_FIM_VIGENCIA`).
- **Linha "membro zero" (SK = 0) em DIM_FILME, DIM_DIRETOR e DIM_PRODUTORA**: convenção clássica
  de Kimball para representar "desconhecido/não aplicável", e exigida tecnicamente pelo mesmo
  step do Pentaho, que verifica a existência dessa linha ao inicializar a dimensão.
- **Ampliação de `FT_DESEMPENHO_FILME.ROI` de `NUMBER(8,4)` para `NUMERIC(14,4)`**: a análise
  exploratória já prevista na seção 5.3.6 da Parte 1 (outliers de ROI) se confirmou na prática —
  alguns filmes do dataset têm `budget_adj` extremamente baixo (ex.: USD 224,80, provável erro de
  digitação na fonte original), produzindo ROI da ordem de 10⁶, que excedia a precisão original
  da coluna.

---

## 10. Área de staging

`stg_tmdb_movies` é uma tabela técnica (não faz parte do modelo dimensional da Parte 1) que
recebe o CSV já filtrado e deduplicado, servindo de fonte única para todas as cargas
subsequentes. É truncada e recarregada por completo a cada execução do job — a idempotência das
camadas seguintes (dimensões, pontes e fato) é o que garante a ausência de duplicados, não a
staging em si.

---

## 11. Documentação das transformations (.ktr)

Arquitetura adotada: steps nativos do Kettle (CSV Input, Filter Rows, Sort/Unique, *Dimension
Lookup/Update*) para extração e para as duas dimensões com versionamento histórico real
(DIM_FILME e DIM_PRODUTORA); e um step **Execute SQL Script** para as operações que são, por
natureza, operações de conjunto (explosão de listas `|`-separadas, geração de calendário,
estatística de percentil global) — o PostgreSQL resolve essas operações de forma nativamente
mais eficiente e com risco de erro muito menor do que a reprodução linha a linha no Kettle. Essa
é uma decisão de engenharia deliberada, documentada aqui para transparência da banca.

### 11.1 `tr_01_stg_tmdb_movies.ktr`
**Origem:** `data/tmdb-movies.csv`, referenciada no `.ktr` por caminho relativo à pasta da
transformação (`${Internal.Transformation.Filename.Directory}/../data/tmdb-movies.csv`) para
funcionar tanto no Windows quanto no Linux. **Destino:** `stg_tmdb_movies` (truncate + insert).
**Steps:** CSV Input → Select values (remove colunas não usadas; renomeia `cast`→`cast_raw`,
`genres`→`genres_raw`, `production_companies`→`production_companies_raw`) → 4 Filter Rows em
cadeia (`imdb_id` não nulo; `director` não nulo; `production_companies_raw` não nulo; orçamento
e receita ajustados `> 0`, pelo mesmo motivo da Parte 1 seção 6.1: ROI indefinido/enganoso com
orçamento zero) → Sort rows (`imdb_id` asc, `revenue_adj` desc) → Unique rows (`imdb_id`) →
Table Output. A combinação Sort+Unique deduplica por `imdb_id` mantendo a linha de maior receita
quando há mais de uma entrada para o mesmo filme (relançamentos), implementando a mesma
diretriz da Parte 1 seção 6.1 ("remoção de registros duplicados por relançamento").
**Resultado real medido:** 10.866 lidos → 3.807 gravados (detalhe do funil na seção 13.1).

### 11.2 `tr_02_dim_filme.ktr`
**Origem:** `stg_tmdb_movies` (um registro por filme). **Destino:** `dim_filme`.
**Steps:** Table Input → Get System Info (data de carga) → *Dimension Lookup/Update* (SCD
Tipo 2, chave natural `id_imdb`, campos rastreados `titulo`, `titulo_original`, `sinopse`,
`duracao_minutos`, `ano_lancamento`, chave substituta via `seq_dim_filme`).
**Adaptação:** a fonte usada nesta fase tem um único campo de título; `titulo` e
`titulo_original` recebem o mesmo valor (`original_title`). `classificacao_indicativa`
permanece `NULL` (não disponível na fonte).
**Comportamento de idempotência comprovado:** 3.807 linhas processadas; 1ª execução insere
3.807 (O=3807); reexecuções processam as mesmas 3.807 e não inserem nenhuma (O=0), pois nenhum
atributo rastreado mudou — o step reconhece que a versão corrente já reflete os dados de origem.

### 11.3 `tr_03_dim_produtora.ktr`
**Origem:** `stg_tmdb_movies.production_companies_raw`, explodido por `|` via SQL
(`unnest(string_to_array(...))`) dentro do próprio Table Input. **Destino:** `dim_produtora`.
**Steps:** Table Input (SQL com `unnest`+`DISTINCT`) → Get System Info → *Dimension Lookup/Update*
(SCD Tipo 2, chave natural `nome_produtora`, sequência `seq_dim_produtora`).
**Adaptação:** `pais_origem` não está disponível na fonte e permanece `NULL`; como não há
atributo descritivo variável além da própria chave, a dimensão não deve, na prática, gerar novas
versões (confirmado no teste de reexecução).
**Resultado real:** 3.264 produtoras distintas.

### 11.4 `tr_04_dim_genero.ktr`
Explosão de `genres_raw` por `|` via SQL, com `INSERT ... WHERE NOT EXISTS` idempotente contra
`dim_genero` (SCD Tipo 1 — tabela plana, sem necessidade de versionamento). **Resultado:** 20
gêneros distintos.

### 11.5 `tr_05_dim_diretor.ktr`
Explosão do campo `director` por `|` (alguns filmes têm mais de um diretor — descoberto durante
a implementação, ao se constatar que o campo também é multivalorado) via SQL, `INSERT ... WHERE
NOT EXISTS` contra `dim_diretor` (SCD Tipo 1). **Adaptação:** a fonte não traz `nconst` do IMDb
para profissionais; `id_nconst` recebe o próprio nome normalizado como chave natural.
**Resultado:** 1.754 diretores distintos (+ 1 membro zero). A tabela fato referencia apenas o
primeiro diretor listado (diretor principal).

### 11.6 `tr_06_dim_ator.ktr`
Explosão de `cast_raw` por `|`, **limitada aos 10 primeiros nomes** (elenco principal, para não
inflar desproporcionalmente a tabela-ponte com papéis secundários/figuração), `INSERT ... WHERE
NOT EXISTS` contra `dim_ator` (SCD Tipo 1, mesma adaptação de `id_nconst` da DIM_DIRETOR).
**Resultado:** 6.747 atores/atrizes distintos.

### 11.7 `tr_07_dim_tempo.ktr`
Gera o calendário completo entre o menor e o maior `release_date` observados em
`stg_tmdb_movies` (via `generate_series`), com `INSERT ... WHERE NOT EXISTS` por data.
**Classificação `JANELA_MERCADO`:** implementa exatamente o Quadro 4 da Parte 1 (calendário de
referência do mercado norte-americano, de onde provêm as bases de origem) — **Fim de Ano**
(15/11 a 31/12), **Verão/alta temporada** (01/05 a 31/08), **Janela de premiações** (01/01 a
28-29/02) e **Regular** (demais datas: março, abril, setembro, outubro e 1 a 14 de novembro).
Nomes de mês e dia da semana foram escritos sem acentuação (`Marco`, em vez de `Março`) para
evitar problemas de codificação entre ferramentas.
**Resultado:** 20.287 dias (1960-06-15 a 2015-12-30) — Fim de Ano: 2.631 · Verão: 6.843 ·
Premiações: 3.258 · Regular: 7.555.

### 11.8 `tr_08_br_filme_genero.ktr`
Recarrega a tabela-ponte para os filmes da carga atual: `DELETE` dos vínculos existentes desses
filmes seguido de `INSERT` a partir da explosão de `genres_raw`, com `IND_PRINCIPAL = 1` para o
primeiro gênero listado. Padrão delete-then-insert por filme, idempotente por construção.
**Resultado:** 10.185 vínculos (3.807 principais + 6.378 secundários).

### 11.9 `tr_09_br_filme_ator.ktr`
Mesmo padrão, para o elenco (limitado aos 10 primeiros nomes, `ORDEM_CREDITO` = posição de
billing, `IND_PRINCIPAL = 1` para a posição 1). Quando o mesmo nome aparece mais de uma vez no
elenco creditado do mesmo filme (ocorre em casos raros de dupla atuação), o `GROUP BY` com
`MIN(posição)` evita violar a chave primária composta `(sk_filme, sk_ator)`.
**Resultado:** 18.978 vínculos. Duas produções do dataset têm `cast_raw` vazio na fonte e,
portanto, não geram ator principal (3.805, não 3.807, com `IND_PRINCIPAL = 1`) — limitação da
fonte, não do processo de carga.

### 11.10 `tr_10_ft_desempenho_filme.ktr`
**Origem:** `stg_tmdb_movies`, com resolução de chaves substitutas via `JOIN`/`LEFT JOIN` contra
`dim_filme` (chave natural `imdb_id`, versão corrente), `dim_tempo` (`release_date`),
`dim_diretor` (primeiro nome de `director`) e `dim_produtora` (primeira produtora listada,
versão corrente). **Destino:** `ft_desempenho_filme`, via `INSERT ... ON CONFLICT ON CONSTRAINT
ft_desemp_uk_filme DO UPDATE` — um *upsert* nativo do PostgreSQL que casa pela chave de negócio
do grão (`sk_filme`, única por filme, embora a PK física seja composta por fidelidade ao
dicionário da Parte 1), garantindo que reexecuções **atualizem** a linha existente em vez de
duplicá-la. `ROI_NORMALIZADO` e `INDICE_SUCESSO_INTEGRADO` entram com valor provisório (0): são
estatísticas globais (percentil histórico do ROI de toda a tabela), recalculadas no passo
seguinte. **Resultado:** 3.807 linhas (mesma contagem da staging — todos os filmes filtrados
encontram diretor, produtora e data de lançamento válidos).

### 11.11 `tr_11_pos_carga.ktr`
Passo de pós-carga, executado após a fato: (1) sincroniza `IND_ATUAL` de `dim_filme` e
`dim_produtora` com `DAT_FIM_VIGENCIA` (o step *Dimension Lookup/Update* do Pentaho gerencia
apenas as datas de vigência, não essa *flag* adicional prevista no dicionário da Parte 1);
(2) recalcula, para **toda** a tabela `ft_desempenho_filme`, `ROI_NORMALIZADO` (percentil
histórico do ROI via `PERCENT_RANK() OVER (ORDER BY roi)`) e `INDICE_SUCESSO_INTEGRADO` (ver
seção 13.3). Por ser uma estatística de conjunto (o percentil de um filme depende de todos os
demais), este cálculo precisa ser refeito a cada carga, não é calculável linha a linha.

---

## 12. Documentação do job (`jb_carga_dw_filmes.kjb`)

Ordem de execução (sequencial, cada entrada aguarda a anterior):

```
Start
  -> 01 Staging TMDB
  -> 02 DIM_FILME          -> 03 DIM_PRODUTORA   -> 04 DIM_GENERO
  -> 05 DIM_DIRETOR        -> 06 DIM_ATOR        -> 07 DIM_TEMPO
  -> 08 BR_FILME_GENERO    -> 09 BR_FILME_ATOR
  -> 10 FT_DESEMPENHO_FILME
  -> 11 Pos-carga
  -> Carga concluida com sucesso
```

**Dependências:** as dimensões (02–07) dependem apenas da staging (01); as tabelas-ponte
(08–09) dependem de DIM_FILME, DIM_GENERO/DIM_ATOR já carregadas; a fato (10) depende de todas
as dimensões; o pós-carga (11) depende da fato. O job respeita essa ordem por meio de uma
cadeia sequencial única (não há paralelismo entre ramos), o que simplifica a leitura do fluxo
em troca de um tempo total de execução maior — aceitável dado o volume de dados desta fase
(~11 segundos por execução completa).

**Tratamento de erro:** cada uma das 11 transformations tem um hop condicional
(`evaluation=N`, "em caso de falha") para a entrada final `Carga abortada - verificar log`. Se
qualquer etapa falhar, o job interrompe a cadeia principal imediatamente e não prossegue com
dados parciais — nenhuma etapa posterior assume que uma etapa anterior com erro produziu dados
válidos.

---

## 13. Resultados da execução

*(Substitui o placeholder "[A COMPLETAR] Após a execução do ETL..." da seção 7 da Parte 1.)*

### 13.1 Funil de qualidade da staging (idêntico nas duas execuções)

| Etapa | Linhas |
|---|---|
| CSV lido | 10.866 |
| `imdb_id` presente | 10.856 |
| `director` presente | 10.816 |
| `production_companies` presente | 9.813 |
| orçamento ajustado > 0 | 5.031 |
| receita ajustada > 0 | 3.808 |
| após deduplicação por `imdb_id` (mantém maior receita) | **3.807** |

Cobertura financeira: apenas 35% dos 10.866 filmes do dataset têm orçamento **e** receita
divulgados e não nulos — consistente com o que a Parte 1 (seção 5.3.1) já previa qualitativamente
para campos financeiros do TMDB.

### 13.2 Volume carregado por tabela (1ª execução = 2ª execução, byte a byte)

| Tabela | Linhas |
|---|---|
| `dim_filme` | 3.808 (3.807 + 1 membro zero) |
| `dim_diretor` | 1.755 (1.754 + 1 membro zero) |
| `dim_ator` | 6.747 |
| `dim_produtora` | 3.265 (3.264 + 1 membro zero) |
| `dim_genero` | 20 |
| `dim_tempo` | 20.287 |
| `br_filme_genero` | 10.185 |
| `br_filme_ator` | 18.978 |
| `ft_desempenho_filme` | **3.807** |
| `dim_sessao` / `dim_cliente` / `ft_vendas_ingressos` (fora de escopo) | 0 / 0 / 0 |

### 13.3 Prova de não duplicação em reexecução

O job foi executado duas vezes em sequência contra o mesmo banco (sem recriar o schema entre
as execuções), simulando um agendamento diário/semanal — logs completos em
`logs/execucao_01_primeira_carga.log` e
`logs/execucao_02_segunda_carga_simulando_reagendamento.log`.

- As contagens de linhas por tabela (seção 13.2) foram **idênticas** antes e depois da 2ª
  execução.
- O step *Dimension Lookup/Update* de `tr_02_dim_filme` e `tr_03_dim_produtora` registrou, na
  2ª execução, `I=3807/3264` linhas processadas e **`O=0`** linhas de saída/inserção (contra
  `O=3807`/`O=3264` na 1ª execução) — ou seja, processou todas as linhas de origem mas não
  inseriu nenhuma versão nova, porque nada havia mudado.
- As consultas de verificação de duplicados (`sql/02_consultas_verificacao.sql`, itens 2–4)
  retornaram **0 linhas** em todas as dimensões, na tabela fato e nas tabelas-ponte, nas duas
  execuções.

### 13.4 Índice de Sucesso Integrado — nota de cálculo

Como Rotten Tomatoes não foi integrado nesta fase (seção 9.1), `NOTA_CRITICA` é `NULL` em todos
os registros e a fórmula da Parte 1 (seção 6.3) foi renormalizada para usar apenas as duas
componentes disponíveis, redistribuindo o peso da nota de crítica proporcionalmente:

```
ISI = (0,40 × ROI_normalizado + 0,30 × nota_publico) / 0,70
```

O top 10 por ISI na carga atual (consulta de exemplo em `sql/02_consultas_verificacao.sql`,
item 5) traz títulos consistentes com a expectativa qualitativa (*The Godfather*, *Psycho*,
*Pulp Fiction*, *Star Wars*, entre clássicos de grande orçamento/recepção), o que funciona como
teste de sanidade do cálculo.

---

## 14. Instruções de execução

Ver `README.md` na raiz do projeto para o passo a passo completo (subir o banco, aplicar o DDL,
rodar o job pelo Spoon ou pelo Kitchen).

---

## 15. Limitações e trabalho futuro

- Integrar Rotten Tomatoes (ou outra fonte de nota de crítica) e recalcular o Índice de Sucesso
  Integrado com a fórmula original de três componentes.
- Obter uma base de venda de ingressos compatível com o grão de `FT_VENDAS_INGRESSOS` e
  implementar `tr_12_dim_sessao`, `tr_13_dim_cliente` e `tr_14_ft_vendas_ingressos`.
- Caso se queira manter fidelidade total à Parte 1 (Oracle), o DDL em
  `sql/01_ddl_postgres.sql` serve de referência de mapeamento de tipos para reverter ao script
  Oracle original (Anexo A da Parte 1) quando uma instância Oracle estiver disponível.
