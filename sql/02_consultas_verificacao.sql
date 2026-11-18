-- =====================================================================
-- CONSULTAS DE VERIFICACAO - validam cada carga do DW_FILMES
-- =====================================================================
SET search_path TO sch_dw_filmes;

-- 1) Contagem de linhas por tabela (comparar antes e depois de cada carga).
SELECT 'stg_tmdb_movies' AS tabela, COUNT(*) AS linhas FROM stg_tmdb_movies
UNION ALL SELECT 'stg_ponte_rt', COUNT(*) FROM stg_ponte_rt
UNION ALL SELECT 'dim_filme', COUNT(*) FROM dim_filme
UNION ALL SELECT 'dim_diretor', COUNT(*) FROM dim_diretor
UNION ALL SELECT 'dim_ator', COUNT(*) FROM dim_ator
UNION ALL SELECT 'dim_produtora', COUNT(*) FROM dim_produtora
UNION ALL SELECT 'dim_genero', COUNT(*) FROM dim_genero
UNION ALL SELECT 'dim_tempo', COUNT(*) FROM dim_tempo
UNION ALL SELECT 'dim_cliente', COUNT(*) FROM dim_cliente
UNION ALL SELECT 'br_filme_genero', COUNT(*) FROM br_filme_genero
UNION ALL SELECT 'br_filme_ator', COUNT(*) FROM br_filme_ator
UNION ALL SELECT 'ft_desempenho_filme', COUNT(*) FROM ft_desempenho_filme
UNION ALL SELECT 'ft_vendas_ingressos', COUNT(*) FROM ft_vendas_ingressos
ORDER BY 1;

-- 2) Ausencia de duplicados na chave natural de cada dimensao (0 linhas).
SELECT 'dim_filme (id_imdb, versao corrente)' AS verificacao, id_imdb, COUNT(*)
FROM dim_filme WHERE ind_atual = 1 GROUP BY id_imdb HAVING COUNT(*) > 1;

SELECT 'dim_diretor (id_nconst)', id_nconst, COUNT(*)
FROM dim_diretor GROUP BY id_nconst HAVING COUNT(*) > 1;

SELECT 'dim_ator (id_nconst)', id_nconst, COUNT(*)
FROM dim_ator GROUP BY id_nconst HAVING COUNT(*) > 1;

SELECT 'dim_produtora (nome_produtora)', nome_produtora, COUNT(*)
FROM dim_produtora GROUP BY nome_produtora HAVING COUNT(*) > 1;

SELECT 'dim_genero (nome_genero)', nome_genero, COUNT(*)
FROM dim_genero GROUP BY nome_genero HAVING COUNT(*) > 1;

SELECT 'dim_tempo (data)', data, COUNT(*)
FROM dim_tempo GROUP BY data HAVING COUNT(*) > 1;

SELECT 'dim_cliente (perfil)', faixa_etaria, tipo_assento, tamanho_grupo, COUNT(*)
FROM dim_cliente GROUP BY faixa_etaria, tipo_assento, tamanho_grupo HAVING COUNT(*) > 1;

-- 2.1) Janela de mercado conforme o calendario (0 linhas).
SELECT 'dim_tempo (janela fora do calendario)', data, janela_mercado
FROM dim_tempo
WHERE janela_mercado <> CASE
        WHEN (mes = 11 AND dia >= 15) OR mes = 12 THEN 'Fim de Ano'
        WHEN mes BETWEEN 5 AND 8 THEN 'Verao'
        WHEN mes IN (1,2) THEN 'Premiacoes'
        ELSE 'Regular' END;

-- 3) Ausencia de duplicados nas tabelas fato (0 linhas).
SELECT 'ft_desempenho_filme (sk_filme)' AS verificacao, sk_filme, COUNT(*)
FROM ft_desempenho_filme GROUP BY sk_filme HAVING COUNT(*) > 1;

SELECT 'ft_vendas_ingressos (nr_ingresso)' AS verificacao, nr_ingresso, COUNT(*)
FROM ft_vendas_ingressos GROUP BY nr_ingresso HAVING COUNT(*) > 1;

-- 4) Ausencia de duplicados nas tabelas-ponte (0 linhas).
SELECT 'br_filme_genero (sk_filme, sk_genero)' AS verificacao, sk_filme, sk_genero, COUNT(*)
FROM br_filme_genero GROUP BY sk_filme, sk_genero HAVING COUNT(*) > 1;

SELECT 'br_filme_ator (sk_filme, sk_ator)' AS verificacao, sk_filme, sk_ator, COUNT(*)
FROM br_filme_ator GROUP BY sk_filme, sk_ator HAVING COUNT(*) > 1;

-- 5) Casamento com o Rotten Tomatoes: uma pagina do RT por filme (0 linhas).
SELECT 'stg_ponte_rt (rt_link)' AS verificacao, rt_link, COUNT(*)
FROM stg_ponte_rt GROUP BY rt_link HAVING COUNT(*) > 1;

-- 6) Cobertura das fontes na tabela fato.
SELECT COUNT(*)                                            AS filmes,
       COUNT(*) FILTER (WHERE origem_financeiro = 'TMDB 5000') AS financeiro_recuperado_tmdb5000,
       COUNT(nota_critica)                                 AS com_nota_da_critica,
       SUM(ind_isi_completo)                               AS isi_com_tres_componentes,
       COUNT(*) FILTER (WHERE sk_diretor = 0)              AS sem_diretor_no_imdb
FROM ft_desempenho_filme;

-- 7) Consulta de negocio de exemplo: top 10 filmes por ISI.
SELECT f.titulo, f.ano_lancamento, d.nome_diretor, p.nome_produtora,
       x.roi_normalizado, x.nota_publico, x.nota_critica, x.indice_sucesso_integrado
FROM ft_desempenho_filme x
JOIN dim_filme f ON f.sk_filme = x.sk_filme
JOIN dim_diretor d ON d.sk_diretor = x.sk_diretor
JOIN dim_produtora p ON p.sk_produtora = x.sk_produtora
ORDER BY x.indice_sucesso_integrado DESC
LIMIT 10;
