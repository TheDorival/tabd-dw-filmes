"""Gera os graficos das perguntas de negocio a partir das views do DW.

Uso:
    python graficos/gerar_graficos.py

Le as views de sql/04_views_perguntas.sql no PostgreSQL e grava um PNG por
pergunta em dois temas:
    graficos/claro/   fundo branco, para a documentacao (impressao)
    graficos/escuro/  fundo preto e destaque amarelo, para os slides

Conexao (variaveis de ambiente, com os valores do projeto como padrao):
    DW_HOST=localhost DW_PORT=55432 DW_DB=dw_filmes DW_USER=dw_filmes DW_PASSWORD=dw_filmes
"""

import os
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import psycopg  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

PASTA = Path(__file__).resolve().parent
FONTE = "Fonte: Data Warehouse DW_FILMES (TMDB, IMDb, Rotten Tomatoes e Cinema Hall), view {view}."

TEMAS = {
    "claro": {
        "fundo": "#ffffff",
        "texto": "#0b0b0b",
        "texto2": "#52514e",
        "grade": "#e6e4df",
        "destaque": "#c98500",
        "neutro": "#cfccc4",
        "referencia": "#52514e",
        "rampa": ["#fbf3e0", "#f2c96b", "#c98500", "#7a4f00"],
    },
    "escuro": {
        "fundo": "#000000",
        "texto": "#F2EBD7",
        "texto2": "#b5b0a3",
        "grade": "#2a2a28",
        "destaque": "#FFC74B",
        "neutro": "#5f5e5a",
        "referencia": "#b5b0a3",
        "rampa": ["#1c1a14", "#6b5420", "#c99a2e", "#FFC74B"],
    },
}

GENEROS = {
    "Action": "Ação", "Adventure": "Aventura", "Animation": "Animação",
    "Comedy": "Comédia", "Crime": "Crime", "Documentary": "Documentário",
    "Drama": "Drama", "Family": "Família", "Fantasy": "Fantasia",
    "Foreign": "Estrangeiro", "History": "História", "Horror": "Terror",
    "Music": "Música", "Mystery": "Mistério", "Romance": "Romance",
    "Science Fiction": "Ficção científica", "TV Movie": "Filme para TV",
    "Thriller": "Suspense", "War": "Guerra", "Western": "Faroeste",
}
JANELAS = {"Fim de Ano": "Fim de ano", "Verao": "Verão",
           "Premiacoes": "Premiações", "Regular": "Regular"}
ORDEM_JANELAS = ["Premiações", "Verão", "Regular", "Fim de ano"]


