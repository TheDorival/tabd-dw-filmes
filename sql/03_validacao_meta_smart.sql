-- =====================================================================
-- VALIDACAO RETROSPECTIVA DA META SMART (Apendice C da documentacao)
-- Indicadores: taxa de prejuizo (proporcao de filmes com ROI < 0) e nota
-- media do publico (IMDb x 10).
-- Meta: taxa de prejuizo pelo menos 20% menor que a da linha de base, sem
-- que a nota media do publico caia mais de 2 pontos.
-- Recomendacoes geradas so com os lancamentos de 1960 a 2010:
--   Regra inicial - combinacoes genero principal x janela de mercado com
--     pelo menos 15 filmes e taxa de prejuizo no terco inferior.
--   Regra final   - regra inicial E nota media historica do publico na
--     combinacao maior ou igual a nota media historica geral.
-- Avaliacao nos lancamentos de 2011 a 2015 (periodo nao usado para gerar
-- as recomendacoes). Resultado: Tabela da Meta SMART na documentacao.
-- =====================================================================
SET search_path TO sch_dw_filmes;
WITH base AS (
    SELECT f.sk_filme, t.ano, t.janela_mercado, g.nome_genero AS genero,
           f.roi, f.nota_publico AS nota,
           CASE WHEN f.roi < 0 THEN 1 ELSE 0 END AS prejuizo
      FROM ft_desempenho_filme f
      JOIN dim_tempo       t  ON t.sk_tempo  = f.sk_tempo_lancamento
      JOIN br_filme_genero bg ON bg.sk_filme = f.sk_filme AND bg.ind_principal = 1
      JOIN dim_genero      g  ON g.sk_genero = bg.sk_genero
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
