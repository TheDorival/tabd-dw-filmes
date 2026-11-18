# Resumo da análise exploratória

Gerado por `eda/analise_exploratoria.py` a partir de `data/tmdb-movies.csv` e do DW carregado.

## 1. Completude de tmdb-movies.csv (10.866 linhas)

| coluna | ausentes | zerados | % das linhas |
|---|---|---|---|
| revenue_adj | 0 | 6.016 | 55,4 |
| budget_adj | 0 | 5.696 | 52,4 |
| production_companies | 1.030 | 0 | 9,5 |
| cast | 76 | 0 | 0,7 |
| director | 44 | 0 | 0,4 |
| runtime | 0 | 31 | 0,3 |
| genres | 23 | 0 | 0,2 |
| imdb_id | 10 | 0 | 0,1 |

## 2. Cobertura das fontes no DW (3.888 filmes)

| fonte | filmes | % dos filmes do DW |
|---|---|---|
| TMDB Movies (orçamento e receita) | 3.807 | 97,9 |
| TMDB 5000 (orçamento e receita recuperados) | 81 | 2,1 |
| IMDb (nota do público) | 3.886 | 99,9 |
| Rotten Tomatoes (nota da crítica) | 3.570 | 91,8 |

## 3. Estatísticas descritivas

| medida | média | desvio-padrão | 1º quartil | mediana | 3º quartil | máximo | n |
|---|---|---|---|---|---|---|---|
| Orçamento (US$ mi de 2010) | 44,4 | 44,7 | 13,4 | 30,3 | 60,8 | 425,0 | 3.888 |
| Receita (US$ mi de 2010) | 137,3 | 215,2 | 19,0 | 62,4 | 164,5 | 2.827,1 | 3.888 |
| ROI (%) | 55.179,5 | 2.291.436,5 | -11,0 | 113,5 | 322,0 | 101.863.153,4 | 3.888 |
| Nota do público - IMDb (0–100) | 64,9 | 9,6 | 59,0 | 66,0 | 72,0 | 93,0 | 3.888 |
| Nota da crítica - RT (0–100) | 55,0 | 27,4 | 31,0 | 57,0 | 80,0 | 100,0 | 3.570 |
| ISI (0–100) | 55,9 | 18,2 | 42,0 | 55,4 | 70,3 | 96,3 | 3.888 |

- Taxa de prejuízo (ROI < 0): 27,4%
- Média do ROI / mediana do ROI: 486 vezes

## 4. ISI médio por gênero (cada filme em todos os seus gêneros)

| genero | filmes | isi |
|---|---|---|
| Filme para TV | 1 | 78,2 |
| Documentário | 32 | 71,5 |
| Animação | 204 | 61,1 |
| História | 134 | 60,1 |
| Faroeste | 57 | 59,2 |
| Guerra | 123 | 59,1 |
| Música | 136 | 58,8 |
| Família | 422 | 57,5 |
| Drama | 1.768 | 57,3 |
| Aventura | 751 | 56,1 |
| Romance | 672 | 55,7 |
| Crime | 664 | 55,6 |
| Comédia | 1.366 | 55,3 |
| Fantasia | 402 | 54,2 |
| Ficção científica | 527 | 54,1 |
| Mistério | 349 | 54,0 |
| Suspense | 1.219 | 53,5 |
| Ação | 1.107 | 53,3 |
| Terror | 469 | 53,1 |
| Estrangeiro | 10 | 37,5 |

## 5. Desempenho por janela de mercado

| janela_mercado | filmes | roi_mediano | nota_publico | nota_critica | isi | prejuizo |
|---|---|---|---|---|---|---|
| Fim de Ano | 579 | 156,1 | 67,6 | 60,6 | 60,2 | 20,4 |
| Premiacoes | 481 | 89,8 | 62,4 | 46,1 | 51,4 | 31,8 |
| Regular | 1.535 | 83,8 | 65,0 | 54,9 | 54,5 | 33,0 |
| Verao | 1.293 | 138,9 | 64,5 | 55,9 | 57,4 | 22,4 |

- Mês com maior ROI mediano: Jun (188%); menor: Set (44%)

## 6. Correlação de Spearman

|  | Orçamento | Receita | ROI | Nota público (IMDb) | Nota público (TMDB) | Nota crítica (RT) | Votos público | Votos crítica | Duração |
|---|---|---|---|---|---|---|---|---|---|
| Orçamento | 1,00 | 0,65 | -0,05 | 0,01 | -0,01 | -0,12 | 0,42 | 0,29 | 0,34 |
| Receita | 0,65 | 1,00 | 0,67 | 0,25 | 0,24 | 0,18 | 0,68 | 0,31 | 0,28 |
| ROI | -0,05 | 0,67 | 1,00 | 0,32 | 0,33 | 0,33 | 0,49 | 0,14 | 0,05 |
| Nota público (IMDb) | 0,01 | 0,25 | 0,32 | 1,00 | 0,91 | 0,81 | 0,52 | 0,19 | 0,41 |
| Nota público (TMDB) | -0,01 | 0,24 | 0,33 | 0,91 | 1,00 | 0,72 | 0,50 | 0,19 | 0,36 |
| Nota crítica (RT) | -0,12 | 0,18 | 0,33 | 0,81 | 0,72 | 1,00 | 0,38 | 0,18 | 0,26 |
| Votos público | 0,42 | 0,68 | 0,49 | 0,52 | 0,50 | 0,38 | 1,00 | 0,56 | 0,28 |
| Votos crítica | 0,29 | 0,31 | 0,14 | 0,19 | 0,19 | 0,18 | 0,56 | 1,00 | 0,19 |
| Duração | 0,34 | 0,28 | 0,05 | 0,41 | 0,36 | 0,26 | 0,28 | 0,19 | 1,00 |

## 7. Outliers de ROI (critério do intervalo interquartil)

- Limite superior: ROI acima de 822%
- Outliers: 353 filmes (9,1%)
- Filmes com orçamento < US$ 1.000: 25; com orçamento ou receita < US$ 1.000: 37

## 8. Crítica × público

- Correlação de Spearman entre a nota da crítica e a do público: 0,81
- Diferença média (crítica − público): -10,0 pontos

## 9. Tamanho das amostras por categoria

| variavel | categorias | com_1_filme | com_20_ou_mais |
|---|---|---|---|
| produtoras | 910 | 604 | 29 |
| diretores principais | 1.639 | 914 | 38 |

(para diretores, a última coluna conta os que têm 10 ou mais filmes)
