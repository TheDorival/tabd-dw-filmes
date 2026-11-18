-- =====================================================================
-- VIEWS DE ANALISE - perguntas de negocio (secao 2.4) e Meta SMART
-- Aplicar depois de 01_ddl_postgres.sql (e reaplicar se o schema for
-- recriado). Sao a fonte unica dos graficos da documentacao, dos slides
-- e do dashboard no Metabase.
--
-- Convencoes:
--   ISI      = indice_sucesso_integrado (0 a 100)
--   nota     = nota_publico (averageRating do IMDb x 10, escala 0 a 100)
--   critica  = nota_critica (Tomatometer do Rotten Tomatoes, 0 a 100)
--   ROI      = (receita - orcamento) / orcamento; as colunas *_pct estao em %
--   prejuizo = ROI < 0
--   ator principal  = br_filme_ator.ind_principal = 1 (1o do elenco)
--   genero principal = br_filme_genero.ind_principal = 1 (1o genero)
-- =====================================================================
SET search_path TO sch_dw_filmes;

-- Recria todas as views (as dependentes de vw_filme caem junto).
DROP VIEW IF EXISTS sch_dw_filmes.vw_filme CASCADE;
DROP VIEW IF EXISTS sch_dw_filmes.vw_p09_desvio_isi_genero;
DROP VIEW IF EXISTS sch_dw_filmes.vw_p12_perfil_espectador;
DROP VIEW IF EXISTS sch_dw_filmes.vw_meta_smart;

-- ---------------------------------------------------------------------
-- Base: um filme por linha, com as cinco variaveis de decisao.
-- Tambem serve de tabela de detalhe/filtros no Metabase.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_filme AS
SELECT f.sk_filme,
       df.titulo,
       t.data            AS data_lancamento,
       t.ano, t.mes, t.trimestre, t.janela_mercado,
       (t.ano / 10) * 10 AS decada,
       d.nome_diretor    AS diretor,
       p.nome_produtora  AS produtora,
       g.nome_genero     AS genero_principal,
       a.nome_ator       AS ator_principal,
       ba.sk_ator        AS sk_ator_principal,
       f.orcamento,
       f.receita_bilheteria AS receita,
       f.roi,
       f.roi_normalizado,
       f.nota_publico    AS nota,
       f.votos_publico   AS votos,
       f.indice_sucesso_integrado AS isi,
       (f.roi < 0)       AS prejuizo,
       f.nota_critica    AS critica,
       f.votos_critica,
       f.nota_publico_tmdb,
       f.nota_publico_rt,
       f.ind_isi_completo,
       f.origem_financeiro,
       df.classificacao_indicativa
  FROM sch_dw_filmes.ft_desempenho_filme f
  JOIN sch_dw_filmes.dim_filme     df ON df.sk_filme = f.sk_filme
  JOIN sch_dw_filmes.dim_tempo     t  ON t.sk_tempo  = f.sk_tempo_lancamento
  JOIN sch_dw_filmes.dim_diretor   d  ON d.sk_diretor = f.sk_diretor
  JOIN sch_dw_filmes.dim_produtora p  ON p.sk_produtora = f.sk_produtora
  LEFT JOIN sch_dw_filmes.br_filme_genero bg ON bg.sk_filme = f.sk_filme AND bg.ind_principal = 1
  LEFT JOIN sch_dw_filmes.dim_genero      g  ON g.sk_genero = bg.sk_genero
  LEFT JOIN sch_dw_filmes.br_filme_ator   ba ON ba.sk_filme = f.sk_filme AND ba.ind_principal = 1
  LEFT JOIN sch_dw_filmes.dim_ator        a  ON a.sk_ator   = ba.sk_ator;


-- ---------------------------------------------------------------------
-- P1. Qual combinacao de diretor e ator ou atriz principal apresenta o
--     maior ISI medio, considerando apenas duplas com pelo menos tres
--     filmes juntos?
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p01_dupla_diretor_ator AS
SELECT diretor, ator_principal,
       COUNT(*)            AS filmes,
       ROUND(AVG(isi), 1)  AS isi_medio,
       ROUND(100 * PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi)::numeric, 1) AS roi_mediano_pct,
       ROUND(AVG(nota), 1) AS nota_media
  FROM sch_dw_filmes.vw_filme
 WHERE ator_principal IS NOT NULL
 GROUP BY diretor, ator_principal
