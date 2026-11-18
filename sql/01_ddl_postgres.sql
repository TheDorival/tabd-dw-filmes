-- =====================================================================
-- DDL DE IMPLANTACAO DO DATA WAREHOUSE - sch_dw_filmes (PostgreSQL 16)
-- Projeto: Analise multidimensional do desempenho de filmes
--
-- Fontes integradas:
--   TMDB Movies (tmdb-movies.csv)    filmes, orcamento, receita, generos, produtoras
--   TMDB 5000 (tmdb_5000_movies.csv) orcamento e receita ausentes no TMDB Movies
--   IMDb (title.basics, title.ratings, title.principals, name.basics)
--                                    nota do publico, diretores e elenco (nconst)
--   Rotten Tomatoes (rotten_tomatoes_movies.csv)
--                                    nota da critica e classificacao indicativa
--   Cinema Hall Ticket Sales (cinema_hall_ticket_sales.csv)
--                                    venda de ingressos e perfil do espectador
--
-- Modelo: constelacao de fatos - FT_DESEMPENHO_FILME e FT_VENDAS_INGRESSOS,
-- com DIM_GENERO compartilhada; 7 dimensoes e 2 tabelas-ponte.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS sch_dw_filmes;
CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public;
SET search_path TO sch_dw_filmes;

-- ---------------------------------------------------------------------
-- 1. FUNCOES DE APOIO
-- ---------------------------------------------------------------------
-- Corrige texto gravado em UTF-8 e lido como Windows-1252 ou Latin-1
-- ("JoffÃ©" -> "Joffé", "Ã‰ditions" -> "Éditions"). Texto ja correto nao
-- converte sem erro e e devolvido sem alteracao.
CREATE OR REPLACE FUNCTION sch_dw_filmes.fn_corrige_codificacao(p_texto TEXT)
RETURNS TEXT LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_texto IS NULL OR p_texto !~ '[ÃÂ]' THEN
        RETURN p_texto;
    END IF;
    BEGIN
        RETURN convert_from(convert_to(p_texto, 'WIN1252'), 'UTF8');
    EXCEPTION WHEN OTHERS THEN
        RETURN convert_from(convert_to(p_texto, 'LATIN1'), 'UTF8');
    END;
EXCEPTION WHEN OTHERS THEN
    RETURN p_texto;
END $$;

-- Normaliza titulos para o casamento TMDB x Rotten Tomatoes: sem acentos,
-- minusculas, "&" -> "and", so letras e numeros e sem artigo inicial.
CREATE OR REPLACE FUNCTION sch_dw_filmes.fn_normaliza_titulo(p_texto TEXT)
RETURNS TEXT LANGUAGE sql STABLE AS $$
    SELECT regexp_replace(
             btrim(regexp_replace(
               regexp_replace(
                 replace(lower(public.unaccent(sch_dw_filmes.fn_corrige_codificacao(p_texto))), '&', ' and '),
                 '[^a-z0-9]+', ' ', 'g'),
               '\s+', ' ', 'g')),
             '^(the|a|an) ', '')
$$;

-- ---------------------------------------------------------------------
-- 2. SEQUENCIAS (chaves substitutas)
-- ---------------------------------------------------------------------
CREATE SEQUENCE sch_dw_filmes.seq_dim_filme     START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_diretor   START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_ator      START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_produtora START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_genero    START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_tempo     START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE sch_dw_filmes.seq_dim_cliente   START WITH 1 INCREMENT BY 1;

