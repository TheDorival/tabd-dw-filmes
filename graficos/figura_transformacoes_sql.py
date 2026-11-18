"""Desenha a figura 'Origem, operacao e destino de cada step Execute SQL Script'.

Uso: python graficos/figura_transformacoes_sql.py
Saida: graficos/claro/fig_transformacoes_sql.png
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

plt.rcParams["text.parse_math"] = False
plt.rcParams["font.family"] = "Segoe UI"

LINHAS = [
    ("tr_03_stg_recupera_financeiro", ("stg sem financeiro", "+ stg_tmdb5000"),
     ("casa por id_tmdb; corrige inflação pelo", "fator do ano → INSERT na staging"), ("stg_tmdb_movies", "origem TMDB 5000")),
    ("tr_09_stg_ponte_rt", ("stg + IMDb", "+ stg_rt_filmes"),
     ("título normalizado + ano ±1 + diretor;", "regra um-para-um por rt_link"), ("stg_ponte_rt", "")),
    ("tr_12_dim_produtora", ("stg.production_", "companies_raw"),
     ("explode por \"|\" → corrige codificação →", "INSERT ... WHERE NOT EXISTS"), ("dim_produtora", "")),
    ("tr_13_dim_genero", ("stg.genres_raw", ""),
     ("explode por \"|\" → INSERT ... WHERE", "NOT EXISTS (Sci-Fi = Science Fiction)"), ("dim_genero", "")),
    ("tr_14_dim_diretor", ("stg_imdb_principais", "+ stg_imdb_nomes"),
     ("diretores por nconst →", "INSERT novos; UPDATE nome e nascimento"), ("dim_diretor", "")),
    ("tr_15_dim_ator", ("stg_imdb_principais", "+ stg_imdb_nomes"),
     ("5 primeiros do elenco por nconst →", "INSERT novos; UPDATE nome e nascimento"), ("dim_ator", "")),
    ("tr_16_dim_tempo", ("min/max release_date", ""),
     ("generate_series (1 linha/dia) → INSERT;", "UPDATE reclassifica JANELA_MERCADO"), ("dim_tempo", "")),
    ("tr_17_dim_cliente", ("stg_cinema_hall", ""),
     ("faixa etária, assento e grupo →", "INSERT ... WHERE NOT EXISTS"), ("dim_cliente", "")),
    ("tr_18_br_filme_genero", ("stg + dim_filme", "+ dim_genero"),
     ("DELETE vínculos dos filmes da carga →", "INSERT (1º gênero = principal)"), ("br_filme_genero", "")),
    ("tr_19_br_filme_ator", ("stg_imdb_principais", "+ dim_filme + dim_ator"),
     ("DELETE vínculos → INSERT com", "ordem de crédito do IMDb"), ("br_filme_ator", "")),
    ("tr_20_ft_desempenho_filme", ("stg + IMDb + RT", "+ 4 dimensões"),
     ("JOINs resolvem SKs; notas IMDb e RT →", "INSERT ... ON CONFLICT DO UPDATE"), ("ft_desempenho_filme", "")),
    ("tr_21_ft_vendas_ingressos", ("stg_cinema_hall", "+ 2 dimensões"),
     ("resolve SKs; recompra como 0/1 →", "INSERT ... ON CONFLICT DO UPDATE"), ("ft_vendas_ingressos", "")),
    ("tr_22_pos_carga", ("ft_desempenho_filme", "+ dim_filme"),
     ("PERCENT_RANK → ROI normalizado;", "ISI de 3 componentes; IND_ATUAL"), ("ft_desempenho_filme", "dim_filme")),
]

AZUL, BRANCO, AMBAR, BORDA, TEXTO, TEXTO2 = "#e8eef9", "#ffffff", "#f2d39b", "#222222", "#111111", "#666666"


def caixa(ax, x, y, w, h, cor, l1, l2, negrito=True):
    ax.add_patch(FancyBboxPatch((x, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=cor, edgecolor=BORDA, linewidth=1.6))
    if l2:
        ax.text(x + w / 2, y + 0.12, l1, ha="center", va="center", fontsize=10.5,
                fontweight="bold" if negrito else "normal", color=TEXTO)
        ax.text(x + w / 2, y - 0.17, l2, ha="center", va="center", fontsize=9.5, color=TEXTO2)
    else:
        ax.text(x + w / 2, y, l1, ha="center", va="center", fontsize=10.5,
                fontweight="bold" if negrito else "normal", color=TEXTO)


def seta(ax, x0, x1, y):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.6))


def main():
    n = len(LINHAS)
    fig, ax = plt.subplots(figsize=(13, 0.95 * n + 0.8))
    ax.set_xlim(0, 13)
    ax.set_ylim(-0.6, n + 0.2)
    ax.axis("off")
    for x, titulo in [(1.3, "Transformação"), (4.0, "Origem"),
                      (7.25, "Execute SQL Script (operação)"), (11.1, "Destino")]:
        ax.text(x, n - 0.05, titulo, ha="center", fontsize=12, fontweight="bold", color=TEXTO2)
    for i, (tr, origem, operacao, destino) in enumerate(LINHAS):
        y = n - 0.85 - i
        ax.text(0.05, y, tr, ha="left", va="center", fontsize=9.6, fontweight="bold", color=TEXTO)
        caixa(ax, 2.95, y, 2.1, 0.62, AZUL, *origem)
        seta(ax, 5.05, 5.55, y)
        ax.add_patch(FancyBboxPatch((5.55, y - 0.36), 3.4, 0.72, boxstyle="round,pad=0,rounding_size=0.08",
                                    facecolor=BRANCO, edgecolor=BORDA, linewidth=1.6))
        ax.text(7.25, y + 0.2, "Execute SQL Script", ha="center", va="center", fontsize=10.5,
                fontweight="bold", color=TEXTO)
        ax.text(7.25, y - 0.03, operacao[0], ha="center", va="center", fontsize=9.3, color=TEXTO2)
        ax.text(7.25, y - 0.22, operacao[1], ha="center", va="center", fontsize=9.3, color=TEXTO2)
        seta(ax, 8.95, 10.05, y)
        caixa(ax, 10.05, y, 2.1, 0.62, AMBAR, *destino)
    saida = Path(__file__).resolve().parent / "claro" / "fig_transformacoes_sql.png"
    saida.parent.mkdir(exist_ok=True)
    fig.savefig(saida, dpi=200, bbox_inches="tight", facecolor="white")
    print(saida)


if __name__ == "__main__":
    main()