HAVING COUNT(*) >= 3
 ORDER BY isi_medio DESC;


-- ---------------------------------------------------------------------
-- P2. Qual e a variacao do ROI e da nota do publico entre filmes de um
--     mesmo diretor com atores principais diferentes?
--     Diretores com pelo menos 3 atores principais distintos. Para cada
--     diretor: ROI mediano e nota media de cada ator principal, e a
--     amplitude (maior - menor) entre eles.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p02_variacao_diretor AS
WITH por_dupla AS (
    SELECT diretor, ator_principal,
           COUNT(*) AS filmes,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi) AS roi_mediano,
           AVG(nota) AS nota_media
      FROM sch_dw_filmes.vw_filme
     WHERE ator_principal IS NOT NULL
     GROUP BY diretor, ator_principal
)
SELECT diretor,
       COUNT(*)    AS atores_principais,
       SUM(filmes) AS filmes,
       ROUND(100 * MIN(roi_mediano)::numeric, 1) AS roi_mediano_min_pct,
       ROUND(100 * MAX(roi_mediano)::numeric, 1) AS roi_mediano_max_pct,
       ROUND(100 * (MAX(roi_mediano) - MIN(roi_mediano))::numeric, 1) AS amplitude_roi_pct,
       ROUND(MIN(nota_media)::numeric, 1) AS nota_min,
       ROUND(MAX(nota_media)::numeric, 1) AS nota_max,
       ROUND((MAX(nota_media) - MIN(nota_media))::numeric, 1) AS amplitude_nota
  FROM por_dupla
 GROUP BY diretor
HAVING COUNT(*) >= 3
 ORDER BY filmes DESC;


-- ---------------------------------------------------------------------
-- P3. Qual mes ou janela de mercado concentra as maiores receitas e as
--     maiores notas do publico e da critica, por genero?
--     Genero principal x janela (minimo de 10 filmes na combinacao). As
--     colunas pos_* indicam a posicao da janela dentro de cada genero
--     (1 = maior receita mediana / maior nota do publico / da critica).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p03_genero_janela AS
WITH combinacao AS (
    SELECT genero_principal, janela_mercado,
           COUNT(*) AS filmes,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY receita) AS receita_mediana,
           AVG(nota) AS nota_media,
           AVG(critica) AS critica_media
      FROM sch_dw_filmes.vw_filme
     GROUP BY genero_principal, janela_mercado
    HAVING COUNT(*) >= 10
)
SELECT genero_principal, janela_mercado, filmes,
       ROUND((receita_mediana / 1e6)::numeric, 1) AS receita_mediana_mi,
       ROUND(nota_media, 1) AS nota_media,
       ROW_NUMBER() OVER (PARTITION BY genero_principal ORDER BY receita_mediana DESC) AS pos_receita,
       ROW_NUMBER() OVER (PARTITION BY genero_principal ORDER BY nota_media DESC)      AS pos_nota,
       ROUND(critica_media, 1) AS critica_media,
       ROW_NUMBER() OVER (PARTITION BY genero_principal ORDER BY critica_media DESC NULLS LAST) AS pos_critica
  FROM combinacao
 ORDER BY genero_principal, janela_mercado;


-- ---------------------------------------------------------------------
-- P4. Qual e o desempenho medio dos lancamentos do primeiro trimestre em
--     comparacao com os da janela de fim de ano?
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p04_trimestre1_fim_de_ano AS
SELECT CASE WHEN trimestre = 1 THEN '1o trimestre (jan-mar)'
            ELSE 'Fim de ano (15/11-31/12)' END AS periodo,
       COUNT(*) AS filmes,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY receita) / 1e6)::numeric, 1) AS receita_mediana_mi,
       ROUND(100 * PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi)::numeric, 1)      AS roi_mediano_pct,
       ROUND(AVG(nota), 1)  AS nota_media,
       ROUND(AVG(isi), 1)   AS isi_medio,
       ROUND(100.0 * AVG(prejuizo::int), 1) AS taxa_prejuizo_pct
  FROM sch_dw_filmes.vw_filme
 WHERE trimestre = 1 OR janela_mercado = 'Fim de Ano'
 GROUP BY 1
 ORDER BY 1;