-- ---------------------------------------------------------------------
-- 3. AREA DE STAGING (tabelas tecnicas; truncadas e recarregadas a cada
--    execucao do job; nao fazem parte do modelo dimensional)
-- ---------------------------------------------------------------------
-- Filmes do TMDB Movies que passam nos filtros de qualidade.
CREATE TABLE sch_dw_filmes.stg_tmdb_movies (
    imdb_id               VARCHAR(12)    NOT NULL,
    id_tmdb               VARCHAR(12),
    original_title        VARCHAR(400),
    overview              VARCHAR(4000),
    runtime               NUMERIC(4),
    release_year          NUMERIC(4),
    release_date          DATE,
    director              VARCHAR(1000),
    cast_raw              VARCHAR(2000),
    genres_raw            VARCHAR(400),
    production_companies_raw VARCHAR(1000),
    vote_average          NUMERIC(4,2),
    vote_count            NUMERIC(10),
    budget                NUMERIC(14,2),
    revenue               NUMERIC(14,2),
    budget_adj            NUMERIC(14,2),
    revenue_adj           NUMERIC(14,2),
    origem_financeiro     VARCHAR(10)    DEFAULT 'TMDB' NOT NULL
);
ALTER TABLE sch_dw_filmes.stg_tmdb_movies ADD CONSTRAINT stg_tmdb_movies_pk PRIMARY KEY (imdb_id);

-- Filmes descartados apenas por orcamento ou receita zerados: candidatos a
-- recuperacao pelo TMDB 5000 (mesmas colunas, sem chave: ainda nao deduplicados).
CREATE TABLE sch_dw_filmes.stg_tmdb_sem_financeiro (LIKE sch_dw_filmes.stg_tmdb_movies);
ALTER TABLE sch_dw_filmes.stg_tmdb_sem_financeiro ALTER COLUMN origem_financeiro DROP NOT NULL;

CREATE TABLE sch_dw_filmes.stg_tmdb5000 (
    id_tmdb   VARCHAR(12),
    budget    VARCHAR(20),
    revenue   VARCHAR(20)
);

CREATE TABLE sch_dw_filmes.stg_imdb_titulos (
    tconst          VARCHAR(12),
    primary_title   VARCHAR(500),
    original_title  VARCHAR(500),
    start_year      VARCHAR(10)
);

CREATE TABLE sch_dw_filmes.stg_imdb_notas (
    tconst          VARCHAR(12),
    average_rating  VARCHAR(10),
    num_votes       VARCHAR(12)
);

CREATE TABLE sch_dw_filmes.stg_imdb_principais (
    tconst    VARCHAR(12),
    ordering  VARCHAR(5),
    nconst    VARCHAR(12),
    category  VARCHAR(30)
);

CREATE TABLE sch_dw_filmes.stg_imdb_nomes (
    nconst        VARCHAR(12),
    primary_name  VARCHAR(300),
    birth_year    VARCHAR(10)
);

CREATE TABLE sch_dw_filmes.stg_rt_filmes (
    rt_link               VARCHAR(200),
    movie_title           VARCHAR(500),
    original_release_date VARCHAR(20),
    directors             VARCHAR(2000),
    content_rating        VARCHAR(10),
    tomatometer_rating    VARCHAR(10),
    tomatometer_count     VARCHAR(10),
    audience_rating       VARCHAR(10),
    audience_count        VARCHAR(12)
);

-- Resultado do casamento TMDB x Rotten Tomatoes (auditavel).
CREATE TABLE sch_dw_filmes.stg_ponte_rt (
    imdb_id   VARCHAR(12)   NOT NULL,
    rt_link   VARCHAR(200)  NOT NULL,
    criterio  VARCHAR(40)   NOT NULL
);
ALTER TABLE sch_dw_filmes.stg_ponte_rt ADD CONSTRAINT stg_ponte_rt_pk PRIMARY KEY (imdb_id);

CREATE TABLE sch_dw_filmes.stg_cinema_hall (
    nr_linha          INTEGER,
    ticket_id         VARCHAR(10),
    age               VARCHAR(5),
    ticket_price      VARCHAR(10),
    movie_genre       VARCHAR(30),
    seat_type         VARCHAR(20),
    number_of_person  VARCHAR(10),
    purchase_again    VARCHAR(5)
);

