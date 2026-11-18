# Roteiro do vídeo — Execução das cargas (Parte 2)

Cobre, nesta ordem, os 5 pontos exigidos pelo professor. Duração estimada: 8–12 min.
Todos os comandos abaixo assumem o terminal aberto em `~/dev/dw-filmes-etl` e o Postgres já
rodando (`docker compose up -d` — ver README.md).

Duas formas de rodar a carga estão descritas: pelo **Spoon** (interface gráfica, mostra a aba
*Step Metrics* com linhas lidas/gravadas por step) ou pelo **Kitchen** (linha de comando, mostra
o mesmo log que foi usado para gerar `logs/execucao_01...log`). Escolha uma ou mostre as duas.

---

## 0. Preparação (fora da gravação, ou nos primeiros segundos)

Resetar o banco para o estado "zero" antes de gravar:

```bash
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes -c "DROP SCHEMA sch_dw_filmes CASCADE;"
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes < sql/01_ddl_postgres.sql
```

## 1. Mostrar as tabelas vazias antes da execução

Narrar: "o schema foi criado, mas ainda não carregamos nada". Rodar:

```bash
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes -f /dev/stdin < sql/02_consultas_verificacao.sql
```

A primeira consulta (contagem por tabela) deve mostrar **0 em todas as linhas**. Pode encerrar
o `psql` por aqui nesta etapa (as próximas consultas do mesmo arquivo vão dar erro em dimensões
vazias — ok ignorar, o ponto já foi demonstrado).

## 2. Executar a carga e mostrar o log com linhas lidas/gravadas

**Opção A — Spoon (GUI):**
1. Abrir o Spoon (`pentaho` no menu, ou comando `spoon.sh` dentro de
   `data-integration/`), abrir `etl/jb_carga_dw_filmes.kjb`.
2. Rodar (F9 ou botão play). Acompanhar o painel inferior: cada entrada do job abre sua
   transformation; clicar em cada uma mostra a aba **Step Metrics** com colunas
   *Read/Written/Input/Output* por step — é exatamente a prova de "quantidade de registros
   lidos e gravados" pedida.
3. Destacar especialmente `tr_01_stg_tmdb_movies` (funil de filtros, 10.866 → 3.807) e
   `tr_02_dim_filme`/`tr_03_dim_produtora` (coluna *Output* = número de linhas realmente
   inseridas pelo *Dimension Lookup/Update*).

**Opção B — Kitchen (linha de comando):**

```bash
DI="/nix/store/azr1m1275fmdiph7n588byhs10klga8s-pentaho-data-integration-9.4.0.0-343/data-integration"
cd "$DI"
bash kitchen.sh -file=~/dev/dw-filmes-etl/etl/jb_carga_dw_filmes.kjb -level=Basic
```

O log impresso no terminal mostra, para cada step, uma linha
`Finished processing (I=..., O=..., R=..., W=..., U=..., E=...)` — I=lidas na entrada,
O=gravadas na saída (ex.: inseridas/atualizadas), W=passadas adiante. Esse é o mesmo formato
salvo em `logs/execucao_01_primeira_carga.log`, que pode ser aberto lado a lado como referência
do que se espera ver.

## 3. Mostrar os dados gravados e conferir a quantidade

```bash
docker exec -i dw_filmes_pg psql -U dw_filmes -d dw_filmes -f /dev/stdin < sql/02_consultas_verificacao.sql
```

Comentar a primeira tabela de contagens comparando com os números documentados na seção 13.2
de `docs/documentacao_etl_parte2.md` (ex.: `ft_desempenho_filme` = 3.807, `dim_ator` = 6.747).
Rodar também a última consulta do arquivo (top 10 por Índice de Sucesso Integrado) para mostrar
dado de negócio real, não só contagens.

## 4. Mostrar que não há dados duplicados

Mesmo arquivo `sql/02_consultas_verificacao.sql`, itens 2 a 4 (procurar duplicado por chave
natural em cada dimensão, por `sk_filme` na fato, e por chave composta nas tabelas-ponte).
Narrar: "todas essas consultas deveriam retornar zero linhas — e retornam", mostrando o
`(0 rows)` de cada uma na tela.

## 5. Reexecutar a carga (simulando agendamento diário/semanal) e provar que não duplicou

1. Rodar a contagem por tabela (item 1 da consulta) e **anotar/mostrar os números na tela**.
2. Rodar o job de novo (igual ao passo 2, Opção A ou B), **sem** resetar o schema desta vez —
   é exatamente isso que simula uma segunda execução agendada sobre um banco que já tem dados.
3. Rodar a contagem por tabela de novo: os números devem ser **idênticos** ao passo (1).
4. Se usou Kitchen, apontar no log a linha do *Dimension Lookup/Update* de `tr_02_dim_filme`:
   na 1ª execução `O=3807` (inseriu), na 2ª execução `O=0` (processou tudo, não inseriu nada
   de novo) — a prova mais direta de que a carga é idempotente.
5. Rodar de novo as consultas de duplicados do item 4: continuam todas em `(0 rows)`.

Fechar o vídeo com uma frase de conclusão: a carga pode ser reexecutada quantas vezes for
necessário (diária, semanal) sem gerar duplicidade, porque cada dimensão usa uma estratégia de
*upsert*/SCD apropriada (Dimension Lookup/Update para SCD2, `INSERT ... WHERE NOT EXISTS` para
as dimensões planas, `ON CONFLICT ... DO UPDATE` na fato).