-- ---------------------------------------------------------------------
-- P5. Quais combinacoes de genero principal e janela de lancamento
--     apresentam a menor taxa de prejuizo (ROI negativo), considerando
--     apenas combinacoes com pelo menos 15 filmes?
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p05_prejuizo_genero_janela AS
SELECT genero_principal, janela_mercado,
       COUNT(*) AS filmes,
       ROUND(100.0 * AVG(prejuizo::int), 1) AS taxa_prejuizo_pct,
       ROUND(100 * PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi)::numeric, 1) AS roi_mediano_pct,
       ROUND(AVG(nota), 1) AS nota_media
  FROM sch_dw_filmes.vw_filme
 GROUP BY genero_principal, janela_mercado
HAVING COUNT(*) >= 15
 ORDER BY taxa_prejuizo_pct, filmes DESC;


-- ---------------------------------------------------------------------
-- P6. Qual produtora apresenta o maior ISI proporcional ao orcamento
--     investido?
--     Metrica: ISI medio por US$ 10 milhoes de orcamento medio
--     (ISI medio / (orcamento medio / 10 mi)), em US$ de 2010.
--     Produtora principal do filme; minimo de 10 filmes.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p06_produtora_isi_orcamento AS
SELECT produtora,
       COUNT(*) AS filmes,
       ROUND(AVG(isi), 1) AS isi_medio,
       ROUND((AVG(orcamento) / 1e6)::numeric, 1) AS orcamento_medio_mi,
       ROUND((AVG(isi) / (AVG(orcamento) / 1e7))::numeric, 2) AS isi_por_10mi
  FROM sch_dw_filmes.vw_filme
 WHERE produtora <> '(nao informado)'
 GROUP BY produtora
HAVING COUNT(*) >= 10
 ORDER BY isi_por_10mi DESC;


-- ---------------------------------------------------------------------
-- P7. A partir de que faixa de orcamento o ROI mediano deixa de crescer?
--     Dez faixas com o mesmo numero de filmes (decis do orcamento, em US$
--     de 2010) e a variacao do ROI mediano em relacao a faixa anterior.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p07_faixa_orcamento AS
WITH faixas AS (
    SELECT orcamento, roi, prejuizo, NTILE(10) OVER (ORDER BY orcamento) AS faixa
      FROM sch_dw_filmes.vw_filme
),
resumo AS (
    SELECT faixa,
           COUNT(*) AS filmes,
           MIN(orcamento) AS orc_min, MAX(orcamento) AS orc_max,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY orcamento) AS orc_mediano,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi) AS roi_mediano,
           AVG(prejuizo::int) AS taxa_prejuizo
      FROM faixas
     GROUP BY faixa
)
SELECT faixa, filmes,
       ROUND((orc_min / 1e6)::numeric, 1)     AS orcamento_min_mi,
       ROUND((orc_max / 1e6)::numeric, 1)     AS orcamento_max_mi,
       ROUND((orc_mediano / 1e6)::numeric, 1) AS orcamento_mediano_mi,
       ROUND(100 * roi_mediano::numeric, 1)   AS roi_mediano_pct,
       ROUND(100 * (roi_mediano - LAG(roi_mediano) OVER (ORDER BY faixa))::numeric, 1) AS variacao_vs_faixa_anterior_pp,
       ROUND(100.0 * taxa_prejuizo, 1)        AS taxa_prejuizo_pct
  FROM resumo
 ORDER BY faixa;


