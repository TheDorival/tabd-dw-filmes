"""Analise exploratoria dos dados do DW_FILMES (secao 5.3 da documentacao).

Uso:
    python eda/analise_exploratoria.py

Le o arquivo de origem (data/tmdb-movies.csv), para a completude, e o Data
Warehouse carregado (PostgreSQL), para as demais analises. Grava:
    eda/figuras/eda_01 ... eda_06.png   figuras da secao 5.3
    eda/resumo_eda.md                   tabelas e numeros citados no texto

Conexao: variaveis DW_HOST, DW_PORT, DW_DB, DW_USER, DW_PASSWORD (padrao: projeto).
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

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "eda" / "figuras"
RESUMO = RAIZ / "eda" / "resumo_eda.md"

TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e6e4df"
DESTAQUE, NEUTRO, ALERTA = "#c98500", "#bdbab2", "#2a78d6"
plt.rcParams.update({"text.parse_math": False, "font.size": 10, "axes.edgecolor": GRADE,
                     "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
                     "axes.spines.top": False, "axes.spines.right": False})
for fonte in ("Segoe UI", "Calibri", "Arial", "DejaVu Sans"):
    if fonte in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = fonte
        break

GENEROS = {
    "Action": "Ação", "Adventure": "Aventura", "Animation": "Animação", "Comedy": "Comédia",
    "Crime": "Crime", "Documentary": "Documentário", "Drama": "Drama", "Family": "Família",
    "Fantasy": "Fantasia", "Foreign": "Estrangeiro", "History": "História", "Horror": "Terror",
    "Music": "Música", "Mystery": "Mistério", "Romance": "Romance", "Science Fiction": "Ficção científica",
    "TV Movie": "Filme para TV", "Thriller": "Suspense", "War": "Guerra", "Western": "Faroeste",
}
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def br(v, casas=1):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def consulta(sql):
    with psycopg.connect(host=os.getenv("DW_HOST", "localhost"), port=os.getenv("DW_PORT", "55432"),
                         dbname=os.getenv("DW_DB", "dw_filmes"), user=os.getenv("DW_USER", "dw_filmes"),
                         password=os.getenv("DW_PASSWORD", "dw_filmes")) as c, c.cursor() as cur:
        cur.execute(sql)
        df = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
    return df


def salvar(fig, nome):
    fig.savefig(SAIDA / nome, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def tabela_md(df, casas=1):
    linhas = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        cel = [br(v, casas) if isinstance(v, (float, np.floating)) else
               (br(v, 0) if isinstance(v, (int, np.integer)) else str(v)) for v in r]
        linhas.append("| " + " | ".join(cel) + " |")
    return "\n".join(linhas)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    md = ["# Resumo da análise exploratória", "",
          "Gerado por `eda/analise_exploratoria.py` a partir de `data/tmdb-movies.csv` e do DW carregado.", ""]

    # ---------------------------------------------------------------- 1. completude da fonte
    fonte = pd.read_csv(RAIZ / "data" / "tmdb-movies.csv")
    n = len(fonte)
    completude = []
    for col in ["revenue_adj", "budget_adj", "production_companies", "cast", "director", "runtime",
                "genres", "imdb_id"]:
        ausentes = int(fonte[col].isna().sum())
        zerados = int((fonte[col] == 0).sum()) if pd.api.types.is_numeric_dtype(fonte[col]) else 0
        completude.append({"coluna": col, "ausentes": ausentes, "zerados": zerados,
                           "% das linhas": 100 * (ausentes + zerados) / n})
    md += [f"## 1. Completude de tmdb-movies.csv ({br(n, 0)} linhas)", "", tabela_md(pd.DataFrame(completude)), ""]

    # ---------------------------------------------------------------- base do DW
    f = consulta("""
        select f.sk_filme, f.orcamento, f.receita_bilheteria as receita, f.roi, f.roi_normalizado,
               f.nota_publico, f.nota_critica, f.nota_publico_tmdb, f.votos_publico, f.votos_critica,
               f.indice_sucesso_integrado as isi, f.ind_isi_completo, f.origem_financeiro,
               df.duracao_minutos as duracao, t.mes, t.janela_mercado, df.titulo
          from sch_dw_filmes.ft_desempenho_filme f
          join sch_dw_filmes.dim_filme df on df.sk_filme = f.sk_filme
          join sch_dw_filmes.dim_tempo t on t.sk_tempo = f.sk_tempo_lancamento""")
    nf = len(f)

    # ---------------------------------------------------------------- 2. cobertura das fontes
    cobertura = pd.DataFrame([
        {"fonte": "TMDB Movies (orçamento e receita)", "filmes": int((f.origem_financeiro == "TMDB").sum())},
        {"fonte": "TMDB 5000 (orçamento e receita recuperados)", "filmes": int((f.origem_financeiro == "TMDB 5000").sum())},
        {"fonte": "IMDb (nota do público)", "filmes": int(consulta(
            "select count(*) n from sch_dw_filmes.stg_imdb_notas").n[0])},
        {"fonte": "Rotten Tomatoes (nota da crítica)", "filmes": int(f.nota_critica.notna().sum())},
    ])
    cobertura["% dos filmes do DW"] = 100 * cobertura.filmes / nf
    md += [f"## 2. Cobertura das fontes no DW ({br(nf, 0)} filmes)", "", tabela_md(cobertura), ""]

    # ---------------------------------------------------------------- 3. estatisticas descritivas
    medidas = {"Orçamento (US$ mi de 2010)": f.orcamento / 1e6, "Receita (US$ mi de 2010)": f.receita / 1e6,
               "ROI (%)": 100 * f.roi, "Nota do público - IMDb (0–100)": f.nota_publico,
               "Nota da crítica - RT (0–100)": f.nota_critica, "ISI (0–100)": f.isi}
    desc = pd.DataFrame([{"medida": k, "média": v.mean(), "desvio-padrão": v.std(), "1º quartil": v.quantile(.25),
                          "mediana": v.median(), "3º quartil": v.quantile(.75), "máximo": v.max(),
                          "n": int(v.notna().sum())} for k, v in medidas.items()])
    md += ["## 3. Estatísticas descritivas", "", tabela_md(desc), "",
           f"- Taxa de prejuízo (ROI < 0): {br(100 * (f.roi < 0).mean())}%",
           f"- Média do ROI / mediana do ROI: {br(f.roi.mean() / f.roi.median(), 0)} vezes", ""]

    fig, ax = plt.subplots(1, 4, figsize=(15, 3.6))
    roi_pct = (100 * f.roi).clip(-100, 1500)
    for a, (dados, titulo, cor) in zip(ax, [
            (roi_pct, "ROI (%) — cortado em 1.500%", NEUTRO), (f.nota_publico, "Nota do público (IMDb)", DESTAQUE),
            (f.nota_critica.dropna(), "Nota da crítica (Rotten Tomatoes)", ALERTA), (f.isi, "ISI", TINTA2)]):
        a.hist(dados, bins=40, color=cor, edgecolor="white", linewidth=0.6)
        a.set_title(titulo, loc="left", color=TINTA, fontsize=10.5)
        a.grid(axis="y", color=GRADE)
        a.set_axisbelow(True)
    ax[0].set_ylabel("Filmes")
    salvar(fig, "eda_01_distribuicoes.png")

    # ---------------------------------------------------------------- 4. ISI por genero
    gen = consulta("""
        select g.nome_genero as genero, count(*) as filmes, avg(f.indice_sucesso_integrado) as isi
          from sch_dw_filmes.ft_desempenho_filme f
          join sch_dw_filmes.br_filme_genero b on b.sk_filme = f.sk_filme
          join sch_dw_filmes.dim_genero g on g.sk_genero = b.sk_genero
         group by 1 order by 3 desc""")
    gen["genero"] = gen.genero.map(GENEROS).fillna(gen.genero)
    md += ["## 4. ISI médio por gênero (cada filme em todos os seus gêneros)", "", tabela_md(gen), ""]
    g50 = gen[gen.filmes >= 50].sort_values("isi")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(g50.genero, g50.isi, color=[DESTAQUE if i >= len(g50) - 3 else NEUTRO for i in range(len(g50))],
            edgecolor="white")
    for y, (v, nfil) in enumerate(zip(g50.isi, g50.filmes)):
        ax.text(v + 0.3, y, f"{br(v)}  ({nfil} filmes)", va="center", fontsize=9, color=TINTA)
    ax.set_xlim(0, g50.isi.max() * 1.25)
    ax.set_xlabel("ISI médio")
    ax.grid(axis="x", color=GRADE)
    ax.set_axisbelow(True)
    salvar(fig, "eda_02_isi_genero.png")

    # ---------------------------------------------------------------- 5. sazonalidade
    jan = f.groupby("janela_mercado").agg(filmes=("roi", "size"), roi_mediano=("roi", lambda s: 100 * s.median()),
                                          nota_publico=("nota_publico", "mean"), nota_critica=("nota_critica", "mean"),
                                          isi=("isi", "mean"),
                                          prejuizo=("roi", lambda s: 100 * (s < 0).mean())).reset_index()
    md += ["## 5. Desempenho por janela de mercado", "", tabela_md(jan), ""]
    mes = f.groupby("mes").agg(roi_mediano=("roi", lambda s: 100 * s.median()), isi=("isi", "mean")).reindex(range(1, 13))
    fig, ax = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    ax[0].bar(range(12), mes.roi_mediano, color=NEUTRO, edgecolor="white")
    ax[0].set_ylabel("ROI mediano (%)")
    ax[1].plot(range(12), mes.isi, color=DESTAQUE, marker="o", linewidth=2)
    ax[1].set_ylabel("ISI médio")
    ax[1].set_xticks(range(12), MESES)
    for a in ax:
        a.grid(axis="y", color=GRADE)
        a.set_axisbelow(True)
    for x, v in enumerate(mes.roi_mediano):
        ax[0].text(x, v + 3, br(v, 0), ha="center", fontsize=8.5, color=TINTA)
    salvar(fig, "eda_03_sazonalidade.png")
    md += [f"- Mês com maior ROI mediano: {MESES[int(mes.roi_mediano.idxmax()) - 1]} ({br(mes.roi_mediano.max(), 0)}%); "
           f"menor: {MESES[int(mes.roi_mediano.idxmin()) - 1]} ({br(mes.roi_mediano.min(), 0)}%)", ""]

    # ---------------------------------------------------------------- 6. correlacoes
    cols = {"orcamento": "Orçamento", "receita": "Receita", "roi": "ROI", "nota_publico": "Nota público (IMDb)",
            "nota_publico_tmdb": "Nota público (TMDB)", "nota_critica": "Nota crítica (RT)",
            "votos_publico": "Votos público", "votos_critica": "Votos crítica", "duracao": "Duração"}
    corr = f[list(cols)].rename(columns=cols).corr(method="spearman")
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, br(corr.values[i, j], 2), ha="center", va="center", fontsize=8.5,
                    color="white" if abs(corr.values[i, j]) > 0.6 else TINTA)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.75, label="Correlação de Spearman")
    salvar(fig, "eda_04_correlacoes.png")
    md += ["## 6. Correlação de Spearman", "", tabela_md(corr.reset_index().rename(columns={"index": ""}), 2), ""]

    # ---------------------------------------------------------------- 7. outliers
    q1, q3 = f.roi.quantile([.25, .75])
    limite = q3 + 1.5 * (q3 - q1)
    out = f[f.roi > limite]
    implaus_orc = f[f.orcamento < 1000]
    implaus_qq = f[(f.orcamento < 1000) | (f.receita < 1000)]
    md += ["## 7. Outliers de ROI (critério do intervalo interquartil)", "",
           f"- Limite superior: ROI acima de {br(100 * limite, 0)}%",
           f"- Outliers: {len(out)} filmes ({br(100 * len(out) / nf)}%)",
           f"- Filmes com orçamento < US$ 1.000: {len(implaus_orc)}; com orçamento ou receita < US$ 1.000: {len(implaus_qq)}", ""]
    fig, ax = plt.subplots(figsize=(8.5, 6))
    normais = f[f.orcamento >= 1000]
    ax.scatter(normais.orcamento, normais.receita, s=8, color=NEUTRO, alpha=0.7, label="Demais filmes")
    ax.scatter(out[out.orcamento >= 1000].orcamento, out[out.orcamento >= 1000].receita, s=10, color=DESTAQUE,
               label=f"Outliers de ROI (> {br(100 * limite, 0)}%)")
    ax.scatter(implaus_orc.orcamento, implaus_orc.receita, s=26, color=ALERTA, marker="D",
               label="Orçamento implausível (< US$ 1.000)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    rotulo = matplotlib.ticker.FuncFormatter(
        lambda v, _: {1: "1", 10: "10", 100: "100", 1e3: "1 mil", 1e4: "10 mil", 1e5: "100 mil",
                      1e6: "1 mi", 1e7: "10 mi", 1e8: "100 mi", 1e9: "1 bi", 1e10: "10 bi"}.get(v, ""))
    for eixo in (ax.xaxis, ax.yaxis):
        eixo.set_major_locator(matplotlib.ticker.LogLocator(base=10, numticks=12))
        eixo.set_major_formatter(rotulo)
        eixo.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("Orçamento (US$ de 2010, escala log)")
    ax.set_ylabel("Receita (US$ de 2010, escala log)")
    ax.grid(color=GRADE)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    salvar(fig, "eda_05_outliers.png")

    # ---------------------------------------------------------------- 8. critica x publico
    cp = f.dropna(subset=["nota_critica"])
    rho = cp[["nota_critica", "nota_publico"]].corr(method="spearman").iloc[0, 1]
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(cp.nota_critica, cp.nota_publico, s=8, color=NEUTRO, alpha=0.7)
    ax.set_xlabel("Nota da crítica (Rotten Tomatoes, 0–100)")
    ax.set_ylabel("Nota do público (IMDb, 0–100)")
    ax.grid(color=GRADE)
    ax.text(2, 95, f"Spearman = {br(rho, 2)}  ·  {br(len(cp), 0)} filmes", color=TINTA, fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    salvar(fig, "eda_06_critica_publico.png")
    md += ["## 8. Crítica × público", "", f"- Correlação de Spearman entre a nota da crítica e a do público: {br(rho, 2)}",
           f"- Diferença média (crítica − público): {br((cp.nota_critica - cp.nota_publico).mean())} pontos", ""]

    # ---------------------------------------------------------------- 9. amostras por categoria
    amostra = consulta("""
        select 'produtoras' as variavel, count(*) as categorias,
               count(*) filter (where n = 1) as com_1_filme, count(*) filter (where n >= 20) as com_20_ou_mais
          from (select sk_produtora, count(*) n from sch_dw_filmes.ft_desempenho_filme group by 1) x
        union all
        select 'diretores principais', count(*), count(*) filter (where n = 1), count(*) filter (where n >= 10)
          from (select sk_diretor, count(*) n from sch_dw_filmes.ft_desempenho_filme group by 1) x""")
    md += ["## 9. Tamanho das amostras por categoria", "", tabela_md(amostra), "",
           "(para diretores, a última coluna conta os que têm 10 ou mais filmes)", ""]

    RESUMO.write_text("\n".join(md), encoding="utf-8")
    print("Figuras em", SAIDA)
    print("Resumo em", RESUMO)


if __name__ == "__main__":
    main()