-- ---------------------------------------------------------------------
-- 4. DIMENSOES
-- ---------------------------------------------------------------------
-- DIM_FILME: SCD Tipo 2 (chave natural estavel: id_imdb).
CREATE TABLE sch_dw_filmes.dim_filme (
    sk_filme                 INTEGER        NOT NULL,
    id_imdb                  VARCHAR(12)    NOT NULL,
    titulo                   VARCHAR(200)   NOT NULL,
    titulo_original          VARCHAR(200),
    sinopse                  VARCHAR(2000),
    duracao_minutos          NUMERIC(4),
    classificacao_indicativa VARCHAR(10),
    ano_lancamento           NUMERIC(4)     NOT NULL,
    dat_inicio_vigencia      DATE DEFAULT CURRENT_DATE NOT NULL,
    dat_fim_vigencia         DATE DEFAULT DATE '9999-12-31' NOT NULL,
    ind_atual                SMALLINT DEFAULT 1 NOT NULL,
    versao                   INTEGER DEFAULT 1 NOT NULL
);
ALTER TABLE sch_dw_filmes.dim_filme ADD CONSTRAINT dim_filme_pk PRIMARY KEY (sk_filme);
ALTER TABLE sch_dw_filmes.dim_filme ADD CONSTRAINT dim_filme_ck_atual CHECK (ind_atual IN (0,1));
ALTER TABLE sch_dw_filmes.dim_filme ADD CONSTRAINT dim_filme_ck_vigencia CHECK (dat_fim_vigencia >= dat_inicio_vigencia);
CREATE INDEX dim_filme_ix_imdb ON sch_dw_filmes.dim_filme (id_imdb);

-- DIM_DIRETOR e DIM_ATOR: SCD Tipo 1, chave natural = nconst do IMDb.
CREATE TABLE sch_dw_filmes.dim_diretor (
    sk_diretor      INTEGER        NOT NULL,
    id_nconst       VARCHAR(12)    NOT NULL,
    nome_diretor    VARCHAR(120)   NOT NULL,
    ano_nascimento  NUMERIC(4)
);
ALTER TABLE sch_dw_filmes.dim_diretor ADD CONSTRAINT dim_diretor_pk PRIMARY KEY (sk_diretor);
ALTER TABLE sch_dw_filmes.dim_diretor ADD CONSTRAINT dim_diretor_uk UNIQUE (id_nconst);

CREATE TABLE sch_dw_filmes.dim_ator (
    sk_ator         INTEGER        NOT NULL,
    id_nconst       VARCHAR(12)    NOT NULL,
    nome_ator       VARCHAR(120)   NOT NULL,
    ano_nascimento  NUMERIC(4)
);
ALTER TABLE sch_dw_filmes.dim_ator ADD CONSTRAINT dim_ator_pk PRIMARY KEY (sk_ator);
ALTER TABLE sch_dw_filmes.dim_ator ADD CONSTRAINT dim_ator_uk UNIQUE (id_nconst);

-- DIM_PRODUTORA: SCD Tipo 1. A chave natural e o nome (nenhuma fonte traz
-- identificador da empresa), e nao ha atributos a versionar.
CREATE TABLE sch_dw_filmes.dim_produtora (
    sk_produtora        INTEGER        NOT NULL,
    nome_produtora      VARCHAR(150)   NOT NULL
);
ALTER TABLE sch_dw_filmes.dim_produtora ADD CONSTRAINT dim_produtora_pk PRIMARY KEY (sk_produtora);
ALTER TABLE sch_dw_filmes.dim_produtora ADD CONSTRAINT dim_produtora_uk UNIQUE (nome_produtora);

-- DIM_GENERO: compartilhada pelas duas tabelas fato.
CREATE TABLE sch_dw_filmes.dim_genero (
    sk_genero    INTEGER       NOT NULL,
    nome_genero  VARCHAR(50)   NOT NULL
);
ALTER TABLE sch_dw_filmes.dim_genero ADD CONSTRAINT dim_genero_pk PRIMARY KEY (sk_genero);
ALTER TABLE sch_dw_filmes.dim_genero ADD CONSTRAINT dim_genero_uk UNIQUE (nome_genero);