-- ---------------------------------------------------------------------
-- P8. Qual e a diferenca de nota do publico entre filmes cujo ator
--     principal teve outro lancamento nos doze meses anteriores e os
--     demais?
--     "Outro lancamento" = qualquer filme da base em que o ator aparece
--     no elenco (qualquer posicao), lancado nos 365 dias anteriores.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p08_lancamento_anterior AS
WITH filmes_do_ator AS (
    SELECT ba.sk_ator, t.data
      FROM sch_dw_filmes.br_filme_ator ba
      JOIN sch_dw_filmes.ft_desempenho_filme f ON f.sk_filme = ba.sk_filme
      JOIN sch_dw_filmes.dim_tempo t ON t.sk_tempo = f.sk_tempo_lancamento
),
classificado AS (
    SELECT v.nota, v.isi,
           EXISTS (SELECT 1 FROM filmes_do_ator o
                    WHERE o.sk_ator = v.sk_ator_principal
                      AND o.data >= v.data_lancamento - 365
                      AND o.data <  v.data_lancamento) AS teve_lancamento_anterior
      FROM sch_dw_filmes.vw_filme v
     WHERE v.sk_ator_principal IS NOT NULL
)
SELECT CASE WHEN teve_lancamento_anterior THEN 'Com lancamento nos 12 meses anteriores'
            ELSE 'Sem lancamento nos 12 meses anteriores' END AS grupo,
       COUNT(*) AS filmes,
       ROUND(AVG(nota), 2)    AS nota_media,
       ROUND(STDDEV(nota), 2) AS desvio_nota,
       ROUND(AVG(isi), 1)     AS isi_medio
  FROM classificado
 GROUP BY 1
 ORDER BY 1;


-- ---------------------------------------------------------------------
-- P9. Quais generos cinematograficos apresentam a menor variacao - medida
--     pelo desvio-padrao - do ISI?
--     Cada filme conta em todos os seus generos (tabela-ponte), como na
--     analise exploratoria; minimo de 50 filmes por genero.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p09_desvio_isi_genero AS
SELECT g.nome_genero AS genero,
       COUNT(*) AS filmes,
       ROUND(AVG(f.indice_sucesso_integrado), 1)    AS isi_medio,
       ROUND(STDDEV(f.indice_sucesso_integrado), 2) AS desvio_padrao_isi
  FROM sch_dw_filmes.ft_desempenho_filme f
  JOIN sch_dw_filmes.br_filme_genero bg ON bg.sk_filme = f.sk_filme
  JOIN sch_dw_filmes.dim_genero g ON g.sk_genero = bg.sk_genero
 GROUP BY g.nome_genero
HAVING COUNT(*) >= 50
 ORDER BY desvio_padrao_isi;


-- ---------------------------------------------------------------------
-- P10. Qual das cinco variaveis - elenco, genero, diretor, produtora ou
--      janela de lancamento - mais discrimina o sucesso historico?
--      Metrica: parcela da variancia do ISI explicada pela variavel,
--      corrigida pelo numero de categorias (epsilon-quadrado):
--        eps2 = (SQ_entre - (k - 1) * QM_dentro) / SQ_total
--      Categorias com menos de 5 filmes sao agrupadas em "Outros", para
--      que diretores, atores e produtoras com um unico filme nao
--      "expliquem" artificialmente o proprio resultado.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p10_discriminacao_variaveis AS
WITH base AS (
    SELECT isi,
           COALESCE(ator_principal, '(sem elenco)')   AS elenco,
           COALESCE(genero_principal, '(sem genero)') AS genero,
           diretor, produtora, janela_mercado AS janela
      FROM sch_dw_filmes.vw_filme
),
longa AS (
    SELECT 'Elenco (ator principal)' AS variavel, elenco AS categoria, isi FROM base
    UNION ALL SELECT 'Genero (principal)', genero, isi FROM base
    UNION ALL SELECT 'Diretor', diretor, isi FROM base
    UNION ALL SELECT 'Produtora (principal)', produtora, isi FROM base
    UNION ALL SELECT 'Janela de lancamento', janela, isi FROM base
),
agrupada AS (
    SELECT variavel,
           CASE WHEN COUNT(*) OVER (PARTITION BY variavel, categoria) >= 5
                THEN categoria ELSE 'Outros' END AS categoria,
           isi
      FROM longa
),
medias AS (
    SELECT variavel, categoria, AVG(isi) AS media_cat
      FROM agrupada GROUP BY variavel, categoria
),
geral AS (
    SELECT AVG(isi) AS media_geral, COUNT(*) AS n_total FROM base
),
sq AS (
    SELECT a.variavel,
           SUM((a.isi - g.media_geral)^2)       AS sq_total,
           SUM((m.media_cat - g.media_geral)^2) AS sq_entre,
           SUM((a.isi - m.media_cat)^2)         AS sq_dentro,
           COUNT(DISTINCT a.categoria)          AS k,
           COUNT(DISTINCT a.categoria) FILTER (WHERE a.categoria <> 'Outros') AS k_proprias,
           MAX(g.n_total)                       AS n
      FROM agrupada a
      JOIN medias m ON m.variavel = a.variavel AND m.categoria = a.categoria
      CROSS JOIN geral g
     GROUP BY a.variavel
)
SELECT variavel,
       k_proprias AS categorias_com_5_ou_mais_filmes,
       ROUND((sq_entre / sq_total)::numeric, 3) AS eta2,
       ROUND(((sq_entre - (k - 1) * sq_dentro / (n - k)) / sq_total)::numeric, 3) AS epsilon2
  FROM sq
 ORDER BY epsilon2 DESC;