def br(valor, casas=1):
    """Numero no formato brasileiro (virgula decimal, ponto de milhar)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def ler_views():
    conexao = psycopg.connect(
        host=os.getenv("DW_HOST", "localhost"),
        port=os.getenv("DW_PORT", "55432"),
        dbname=os.getenv("DW_DB", "dw_filmes"),
        user=os.getenv("DW_USER", "dw_filmes"),
        password=os.getenv("DW_PASSWORD", "dw_filmes"),
    )
    nomes = [
        "vw_p01_dupla_diretor_ator", "vw_p02_variacao_diretor", "vw_p03_genero_janela",
        "vw_p04_trimestre1_fim_de_ano", "vw_p05_prejuizo_genero_janela",
        "vw_p06_produtora_isi_orcamento", "vw_p07_faixa_orcamento",
        "vw_p08_lancamento_anterior", "vw_p09_desvio_isi_genero",
        "vw_p10_discriminacao_variaveis", "vw_p11_sucesso_equilibrado",
        "vw_p12_perfil_espectador", "vw_meta_smart",
    ]
    dados = {}
    with conexao:
        for nome in nomes:
            with conexao.cursor() as cur:
                cur.execute(f"SELECT * FROM sch_dw_filmes.{nome}")
                colunas = [c.name for c in cur.description]
                df = pd.DataFrame(cur.fetchall(), columns=colunas)
            for col in df.columns:
                if df[col].dtype == object:
                    try:
                        df[col] = pd.to_numeric(df[col])
                    except (ValueError, TypeError):
                        pass
            dados[nome] = df
        with conexao.cursor() as cur:
            cur.execute("SELECT round(100.0*avg((roi<0)::int),1) FROM sch_dw_filmes.ft_desempenho_filme")
            dados["prejuizo_geral"] = float(cur.fetchone()[0])
    return dados


def configurar_fonte():
    # "US$ ... US$" nao pode virar formula matematica.
    plt.rcParams["text.parse_math"] = False
    disponiveis = {f.name for f in font_manager.fontManager.ttflist}
    for nome in ("Segoe UI", "Calibri", "Arial", "DejaVu Sans"):
        if nome in disponiveis:
            plt.rcParams["font.family"] = nome
            return


class Grafico:
    """Figura com titulo, subtitulo e rodape de fonte no padrao do projeto."""

    def __init__(self, tema, titulo, subtitulo, view, largura=10, altura=5.6,
                 linhas=1, colunas=1, **kw):
        self.t = TEMAS[tema]
        # Na documentacao (tema claro), titulo e fonte ficam na legenda e no rodape da
        # figura, no padrao ABNT; o grafico leva so a area de plotagem.
        self.cabecalho = tema != "claro"
        if not self.cabecalho:
            altura *= 0.85
        self.fig, eixos = plt.subplots(linhas, colunas, figsize=(largura, altura), **kw)
        self.eixos = np.atleast_1d(eixos).ravel()
        self.fig.patch.set_facecolor(self.t["fundo"])
        if self.cabecalho:
            self.fig.suptitle(titulo, x=0.02, y=0.975, ha="left", fontsize=15,
                              fontweight="bold", color=self.t["texto"])
            self.fig.text(0.02, 0.905, textwrap.fill(subtitulo, int(largura * 13)), ha="left",
                          va="top", fontsize=10.5, color=self.t["texto2"], linespacing=1.4)
            self.fig.text(0.02, 0.015, FONTE.format(view=view), ha="left", va="bottom",
                          fontsize=8.5, color=self.t["texto2"])
        for ax in self.eixos:
            self.estilo(ax)

    def estilo(self, ax, grade="x"):
        t = self.t
        ax.set_facecolor(t["fundo"])
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color(t["grade"])
        ax.tick_params(colors=t["texto2"], labelsize=9.5, length=0)
        ax.xaxis.label.set_color(t["texto2"])
        ax.yaxis.label.set_color(t["texto2"])
        ax.grid(axis=grade, color=t["grade"], linewidth=0.8)
        ax.set_axisbelow(True)

    def salvar(self, caminho, topo=0.84, base=0.13):
        if not self.cabecalho:
            topo, base = 0.95, max(base - 0.03, 0.09)
        self.fig.subplots_adjust(top=topo, bottom=base)
        self.fig.savefig(caminho, dpi=200, facecolor=self.t["fundo"])
        plt.close(self.fig)


def barras_h(ax, t, rotulos, valores, textos, destaque_idx=(0,), limite=None):
    """Barras horizontais, primeira linha no topo, com rotulo de valor."""
    y = np.arange(len(valores))[::-1]
    cores = [t["destaque"] if i in destaque_idx else t["neutro"] for i in range(len(valores))]
    ax.barh(y, valores, color=cores, height=0.68, edgecolor=t["fundo"], linewidth=2)
    ax.set_yticks(y, rotulos)
    ax.tick_params(axis="y", labelcolor=t["texto"])
    maximo = limite or max(valores) * 1.18
    ax.set_xlim(0, maximo)
    for yi, v, txt in zip(y, valores, textos):
        ax.text(v + maximo * 0.01, yi, txt, va="center", fontsize=9, color=t["texto"])


# --------------------------------------------------------------------------
# Um grafico por pergunta
# --------------------------------------------------------------------------

def p01(d, tema, saida):
    df = d["vw_p01_dupla_diretor_ator"].head(10)
    g = Grafico(tema, "P1 · Duplas diretor + ator principal com maior ISI",
                "ISI médio das duplas com pelo menos 3 filmes juntos (10 maiores)",
                "vw_p01_dupla_diretor_ator")
    rot = [f"{r.diretor} + {r.ator_principal}" for r in df.itertuples()]
    txt = [f"{br(r.isi_medio)}  ({r.filmes} filmes)" for r in df.itertuples()]
    barras_h(g.eixos[0], g.t, rot, df.isi_medio.tolist(), txt, limite=100)
    g.eixos[0].set_xlabel("ISI médio (0 a 100)")
    g.fig.subplots_adjust(left=0.33)
    g.salvar(saida / "p01_dupla_diretor_ator.png")


def p02(d, tema, saida):
    df = d["vw_p02_variacao_diretor"]
    mediana = df.amplitude_nota.median()
    top = df.head(12).iloc[::-1]
    g = Grafico(tema, "P2 · Mesma direção, atores principais diferentes",
                f"Menor e maior nota média do público entre os atores principais de cada diretor "
                f"(12 diretores com mais filmes). Amplitude mediana entre os {len(df)} diretores: "
                f"{br(mediana)} pontos",
                "vw_p02_variacao_diretor", altura=6)
    ax, t = g.eixos[0], g.t
    y = np.arange(len(top))
    ax.hlines(y, top.nota_min, top.nota_max, color=t["neutro"], linewidth=3)
    ax.scatter(top.nota_min, y, s=60, color=t["neutro"], zorder=3, edgecolor=t["fundo"], linewidth=2)
    ax.scatter(top.nota_max, y, s=60, color=t["destaque"], zorder=3, edgecolor=t["fundo"], linewidth=2)
    ax.set_yticks(y, [f"{r.diretor} ({r.atores_principais} atores)" for r in top.itertuples()])
    ax.tick_params(axis="y", labelcolor=t["texto"])
    for yi, r in zip(y, top.itertuples()):
        ax.text(r.nota_max + 0.8, yi, f"{br(r.amplitude_nota)} pts", va="center",
                fontsize=9, color=t["texto"])
    ax.set_xlim(35, 90)
    ax.set_xlabel("Nota média do público (0 a 100) — cinza: menor · destaque: maior")
    g.fig.subplots_adjust(left=0.27)
    g.salvar(saida / "p02_variacao_diretor.png", topo=0.81)


def heatmap(ax, t, matriz, rotulo_fmt, cmap, destaque_mask):
    ax.grid(False)
    ax.imshow(matriz.values.astype(float), cmap=cmap, aspect="auto")
    ax.set_xticks(range(matriz.shape[1]), matriz.columns)
    ax.set_yticks(range(matriz.shape[0]), matriz.index)
    ax.tick_params(colors=t["texto"], labelsize=9, length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    vals = matriz.values.astype(float)
    lim = np.nanmin(vals) + (np.nanmax(vals) - np.nanmin(vals)) * 0.55
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                ax.text(j, i, "–", ha="center", va="center", fontsize=8.5, color=t["texto2"])
                continue
            escuro = (v > lim) if t["fundo"] == "#ffffff" else (v < lim)
            cor = "#ffffff" if escuro else "#0b0b0b"
            melhor = bool(destaque_mask.iloc[i, j])
            ax.text(j, i, rotulo_fmt(v), ha="center", va="center", fontsize=8.5, color=cor,
                    fontweight="bold" if melhor else "normal")
            if melhor:
                ax.add_patch(Rectangle((j - 0.47, i - 0.44), 0.94, 0.88, fill=False,
                                       edgecolor=t["texto"], linewidth=1.6))


def p03(d, tema, saida):
    df = d["vw_p03_genero_janela"].copy()
    df["genero"] = df.genero_principal.map(GENEROS).fillna(df.genero_principal)
    df["janela"] = df.janela_mercado.map(JANELAS)
    ordem_gen = df.groupby("genero").filmes.sum().sort_values(ascending=False).index
    piv = lambda col: df.pivot(index="genero", columns="janela", values=col).reindex(  # noqa: E731
        index=ordem_gen, columns=ORDEM_JANELAS)
    g = Grafico(tema, "P3 · Receita, nota do público e nota da crítica por gênero e janela",
                "Gênero principal × janela (mínimo de 10 filmes). Moldura = melhor janela do gênero. "
                "Receita mediana em US$ milhões de 2010; público: IMDb; crítica: Rotten Tomatoes",
                "vw_p03_genero_janela", largura=15, altura=7.2, colunas=3)
    t = g.t
    cmap = LinearSegmentedColormap.from_list("seq", t["rampa"])
    paineis = [("receita_mediana_mi", "pos_receita", "Receita mediana (US$ mi)", lambda v: br(v, 0)),
               ("nota_media", "pos_nota", "Nota média do público", lambda v: br(v)),
               ("critica_media", "pos_critica", "Nota média da crítica", lambda v: br(v))]
    for i, (col, pos, nome, fmt) in enumerate(paineis):
        heatmap(g.eixos[i], t, piv(col), fmt, cmap, piv(pos) == 1)
        g.eixos[i].set_title(nome, color=t["texto"], fontsize=11, loc="left")
        if i:
            g.eixos[i].set_yticklabels([])
    g.fig.subplots_adjust(left=0.1, right=0.99, wspace=0.05)
    g.salvar(saida / "p03_genero_janela.png", topo=0.83)


def p04(d, tema, saida):
    df = d["vw_p04_trimestre1_fim_de_ano"].set_index("periodo")
    metricas = [("receita_mediana_mi", "Receita mediana\n(US$ mi)", 1),
                ("roi_mediano_pct", "ROI mediano\n(%)", 0),
                ("nota_media", "Nota média\ndo público", 1),
                ("isi_medio", "ISI\nmédio", 1),
                ("taxa_prejuizo_pct", "Taxa de\nprejuízo (%)", 1)]
    q1 = df.index[df.index.str.startswith("1o")][0]
    fa = df.index[~df.index.str.startswith("1o")][0]
    g = Grafico(tema, "P4 · 1º trimestre × janela de fim de ano",
                f"Lançamentos de janeiro a março ({df.loc[q1, 'filmes']} filmes) e de 15/11 a 31/12 "
                f"({df.loc[fa, 'filmes']} filmes). Destaque: fim de ano",
                "vw_p04_trimestre1_fim_de_ano", largura=11, altura=5, colunas=5)
    t = g.t
    for ax, (col, nome, casas) in zip(g.eixos, metricas):
        vals = [df.loc[q1, col], df.loc[fa, col]]
        ax.bar([0, 1], vals, color=[t["neutro"], t["destaque"]], width=0.7,
               edgecolor=t["fundo"], linewidth=2)
        ax.set_xticks([0, 1], ["1º trim.", "Fim de ano"])
        ax.tick_params(axis="x", labelcolor=t["texto"], labelsize=9)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.grid(False)
        ax.set_ylim(0, max(vals) * 1.25)
        ax.set_title(nome, color=t["texto"], fontsize=10)
        for x, v in zip([0, 1], vals):
            ax.text(x, v + max(vals) * 0.03, br(v, casas), ha="center", fontsize=10,
                    color=t["texto"], fontweight="bold")
    g.fig.subplots_adjust(wspace=0.35, left=0.03, right=0.98)
    g.salvar(saida / "p04_trimestre1_fim_de_ano.png", topo=0.72, base=0.12)


def p05(d, tema, saida):
    df = d["vw_p05_prejuizo_genero_janela"].head(10)
    geral = d["prejuizo_geral"]
    g = Grafico(tema, "P5 · Combinações de gênero e janela com menor risco de prejuízo",
                f"Taxa de prejuízo (ROI < 0) por gênero principal × janela, mínimo de 15 filmes. "
                f"Linha: taxa de todos os filmes ({br(geral)}%)",
                "vw_p05_prejuizo_genero_janela")
    ax, t = g.eixos[0], g.t
    rot = [f"{GENEROS.get(r.genero_principal, r.genero_principal)} · {JANELAS[r.janela_mercado]}"
           for r in df.itertuples()]
    txt = [f"{br(r.taxa_prejuizo_pct)}%  ({r.filmes} filmes)" for r in df.itertuples()]
    barras_h(ax, t, rot, df.taxa_prejuizo_pct.tolist(), txt, destaque_idx=range(3), limite=40)
    ax.axvline(geral, color=t["referencia"], linestyle="--", linewidth=1.2)
    ax.text(geral + 0.4, len(df) - 0.4, "média geral", color=t["texto2"], fontsize=8.5)
    ax.set_xlabel("Taxa de prejuízo (%)")
    g.fig.subplots_adjust(left=0.27)
    g.salvar(saida / "p05_prejuizo_genero_janela.png")


def p06(d, tema, saida):
    df = d["vw_p06_produtora_isi_orcamento"].head(10)
    g = Grafico(tema, "P6 · Produtoras com maior ISI em relação ao orçamento",
                "ISI médio por US$ 10 milhões de orçamento médio (US$ de 2010). "
                "Produtora principal, mínimo de 10 filmes",
                "vw_p06_produtora_isi_orcamento")
    txt = [f"{br(r.isi_por_10mi, 1)}   (ISI {br(r.isi_medio)} · US$ {br(r.orcamento_medio_mi)} mi · "
           f"{r.filmes} filmes)" for r in df.itertuples()]
    barras_h(g.eixos[0], g.t, df.produtora.tolist(), df.isi_por_10mi.tolist(), txt,
             limite=df.isi_por_10mi.max() * 1.75)
    g.eixos[0].set_xlabel("ISI médio por US$ 10 mi de orçamento médio")
    g.fig.subplots_adjust(left=0.22)
    g.salvar(saida / "p06_produtora_isi_orcamento.png")


def p07(d, tema, saida):
    df = d["vw_p07_faixa_orcamento"]
    rot = [f"{br(r.orcamento_min_mi)}–{br(r.orcamento_max_mi)}" for r in df.itertuples()]
    g = Grafico(tema, "P7 · ROI mediano por faixa de orçamento",
                "Dez faixas com o mesmo número de filmes (US$ milhões de 2010). O ROI mediano cai "
                "até a faixa de US$ 52–71 mi e só volta a subir nos maiores orçamentos",
                "vw_p07_faixa_orcamento", largura=11, altura=7, linhas=2, sharex=True,
                gridspec_kw={"height_ratios": [3, 2]})
    t = g.t
    x = np.arange(len(df))
    ax1, ax2 = g.eixos
    ax1.grid(axis="y", color=t["grade"])
    ax1.grid(axis="x", visible=False)
    ax1.plot(x, df.roi_mediano_pct, color=t["destaque"], linewidth=2, marker="o", markersize=8,
             markeredgecolor=t["fundo"], markeredgewidth=2)
    menor = int(df.roi_mediano_pct.idxmin())
    for xi, v in zip(x, df.roi_mediano_pct):
        ax1.text(xi, v + 14, f"{br(v, 0)}%", ha="center", fontsize=9, color=t["texto"],
                 fontweight="bold" if xi in (0, menor, len(df) - 1) else "normal")
    ax1.set_ylabel("ROI mediano (%)")
    ax1.set_ylim(0, df.roi_mediano_pct.max() * 1.2)
    ax2.grid(axis="y", color=t["grade"])
    ax2.grid(axis="x", visible=False)
    ax2.bar(x, df.taxa_prejuizo_pct, color=t["neutro"], width=0.7, edgecolor=t["fundo"], linewidth=2)
    for xi, v in zip(x, df.taxa_prejuizo_pct):
        ax2.text(xi, v + 1, f"{br(v)}%", ha="center", fontsize=8.5, color=t["texto"])
    ax2.set_ylabel("Taxa de prejuízo (%)")
    ax2.set_ylim(0, df.taxa_prejuizo_pct.max() * 1.3)
    ax2.set_xticks(x, rot)
    ax2.tick_params(axis="x", labelcolor=t["texto"], labelsize=8.5)
    ax2.set_xlabel("Faixa de orçamento (US$ milhões de 2010)")
    if g.cabecalho:
        g.fig.text(0.98, 0.015, "A 1ª faixa inclui os 21 orçamentos implausíveis (< US$ 1.000) da fonte.",
                   ha="right", va="bottom", fontsize=8.5, color=t["texto2"])
    g.fig.subplots_adjust(hspace=0.12, left=0.08, right=0.98)
    g.salvar(saida / "p07_faixa_orcamento.png", topo=0.84, base=0.12)


def p08(d, tema, saida):
    df = d["vw_p08_lancamento_anterior"]
    com = df[df.grupo.str.startswith("Com")].iloc[0]
    sem = df[df.grupo.str.startswith("Sem")].iloc[0]
    dif = com.nota_media - sem.nota_media
    g = Grafico(tema, "P8 · Ator principal com lançamento recente",
                f"Nota média do público quando o ator principal teve outro filme nos 12 meses "
                f"anteriores. Diferença: {br(dif, 2)} ponto — praticamente nula",
                "vw_p08_lancamento_anterior", largura=9, altura=5)
    ax, t = g.eixos[0], g.t
    rot = [f"Com lançamento anterior\n({com.filmes} filmes)", f"Sem lançamento anterior\n({sem.filmes} filmes)"]
    vals = [com.nota_media, sem.nota_media]
    ax.bar([0, 1], vals, color=[t["destaque"], t["neutro"]], width=0.55, edgecolor=t["fundo"], linewidth=2)
    ax.set_xticks([0, 1], rot)
    ax.tick_params(axis="x", labelcolor=t["texto"], labelsize=10)
    ax.grid(axis="y", color=t["grade"])
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Nota média do público (0 a 100)")
    for x, v, dp in zip([0, 1], vals, [com.desvio_nota, sem.desvio_nota]):
        ax.text(x, v + 2, f"{br(v, 2)}\n(desvio {br(dp, 1)})", ha="center", fontsize=10,
                color=t["texto"], fontweight="bold")
    g.salvar(saida / "p08_lancamento_anterior.png", topo=0.76)


def p09(d, tema, saida):
    df = d["vw_p09_desvio_isi_genero"]
    g = Grafico(tema, "P9 · Gêneros com resultado mais previsível",
                "Desvio-padrão do ISI por gênero (cada filme conta em todos os seus gêneros; "
                "mínimo de 50 filmes). Quanto menor, mais consistente",
                "vw_p09_desvio_isi_genero", altura=6.4)
    rot = [GENEROS.get(x, x) for x in df.genero]
    txt = [f"{br(r.desvio_padrao_isi, 2)}   (ISI médio {br(r.isi_medio)} · {r.filmes} filmes)"
           for r in df.itertuples()]
    barras_h(g.eixos[0], g.t, rot, df.desvio_padrao_isi.tolist(), txt, destaque_idx=range(3), limite=30)
    g.eixos[0].set_xlabel("Desvio-padrão do ISI")
    g.fig.subplots_adjust(left=0.17)
    g.salvar(saida / "p09_desvio_isi_genero.png")


def p10(d, tema, saida):
    df = d["vw_p10_discriminacao_variaveis"]
    nomes = {"Produtora (principal)": "Produtora", "Diretor": "Diretor",
             "Elenco (ator principal)": "Elenco (ator principal)",
             "Janela de lancamento": "Janela de lançamento", "Genero (principal)": "Gênero"}
    g = Grafico(tema, "P10 · Qual variável mais discrimina o sucesso?",
                "Parcela da variação do ISI explicada por cada variável (ε², corrigido pelo número de "
                "categorias; categorias com menos de 5 filmes agrupadas)",
                "vw_p10_discriminacao_variaveis", altura=4.8)
    rot = [nomes.get(v, v) for v in df.variavel]
    txt = [f"{br(100 * r.epsilon2, 1)}%   ({r.categorias_com_5_ou_mais_filmes} categorias)"
           for r in df.itertuples()]
    barras_h(g.eixos[0], g.t, rot, (100 * df.epsilon2).tolist(), txt, limite=10)
    g.eixos[0].set_xlabel("Variação do ISI explicada (%)")
    g.fig.subplots_adjust(left=0.22)
    g.salvar(saida / "p10_discriminacao_variaveis.png", topo=0.8, base=0.13)


def p11(d, tema, saida):
    df = d["vw_p11_sucesso_equilibrado"].head(10)
    g = Grafico(tema, "P11 · Combinações com ROI alto e aprovação de pelo menos 70",
                "Parcela dos filmes com ROI acima da mediana geral e notas da crítica e do público ≥ 70, "
                "por gênero principal × janela (mínimo de 15 filmes com nota da crítica)",
                "vw_p11_sucesso_equilibrado")
    rot = [f"{GENEROS.get(r.genero_principal, r.genero_principal)} · {JANELAS[r.janela_mercado]}"
           for r in df.itertuples()]
    txt = [f"{br(r.taxa_equilibrio_pct)}%  ({r.filmes_equilibrados} de {r.filmes} filmes)" for r in df.itertuples()]
    barras_h(g.eixos[0], g.t, rot, df.taxa_equilibrio_pct.tolist(), txt, limite=80)
    g.eixos[0].set_xlabel("Filmes com sucesso equilibrado (%)")
    g.fig.subplots_adjust(left=0.27)
    g.salvar(saida / "p11_sucesso_equilibrado.png")


def p12(d, tema, saida):
    df = d["vw_p12_perfil_espectador"].copy()
    df["genero"] = df.genero.map(GENEROS).fillna(df.genero)
    piv = lambda col: df.pivot(index="genero", columns="faixa_etaria", values=col)  # noqa: E731
    g = Grafico(tema, "P12 · Perfil do espectador por gênero",
                "Base de vendas (1.440 ingressos, sem filme nem data): participação de cada faixa etária "
                "nos ingressos do gênero e taxa de intenção de recompra. Moldura = maior valor do gênero",
                "vw_p12_perfil_espectador", largura=12, altura=5.4, colunas=2)
    t = g.t
    cmap = LinearSegmentedColormap.from_list("seq", t["rampa"])
    for i, (col, nome) in enumerate([("pct_ingressos_do_genero", "Participação nos ingressos do gênero (%)"),
                                     ("taxa_recompra_pct", "Intenção de recompra (%)")]):
        m = piv(col)
        heatmap(g.eixos[i], t, m, lambda v: br(v), cmap, m.eq(m.max(axis=1), axis=0))
        g.eixos[i].set_title(nome, color=t["texto"], fontsize=11, loc="left")
        g.eixos[i].set_xlabel("Faixa etária", color=t["texto2"])
        if i:
            g.eixos[i].set_yticklabels([])
    g.fig.subplots_adjust(left=0.12, right=0.99, wspace=0.05)
    g.salvar(saida / "p12_perfil_espectador.png", topo=0.74, base=0.15)


def meta_smart(d, tema, saida):
    df = d["vw_meta_smart"].sort_values("ordem").reset_index(drop=True)
    base = df.iloc[0]
    g = Grafico(tema, "Meta SMART · Prejuízo e nota do público com e sem a recomendação",
                f"Lançamentos de 2011 a 2015; recomendações de gênero × janela geradas só com 1960–2010. "
                f"Metas: prejuízo de no máximo {br(base.meta_taxa_prejuizo_pct)}% e nota média "
                f"de no mínimo {br(base.meta_nota_minima, 2)}",
                "vw_meta_smart", largura=9, altura=5.2)
    ax, t = g.eixos[0], g.t
    xs = list(range(len(df)))
    cores = [t["neutro"], t["rampa"][1], t["destaque"]]
    nomes = ["Todos os lançamentos", "Regra inicial\n(só prejuízo)", "Regra final\n(prejuízo e nota)"]
    ax.bar(xs, df.taxa_prejuizo_pct, color=cores[:len(df)], width=0.55,
           edgecolor=t["fundo"], linewidth=2)
    ax.axhline(base.meta_taxa_prejuizo_pct, color=t["referencia"], linestyle="--", linewidth=1.2)
    ax.text(0.5, base.meta_taxa_prejuizo_pct + 0.5,
            f"meta: {br(base.meta_taxa_prejuizo_pct)}%", ha="center", va="bottom",
            fontsize=9, color=t["texto2"])
    rotulos = []
    for x, r in df.iterrows():
        rotulos.append(f"{nomes[x]}\n{r.filmes} filmes, {r.combinacoes} comb.")
        if x == 0:
            sit = "linha de base"
        else:
            ok_n = r.nota_media >= base.meta_nota_minima
            ok_t = r.taxa_prejuizo_pct <= base.meta_taxa_prejuizo_pct
            sit = "cumpre a meta" if (ok_n and ok_t) else ("nota abaixo do mínimo" if not ok_n else "prejuízo acima da meta")
        dif = "" if x == 0 else f" ({'+' if r.diferenca_nota >= 0 else '−'}{br(abs(r.diferenca_nota), 2)})"
        ax.text(x, r.taxa_prejuizo_pct + 0.8,
                f"{br(r.taxa_prejuizo_pct)}%\nnota {br(r.nota_media, 2)}{dif}\n{sit}",
                ha="center", va="bottom", fontsize=9.5, color=t["texto"], zorder=5,
                bbox=dict(facecolor=t["fundo"], edgecolor="none", pad=2),
                fontweight="bold" if x == len(df) - 1 else "normal")
    ax.set_xticks(xs, rotulos)
    ax.tick_params(axis="x", labelcolor=t["texto"], labelsize=9.5)
    ax.grid(axis="y", color=t["grade"])
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 40)
    ax.set_ylabel("Taxa de prejuízo (%)")
    g.salvar(saida / "meta_smart.png", topo=0.79, base=0.17)


def main():
    configurar_fonte()
    dados = ler_views()
    funcoes = [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, meta_smart]
    for tema in TEMAS:
        saida = PASTA / tema
        saida.mkdir(exist_ok=True)
        for f in funcoes:
            f(dados, tema, saida)
        print(f"{len(funcoes)} gráficos em {saida}")


if __name__ == "__main__":
    main()