CREATE TABLE sch_dw_filmes.dim_tempo (
    sk_tempo        INTEGER       NOT NULL,
    data            DATE          NOT NULL,
    ano             NUMERIC(4)    NOT NULL,
    semestre        NUMERIC(1)    NOT NULL,
    trimestre       NUMERIC(1)    NOT NULL,
    mes             NUMERIC(2)    NOT NULL,
    nom_mes         VARCHAR(9)    NOT NULL,
    dia             NUMERIC(2)    NOT NULL,
    dia_semana      VARCHAR(13)   NOT NULL,
    ind_fim_semana  NUMERIC(1)    NOT NULL,
    ano_mes         VARCHAR(7)    NOT NULL,
    janela_mercado  VARCHAR(20)   NOT NULL
);
ALTER TABLE sch_dw_filmes.dim_tempo ADD CONSTRAINT dim_tempo_pk PRIMARY KEY (sk_tempo);
ALTER TABLE sch_dw_filmes.dim_tempo ADD CONSTRAINT dim_tempo_uk UNIQUE (data);
ALTER TABLE sch_dw_filmes.dim_tempo ADD CONSTRAINT dim_tempo_ck_trim CHECK (trimestre BETWEEN 1 AND 4);
ALTER TABLE sch_dw_filmes.dim_tempo ADD CONSTRAINT dim_tempo_ck_mes CHECK (mes BETWEEN 1 AND 12);
ALTER TABLE sch_dw_filmes.dim_tempo ADD CONSTRAINT dim_tempo_ck_janela
    CHECK (janela_mercado IN ('Fim de Ano', 'Verao', 'Premiacoes', 'Regular'));

-- DIM_CLIENTE: perfil do espectador (dimensao de combinacoes, SCD Tipo 1).
-- A base de vendas nao identifica pessoas: o membro e a combinacao de faixa
-- etaria, tipo de assento e tamanho do grupo.
CREATE TABLE sch_dw_filmes.dim_cliente (
    sk_cliente      INTEGER       NOT NULL,
    faixa_etaria    VARCHAR(10)   NOT NULL,
    tipo_assento    VARCHAR(20)   NOT NULL,
    tamanho_grupo   VARCHAR(20)   NOT NULL
);
ALTER TABLE sch_dw_filmes.dim_cliente ADD CONSTRAINT dim_cliente_pk PRIMARY KEY (sk_cliente);
ALTER TABLE sch_dw_filmes.dim_cliente ADD CONSTRAINT dim_cliente_uk UNIQUE (faixa_etaria, tipo_assento, tamanho_grupo);

-- ---------------------------------------------------------------------
-- 4.1 MEMBRO ZERO (linha "desconhecido", SK = 0)
-- ---------------------------------------------------------------------
INSERT INTO sch_dw_filmes.dim_filme
    (sk_filme, id_imdb, titulo, ano_lancamento, dat_inicio_vigencia, dat_fim_vigencia, ind_atual, versao)
VALUES (0, 'N/D', '(nao informado)', 0, DATE '1900-01-01', DATE '9999-12-31', 1, 1);
INSERT INTO sch_dw_filmes.dim_produtora (sk_produtora, nome_produtora) VALUES (0, '(nao informado)');
INSERT INTO sch_dw_filmes.dim_diretor (sk_diretor, id_nconst, nome_diretor) VALUES (0, 'N/D', '(nao informado)');

-- ---------------------------------------------------------------------
-- 5. TABELAS-PONTE (relacionamentos muitos-para-muitos)
-- ---------------------------------------------------------------------
CREATE TABLE sch_dw_filmes.br_filme_ator (
    sk_filme        INTEGER   NOT NULL,
    sk_ator         INTEGER   NOT NULL,
    ordem_credito   NUMERIC(3) NOT NULL,
    ind_principal   SMALLINT  DEFAULT 0 NOT NULL
);
ALTER TABLE sch_dw_filmes.br_filme_ator ADD CONSTRAINT br_filme_ator_pk PRIMARY KEY (sk_filme, sk_ator);
ALTER TABLE sch_dw_filmes.br_filme_ator ADD CONSTRAINT br_filme_ator_fk_filme FOREIGN KEY (sk_filme) REFERENCES sch_dw_filmes.dim_filme (sk_filme);
ALTER TABLE sch_dw_filmes.br_filme_ator ADD CONSTRAINT br_filme_ator_fk_ator FOREIGN KEY (sk_ator) REFERENCES sch_dw_filmes.dim_ator (sk_ator);
ALTER TABLE sch_dw_filmes.br_filme_ator ADD CONSTRAINT br_filme_ator_ck_princ CHECK (ind_principal IN (0,1));