-- ---------------------------------------------------------------------
-- P11. Quais combinacoes de genero principal e janela de lancamento
--      entregam ROI elevado sem que a aprovacao da critica ou do publico
--      caia abaixo de 70?
--      "Sucesso equilibrado" = ROI acima do ROI mediano de todos os filmes
--      E nota da critica >= 70 E nota do publico >= 70. Considera apenas
--      filmes com nota da critica e combinacoes com pelo menos 15 deles.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p11_sucesso_equilibrado AS
WITH mediana AS (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi) AS roi_mediano
      FROM sch_dw_filmes.vw_filme
),
base AS (
    SELECT v.genero_principal, v.janela_mercado, v.roi, v.nota, v.critica,
           (v.roi > m.roi_mediano AND v.critica >= 70 AND v.nota >= 70) AS equilibrado
      FROM sch_dw_filmes.vw_filme v CROSS JOIN mediana m
     WHERE v.critica IS NOT NULL
)
SELECT genero_principal, janela_mercado,
       COUNT(*) AS filmes,
       COUNT(*) FILTER (WHERE equilibrado) AS filmes_equilibrados,
       ROUND(100.0 * AVG(equilibrado::int), 1) AS taxa_equilibrio_pct,
       ROUND(100 * PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roi)::numeric, 1) AS roi_mediano_pct,
       ROUND(AVG(critica), 1) AS critica_media,
       ROUND(AVG(nota), 1) AS nota_media
  FROM base
 GROUP BY genero_principal, janela_mercado
HAVING COUNT(*) >= 15
 ORDER BY taxa_equilibrio_pct DESC, filmes DESC;


-- ---------------------------------------------------------------------
-- P12. Qual perfil de espectador (faixa etaria) concentra a compra de
--      ingressos e a intencao de recompra, por genero?
--      FT_VENDAS_INGRESSOS x DIM_GENERO x DIM_CLIENTE. A base de vendas nao
--      identifica filme nem data: a analise e por genero e perfil.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_p12_perfil_espectador AS
SELECT g.nome_genero AS genero,
       c.faixa_etaria,
       COUNT(*) AS ingressos,
       SUM(v.qtd_pessoas) AS pessoas,
       ROUND(AVG(v.preco_ingresso), 2) AS preco_medio,
       ROUND(100.0 * AVG(v.ind_recompra), 1) AS taxa_recompra_pct,
       ROUND(100.0 * AVG((c.tipo_assento <> 'Padrao')::int), 1) AS pct_assento_superior,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY g.nome_genero), 1) AS pct_ingressos_do_genero
  FROM sch_dw_filmes.ft_vendas_ingressos v
  JOIN sch_dw_filmes.dim_genero  g ON g.sk_genero  = v.sk_genero
  JOIN sch_dw_filmes.dim_cliente c ON c.sk_cliente = v.sk_cliente
 GROUP BY g.nome_genero, c.faixa_etaria
 ORDER BY g.nome_genero, c.faixa_etaria;


