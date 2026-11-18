"""Desenha o modelo dimensional do DW_FILMES (constelacao de fatos).

As tabelas e colunas sao lidas do catalogo do PostgreSQL (information_schema),
de modo que a figura reflete exatamente o schema implantado pelo DDL.

Uso: python graficos/figura_modelo.py
Saida: graficos/claro/fig_modelo_dimensional.png
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import psycopg  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

plt.rcParams["text.parse_math"] = False
plt.rcParams["font.family"] = "Segoe UI"

FATO, DIM, PONTE = "#f2d39b", "#dce6f7", "#e4e2dc"
CONFORMADA = "#c8dcc4"
BORDA, TEXTO, TEXTO2 = "#222222", "#111111", "#5c5b57"
LINHA, CAB = 0.30, 0.46

# tabela: (coluna x, topo y, largura, cor do cabecalho)
LAYOUT = {
    "dim_diretor": (0.0, 10.6, 3.5, DIM),
    "dim_produtora": (0.0, 8.0, 3.5, DIM),
    "dim_tempo": (0.0, 6.4, 3.5, DIM),
    "ft_desempenho_filme": (4.5, 10.6, 4.3, FATO),
    "dim_filme": (9.6, 10.6, 3.8, DIM),
    "br_filme_ator": (9.6, 5.9, 3.8, PONTE),
    "br_filme_genero": (9.6, 3.6, 3.8, PONTE),
    "dim_ator": (14.4, 10.6, 3.5, DIM),
    "dim_genero": (14.4, 7.4, 3.5, CONFORMADA),
    "ft_vendas_ingressos": (14.4, 5.6, 3.5, FATO),
    "dim_cliente": (14.4, 2.1, 3.5, DIM),
}
PK = {
    "dim_diretor": {"sk_diretor"}, "dim_produtora": {"sk_produtora"}, "dim_tempo": {"sk_tempo"},
    "dim_filme": {"sk_filme"}, "dim_ator": {"sk_ator"}, "dim_genero": {"sk_genero"},
    "dim_cliente": {"sk_cliente"}, "ft_vendas_ingressos": {"nr_ingresso"},
    "ft_desempenho_filme": {"sk_filme", "sk_diretor", "sk_produtora", "sk_tempo_lancamento"},
    "br_filme_ator": {"sk_filme", "sk_ator"}, "br_filme_genero": {"sk_filme", "sk_genero"},
}
# (tabela origem, coluna FK, tabela destino, coluna PK, lado de saida, lado de chegada)
LIGACOES = [
    ("ft_desempenho_filme", "sk_diretor", "dim_diretor", "sk_diretor", "e", "d"),
    ("ft_desempenho_filme", "sk_produtora", "dim_produtora", "sk_produtora", "e", "d"),
    ("ft_desempenho_filme", "sk_tempo_lancamento", "dim_tempo", "sk_tempo", "e", "d"),
    ("ft_desempenho_filme", "sk_filme", "dim_filme", "sk_filme", "d", "e"),
    ("br_filme_ator", "sk_filme", "dim_filme", "sk_filme", "e", "e"),
    ("br_filme_genero", "sk_filme", "dim_filme", "sk_filme", "e", "e"),
    ("br_filme_ator", "sk_ator", "dim_ator", "sk_ator", "d", "e"),
    ("br_filme_genero", "sk_genero", "dim_genero", "sk_genero", "d", "e"),
    ("ft_vendas_ingressos", "sk_genero", "dim_genero", "sk_genero", "d", "d"),
    ("ft_vendas_ingressos", "sk_cliente", "dim_cliente", "sk_cliente", "d", "d"),
]


def ler_colunas():
    con = psycopg.connect(host=os.getenv("DW_HOST", "localhost"), port=os.getenv("DW_PORT", "55432"),
                          dbname=os.getenv("DW_DB", "dw_filmes"), user=os.getenv("DW_USER", "dw_filmes"),
                          password=os.getenv("DW_PASSWORD", "dw_filmes"))
    with con, con.cursor() as cur:
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                        WHERE table_schema = 'sch_dw_filmes' ORDER BY table_name, ordinal_position""")
        cols = {}
        for t, c in cur.fetchall():
            cols.setdefault(t, []).append(c)
    return cols


def main():
    cols = ler_colunas()
    fig, ax = plt.subplots(figsize=(15, 9.4))
    ax.set_xlim(-0.2, 18.1)
    ax.set_ylim(-0.4, 11.0)
    ax.axis("off")
    pos = {}  # (tabela, coluna) -> y do centro da linha
    for t, (x, topo, w, cor) in LAYOUT.items():
        c = cols[t]
        h = CAB + LINHA * len(c) + 0.08
        ax.add_patch(Rectangle((x, topo - h), w, h, facecolor="white", edgecolor=BORDA, linewidth=1.3, zorder=3))
        ax.add_patch(Rectangle((x, topo - CAB), w, CAB, facecolor=cor, edgecolor=BORDA, linewidth=1.3, zorder=3))
        ax.text(x + w / 2, topo - CAB / 2, t.upper(), ha="center", va="center", fontsize=10,
                fontweight="bold", color=TEXTO, zorder=4)
        fks = {l[1] for l in LIGACOES if l[0] == t}
        for i, nome in enumerate(c):
            y = topo - CAB - LINHA * (i + 0.5) - 0.04
            pos[(t, nome)] = y
            marca = " / ".join(m for m, ok in (("PK", nome in PK[t]), ("FK", nome in fks)) if ok)
            ax.text(x + 0.12, y, nome, ha="left", va="center", fontsize=8.3, color=TEXTO, zorder=4,
                    fontweight="bold" if nome in PK[t] else "normal")
            if marca:
                ax.text(x + w - 0.1, y, marca, ha="right", va="center", fontsize=7.2, color=TEXTO2, zorder=4)
    for origem, fk, destino, pk, lo, ld in LIGACOES:
        xo, _, wo, _ = LAYOUT[origem]
        xd, _, wd, _ = LAYOUT[destino]
        p0 = (xo if lo == "e" else xo + wo, pos[(origem, fk)])
        p1 = (xd if ld == "e" else xd + wd, pos[(destino, pk)])
        if lo == ld:  # mesma lateral: contorna pelo lado
            braco = 22 if lo == "d" else -22
            estilo = f"arc,angleA={0 if lo == 'd' else 180},angleB={0 if ld == 'd' else 180},armA=22,armB=22,rad=6"
        else:
            estilo = "angle,angleA=0,angleB=90,rad=6" if False else f"arc,angleA={0 if lo == 'd' else 180},angleB={0 if ld == 'd' else 180},armA=16,armB=16,rad=6"
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10, color="#444444",
                                     linewidth=1.1, connectionstyle=estilo, zorder=2))
    y = -0.15
    x = 0.0
    for cor, txt in [(FATO, "tabela fato"), (DIM, "dimensão"), (CONFORMADA, "dimensão compartilhada pelos dois fatos"),
                     (PONTE, "tabela-ponte")]:
        ax.add_patch(Rectangle((x, y - 0.12), 0.35, 0.24, facecolor=cor, edgecolor=BORDA, linewidth=1))
        ax.text(x + 0.48, y, txt, va="center", fontsize=9, color=TEXTO2)
        x += 0.9 + 0.105 * len(txt)
    ax.text(18.0, y, "Setas: chave estrangeira → chave primária referenciada", ha="right", va="center",
            fontsize=9, color=TEXTO2)
    saida = Path(__file__).resolve().parent / "claro" / "fig_modelo_dimensional.png"
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(saida, dpi=200, facecolor="white")
    print(saida)


if __name__ == "__main__":
    main()