CREATE TABLE sch_dw_filmes.br_filme_genero (
    sk_filme       INTEGER   NOT NULL,
    sk_genero      INTEGER   NOT NULL,
    ind_principal  SMALLINT  DEFAULT 0 NOT NULL
);
ALTER TABLE sch_dw_filmes.br_filme_genero ADD CONSTRAINT br_filme_genero_pk PRIMARY KEY (sk_filme, sk_genero);
ALTER TABLE sch_dw_filmes.br_filme_genero ADD CONSTRAINT br_filme_genero_fk_filme FOREIGN KEY (sk_filme) REFERENCES sch_dw_filmes.dim_filme (sk_filme);
ALTER TABLE sch_dw_filmes.br_filme_genero ADD CONSTRAINT br_filme_genero_fk_gen FOREIGN KEY (sk_genero) REFERENCES sch_dw_filmes.dim_genero (sk_genero);
ALTER TABLE sch_dw_filmes.br_filme_genero ADD CONSTRAINT br_filme_genero_ck_princ CHECK (ind_principal IN (0,1));

-- ---------------------------------------------------------------------
-- 6. TABELAS FATO
-- ---------------------------------------------------------------------
-- FT_DESEMPENHO_FILME: grao = um filme.
CREATE TABLE sch_dw_filmes.ft_desempenho_filme (
    sk_filme                 INTEGER       NOT NULL,
    sk_diretor               INTEGER       NOT NULL,
    sk_produtora             INTEGER       NOT NULL,
    sk_tempo_lancamento      INTEGER       NOT NULL,
    orcamento                NUMERIC(14,2) NOT NULL,
    receita_bilheteria       NUMERIC(14,2) NOT NULL,
    roi                      NUMERIC(14,4) NOT NULL,
    roi_normalizado          NUMERIC(5,2)  NOT NULL,
    nota_publico             NUMERIC(5,2),
    votos_publico            NUMERIC(10)   DEFAULT 0,
    nota_critica             NUMERIC(5,2),
    votos_critica            NUMERIC(8)    DEFAULT 0,
    nota_publico_tmdb        NUMERIC(5,2),
    nota_publico_rt          NUMERIC(5,2),
    indice_sucesso_integrado NUMERIC(5,2)  NOT NULL,
    ind_isi_completo         SMALLINT      DEFAULT 0 NOT NULL,
    origem_financeiro        VARCHAR(10)   NOT NULL
);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_pk PRIMARY KEY (sk_filme, sk_diretor, sk_produtora, sk_tempo_lancamento);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_uk_filme UNIQUE (sk_filme);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_fk_filme FOREIGN KEY (sk_filme) REFERENCES sch_dw_filmes.dim_filme (sk_filme);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_fk_diretor FOREIGN KEY (sk_diretor) REFERENCES sch_dw_filmes.dim_diretor (sk_diretor);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_fk_produtora FOREIGN KEY (sk_produtora) REFERENCES sch_dw_filmes.dim_produtora (sk_produtora);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_fk_tempo FOREIGN KEY (sk_tempo_lancamento) REFERENCES sch_dw_filmes.dim_tempo (sk_tempo);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_ck_orcamento CHECK (orcamento > 0);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_ck_notas CHECK (
    (nota_publico IS NULL OR nota_publico BETWEEN 0 AND 100) AND
    (nota_critica IS NULL OR nota_critica BETWEEN 0 AND 100));
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_ck_isi CHECK (indice_sucesso_integrado BETWEEN 0 AND 100);
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_ck_isi_completo CHECK (ind_isi_completo IN (0,1));
ALTER TABLE sch_dw_filmes.ft_desempenho_filme ADD CONSTRAINT ft_desemp_ck_origem CHECK (origem_financeiro IN ('TMDB', 'TMDB 5000'));