-- ---------------------------------------------------------------------
-- META SMART - validacao retrospectiva (mesma logica do arquivo 03).
-- Recomendacoes geradas so com 1960-2010; avaliadas em 2011-2015.
-- Metas: taxa de prejuizo pelo menos 20% menor que a da linha de base e
-- nota media do publico no maximo 2 pontos abaixo da linha de base.
-- Regra inicial: combinacoes genero x janela (>= 15 filmes) no terco
--   inferior da taxa de prejuizo historica.
-- Regra final: regra inicial E nota media historica do publico na
--   combinacao >= nota media historica geral (criterio de qualidade,
--   tambem calculado so com 1960-2010). A regra inicial reduzia o
--   prejuizo mas ficava 2,02 pontos abaixo na nota, violando a restricao.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW sch_dw_filmes.vw_meta_smart AS
WITH base AS (
    SELECT ano, janela_mercado, genero_principal AS genero, roi, nota,
           prejuizo::int AS prejuizo
      FROM sch_dw_filmes.vw_filme
     WHERE genero_principal IS NOT NULL
),
historico AS (
    SELECT genero, janela_mercado, AVG(prejuizo) AS taxa_prejuizo,
           AVG(nota) AS nota_media
      FROM base WHERE ano <= 2010
     GROUP BY genero, janela_mercado
    HAVING COUNT(*) >= 15
),
nota_historica AS (
    SELECT AVG(nota) AS nota FROM base WHERE ano <= 2010
),
inicial AS (
    SELECT genero, janela_mercado, nota_media FROM historico
     WHERE taxa_prejuizo <= (SELECT PERCENTILE_CONT(1.0/3) WITHIN GROUP (ORDER BY taxa_prejuizo) FROM historico)
),
final AS (
    SELECT genero, janela_mercado FROM inicial
     WHERE nota_media >= (SELECT nota FROM nota_historica)
),
teste AS (
    SELECT b.*,
           (i.genero IS NOT NULL) AS regra_inicial,
           (f.genero IS NOT NULL) AS regra_final
      FROM base b
      LEFT JOIN inicial i ON i.genero = b.genero AND i.janela_mercado = b.janela_mercado
      LEFT JOIN final   f ON f.genero = b.genero AND f.janela_mercado = b.janela_mercado
     WHERE b.ano BETWEEN 2011 AND 2015
),
linha_base AS (
    SELECT AVG(prejuizo) AS taxa, AVG(nota) AS nota FROM teste
),
grupos AS (
    SELECT 1 AS ordem, 'Linha de base (todos os lancamentos 2011-2015)' AS grupo, t.* FROM teste t
    UNION ALL
    SELECT 2, 'Regra inicial (so taxa de prejuizo)', t.* FROM teste t WHERE regra_inicial
    UNION ALL
    SELECT 3, 'Regra final (prejuizo e nota historica)', t.* FROM teste t WHERE regra_final
)
SELECT g.ordem, g.grupo,
       COUNT(DISTINCT (g.genero, g.janela_mercado)) AS combinacoes,
       COUNT(*) AS filmes,
       ROUND(100.0 * AVG(g.prejuizo), 1) AS taxa_prejuizo_pct,
       ROUND(100 * PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY g.roi)::numeric, 1) AS roi_mediano_pct,
       ROUND(AVG(g.nota), 2) AS nota_media,
       ROUND(AVG(g.nota) - MAX(lb.nota), 2) AS diferenca_nota,
       ROUND(100.0 * (1 - AVG(g.prejuizo) / MAX(lb.taxa)), 1) AS reducao_prejuizo_pct,
       ROUND(100.0 * MAX(lb.taxa) * 0.8, 1) AS meta_taxa_prejuizo_pct,
       ROUND(MAX(lb.nota) - 2, 2) AS meta_nota_minima,
       (AVG(g.prejuizo) <= MAX(lb.taxa) * 0.8 AND AVG(g.nota) >= MAX(lb.nota) - 2) AS cumpre_meta
  FROM grupos g CROSS JOIN linha_base lb
 GROUP BY g.ordem, g.grupo
 ORDER BY g.ordem;