-- FT_VENDAS_INGRESSOS: grao = um ingresso vendido (uma linha da base de vendas).
-- A base nao identifica o filme nem a data da sessao; a ligacao com o restante
-- do modelo e feita pelo genero do filme (DIM_GENERO, compartilhada).
CREATE TABLE sch_dw_filmes.ft_vendas_ingressos (
    nr_ingresso       INTEGER       NOT NULL,
    id_ingresso       VARCHAR(10)   NOT NULL,
    sk_genero         INTEGER       NOT NULL,
    sk_cliente        INTEGER       NOT NULL,
    idade             NUMERIC(3)    NOT NULL,
    preco_ingresso    NUMERIC(6,2)  NOT NULL,
    qtd_pessoas       NUMERIC(2)    NOT NULL,
    ind_recompra      SMALLINT      NOT NULL
);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_pk PRIMARY KEY (nr_ingresso);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_fk_genero FOREIGN KEY (sk_genero) REFERENCES sch_dw_filmes.dim_genero (sk_genero);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_fk_cliente FOREIGN KEY (sk_cliente) REFERENCES sch_dw_filmes.dim_cliente (sk_cliente);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_ck_preco CHECK (preco_ingresso > 0);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_ck_pessoas CHECK (qtd_pessoas BETWEEN 1 AND 20);
ALTER TABLE sch_dw_filmes.ft_vendas_ingressos ADD CONSTRAINT ft_vendas_ck_recompra CHECK (ind_recompra IN (0,1));

-- ---------------------------------------------------------------------
-- 7. COMENTARIOS DE DOCUMENTACAO
-- ---------------------------------------------------------------------
COMMENT ON TABLE sch_dw_filmes.ft_desempenho_filme IS 'Fato de desempenho. Grao: uma linha por filme.';
COMMENT ON TABLE sch_dw_filmes.ft_vendas_ingressos IS 'Fato de vendas. Grao: um ingresso (linha da base Cinema Hall). Liga-se ao modelo pelo genero.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.roi IS '(receita_bilheteria - orcamento) / orcamento';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.roi_normalizado IS 'Posto percentil do ROI (PERCENT_RANK) x 100, recalculado para toda a tabela a cada carga.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.nota_publico IS 'averageRating do IMDb x 10 (0 a 100); vote_average do TMDB x 10 quando o filme nao tem nota no IMDb.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.votos_publico IS 'numVotes do IMDb (vote_count do TMDB quando nao ha nota no IMDb).';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.nota_critica IS 'Tomatometer do Rotten Tomatoes (0 a 100); nulo quando o filme nao foi casado com o RT.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.indice_sucesso_integrado IS 'ISI = 0,40 * roi_normalizado + 0,30 * nota_publico + 0,30 * nota_critica; sem nota da critica, (0,40 * roi_normalizado + 0,30 * nota_publico) / 0,70.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.ind_isi_completo IS '1 quando o ISI usa as tres componentes; 0 quando falta a nota da critica.';
COMMENT ON COLUMN sch_dw_filmes.ft_desempenho_filme.origem_financeiro IS 'TMDB (tmdb-movies.csv) ou TMDB 5000 (orcamento e receita recuperados e corrigidos para US$ de 2010).';
COMMENT ON TABLE sch_dw_filmes.dim_produtora IS 'Dimensao SCD Tipo 1: chave natural = nome da produtora.';
COMMENT ON TABLE sch_dw_filmes.dim_cliente IS 'Perfil do espectador: faixa etaria x tipo de assento x tamanho do grupo.';
COMMENT ON COLUMN sch_dw_filmes.dim_tempo.janela_mercado IS 'Fim de Ano (15/11-31/12), Verao (01/05-31/08), Premiacoes (01/01-fim de fev.) ou Regular.';
COMMENT ON TABLE sch_dw_filmes.stg_ponte_rt IS 'Casamento TMDB x Rotten Tomatoes por titulo normalizado e ano (+-1), com desempate pelo diretor.';

-- =====================================================================
-- FIM DO SCRIPT
-- =====================================================================
