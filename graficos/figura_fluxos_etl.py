"""Desenha os fluxos das transformacoes (.ktr) e do job (.kjb) a partir do XML.

As posicoes dos steps e das entradas sao as mesmas gravadas pelo Spoon
(<GUI><xloc>/<yloc>), e as ligacoes sao os hops do arquivo. Assim a figura
reproduz o desenho do Spoon sem depender de captura de tela.

Uso: python graficos/figura_fluxos_etl.py
Saida: graficos/claro/fluxo_*.png
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
import textwrap  # noqa: E402

plt.rcParams["text.parse_math"] = False
plt.rcParams["font.family"] = "Segoe UI"

BASE = Path(__file__).resolve().parent.parent
ETL = BASE / "etl"
SAIDA = Path(__file__).resolve().parent / "claro"

ENTRADA, MEIO, SAIDA_COR, ESPECIAL = "#e8eef9", "#ffffff", "#f2d39b", "#e4e2dc"
BORDA, TEXTO, TEXTO2 = "#222222", "#111111", "#5c5b57"
VERDE, VERMELHO, CINZA = "#2f7d32", "#b3261e", "#555555"

TIPOS = {
    "CsvInput": ("CSV file input", ENTRADA), "TableInput": ("Table input", ENTRADA),
    "SelectValues": ("Select values", MEIO), "FilterRows": ("Filter rows", MEIO),
    "SortRows": ("Sort rows", MEIO), "Unique": ("Unique rows", MEIO),
    "StreamLookup": ("Stream lookup", MEIO), "SystemInfo": ("Get system info", MEIO),
    "ExecSQL": ("Execute SQL script", MEIO),
    "TableOutput": ("Table output", SAIDA_COR), "DimensionLookup": ("Dimension lookup/update", SAIDA_COR),
}
W, H = 118, 46  # tamanho da caixa, em coordenadas do Spoon


def caixa(ax, x, y, nome, sub, cor, w=W, h=H):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=7",
                                facecolor=cor, edgecolor=BORDA, linewidth=1.3, zorder=3))
    ax.text(x, y - 7, nome, ha="center", va="center", fontsize=8.6 if len(nome) <= 17 else 7.4, fontweight="bold", color=TEXTO, zorder=4)
    ax.text(x, y + 10, sub, ha="center", va="center", fontsize=7.4, color=TEXTO2, zorder=4)


def ponto_borda(x0, y0, x1, y1, w=W, h=H):
    """Ponto onde a reta (x0,y0)->(x1,y1) sai da caixa centrada em (x0,y0)."""
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return x0, y0
    tx = (w / 2) / abs(dx) if dx else float("inf")
    ty = (h / 2) / abs(dy) if dy else float("inf")
    t = min(tx, ty)
    return x0 + dx * t, y0 + dy * t


def seta(ax, a, b, cor, tracejada=False, rotulo=None, w=W, h=H, curva=0.0):
    x0, y0 = ponto_borda(a[0], a[1], b[0], b[1], w, h)
    x1, y1 = ponto_borda(b[0], b[1], a[0], a[1], w, h)
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11,
                                 color=cor, linewidth=1.3, linestyle="--" if tracejada else "-",
                                 connectionstyle=f"arc3,rad={curva}", zorder=2))
    if rotulo:
        ax.text((x0 + x1) / 2 + 6, (y0 + y1) / 2, rotulo, fontsize=7.2, color=cor,
                ha="left", va="center", zorder=4,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6))


def quebrar(texto, n=16):
    if len(texto) <= n:
        return texto
    if "_" in texto:
        i = texto.rfind("_", 0, n)
        return texto[:i + 1] + chr(10) + texto[i + 1:]
    return chr(10).join(textwrap.wrap(texto, n))


def ler_ktr(arquivo):
    raiz = ET.parse(arquivo).getroot()
    steps = {}
    for s in raiz.iter("step"):
        g = s.find("GUI")
        steps[s.findtext("name")] = dict(tipo=s.findtext("type"), x=int(g.findtext("xloc")),
                                         y=int(g.findtext("yloc")), verdadeiro=s.findtext("send_true_to"),
                                         falso=s.findtext("send_false_to"))
    hops = [(h.findtext("from"), h.findtext("to")) for h in raiz.find("order").findall("hop")]
    return steps, hops


def desenhar_ktr(ax, arquivo, titulo=None, dobrar=None):
    """dobrar = (limite_x, dy): os steps a direita do limite vao para uma segunda linha,
    em sentido inverso (cadeia em "S"), para caber na largura da pagina."""
    steps, hops = ler_ktr(arquivo)
    if dobrar:
        limite, dy = dobrar
        linha1 = [s["x"] for s in steps.values() if s["x"] <= limite]
        linha2 = [s["x"] for s in steps.values() if s["x"] > limite]
        soma = max(linha1) + min(linha2)
        for st in steps.values():
            if st["x"] > limite:
                st["x"], st["y"] = soma - st["x"], st["y"] + dy
    for origem, destino in hops:
        s = steps[origem]
        a, b = (s["x"], s["y"]), (steps[destino]["x"], steps[destino]["y"])
        if s["tipo"] == "FilterRows" and destino == s["falso"]:
            seta(ax, a, b, VERMELHO, True, "falso")
        elif s["tipo"] == "FilterRows" and destino == s["verdadeiro"]:
            seta(ax, a, b, VERDE)
        else:
            seta(ax, a, b, CINZA)
    for nome, s in steps.items():
        sub, cor = TIPOS.get(s["tipo"], (s["tipo"], MEIO))
        caixa(ax, s["x"], s["y"], nome, sub, cor)
    xs = [s["x"] for s in steps.values()]
    ys = [s["y"] for s in steps.values()]
    ax.set_xlim(min(xs) - W / 2 - 12, max(xs) + W / 2 + 12)
    ax.set_ylim(max(ys) + H / 2 + 14, min(ys) - H / 2 - (34 if titulo else 12))
    ax.set_aspect("equal")
    ax.axis("off")
    if titulo:
        ax.text(min(xs) - W / 2, min(ys) - H / 2 - 20, titulo, fontsize=10, fontweight="bold",
                color=TEXTO, ha="left", va="center")


def legenda_ktr(fig, y=0.02, falso=True):
    itens = [(ENTRADA, "entrada"), (MEIO, "transformação"), (SAIDA_COR, "gravação no banco")]
    x = 0.02
    for cor, txt in itens:
        fig.patches.append(Rectangle((x, y), 0.012, 0.035, transform=fig.transFigure,
                                     facecolor=cor, edgecolor=BORDA, linewidth=1))
        fig.text(x + 0.025, y + 0.017, txt, fontsize=8.5, va="center", color=TEXTO2)
        x += 0.13
    if falso:
        fig.text(x + 0.06, y + 0.017, "seta verde: linhas aprovadas no filtro;  seta vermelha tracejada: "
                               "linhas reprovadas", fontsize=8.5, va="center", color=TEXTO2)


def figura_ktr(nome_arquivo, saida, largura=13, altura=2.6, falso=True, dobrar=None, base=0.16):
    fig, ax = plt.subplots(figsize=(largura, altura))
    desenhar_ktr(ax, ETL / nome_arquivo, dobrar=dobrar)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=base)
    legenda_ktr(fig, falso=falso)
    fig.savefig(SAIDA / saida, dpi=200, facecolor="white")
    plt.close(fig)
    print(SAIDA / saida)


def figura_curtas(saida):
    arquivos = ["tr_02_stg_tmdb5000.ktr", "tr_08_stg_rt_filmes.ktr",
                "tr_10_stg_cinema_hall.ktr", "tr_11_dim_filme.ktr"]
    fig, eixos = plt.subplots(2, 2, figsize=(11, 3.6))
    for ax, arq in zip(eixos.flat, arquivos):
        desenhar_ktr(ax, ETL / arq, titulo=arq)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.12, hspace=0.25, wspace=0.08)
    legenda_ktr(fig, falso=False)
    fig.savefig(SAIDA / saida, dpi=200, facecolor="white")
    plt.close(fig)
    print(SAIDA / saida)


def figura_job(saida):
    raiz = ET.parse(ETL / "jb_carga_dw_filmes.kjb").getroot()
    ent = {}
    for e in raiz.iter("entry"):
        ent[e.findtext("name")] = (e.findtext("type"), int(e.findtext("xloc")), int(e.findtext("yloc")))
    # Cadeia de sucesso em "S", 6 entradas por linha, para caber na largura da pagina
    abort = "Carga abortada - verificar log"
    sucesso = {}
    for hop in raiz.find("hops").findall("hop"):
        if hop.findtext("to") != abort:
            sucesso[hop.findtext("from")] = hop.findtext("to")
    ordem = ["Start"]
    while ordem[-1] in sucesso:
        ordem.append(sucesso[ordem[-1]])
    por_linha, dx, dy = 6, 170, 125
    for i, nome in enumerate(ordem):
        r, c = divmod(i, por_linha)
        x = c * dx if r % 2 == 0 else (por_linha - 1 - c) * dx
        ent[nome] = (ent[nome][0], x, r * dy)
    linhas = (len(ordem) + por_linha - 1) // por_linha
    ent[abort] = (ent[abort][0], 2.5 * dx, linhas * dy + 10)
    w, h = 140, 62
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    for hop in raiz.find("hops").findall("hop"):
        a, b = hop.findtext("from"), hop.findtext("to")
        pa, pb = ent[a][1:], ent[b][1:]
        if b == abort:
            ax.add_patch(FancyArrowPatch(ponto_borda(*pa, *pb, w, h), ponto_borda(*pb, *pa, w, h),
                                         arrowstyle="-|>", mutation_scale=7, color=VERMELHO, alpha=0.22,
                                         linewidth=0.8, linestyle="--", zorder=1))
        else:
            seta(ax, pa, pb, VERDE if hop.findtext("unconditional") != "Y" else CINZA, w=w, h=h)
    for nome, (tipo, x, y) in ent.items():
        if tipo == "TRANS":
            num, resto = nome.split(" - ", 1)
            cor = MEIO if int(num) > 10 else ENTRADA
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=7",
                                        facecolor=cor, edgecolor=BORDA, linewidth=1.3, zorder=3))
            ax.text(x, y - 15, num, ha="center", va="center", fontsize=9, fontweight="bold",
                    color=TEXTO, zorder=4)
            ax.text(x, y + 9, quebrar(resto, 17), ha="center", va="center",
                    fontsize=8, color=TEXTO, zorder=4, linespacing=1.0)
        elif tipo == "SPECIAL":
            caixa(ax, x, y, "Start", "início", ESPECIAL, w, h)
        elif tipo == "SUCCESS":
            caixa(ax, x, y, "Carga concluída", "sucesso", "#cfe8cf", w, h)
        else:
            caixa(ax, x, y, "Carga abortada", "verificar log", "#f4c7c3", w, h)
    xs = [v[1] for v in ent.values()]
    ys = [v[2] for v in ent.values()]
    ax.set_xlim(min(xs) - w / 2 - 10, max(xs) + w / 2 + 10)
    ax.set_ylim(max(ys) + h / 2 + 10, min(ys) - h / 2 - 10)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.12)
    x = 0.02
    for cor, txt in [(ENTRADA, "staging (01 a 10)"), (MEIO, "dimensões, pontes, fatos e pós-carga (11 a 22)")]:
        fig.patches.append(Rectangle((x, 0.025), 0.01, 0.03, transform=fig.transFigure,
                                     facecolor=cor, edgecolor=BORDA, linewidth=1))
        fig.text(x + 0.022, 0.04, txt, fontsize=8.5, va="center", color=TEXTO2)
        x += 0.2 if "staging" in txt else 0.5
    fig.text(0.02, 0.0, "Seta verde: segue em caso de sucesso; vermelha tracejada: desvia para o aborto em caso "
                        "de falha.", fontsize=8.5, va="bottom", color=TEXTO2)
    fig.savefig(SAIDA / saida, dpi=200, facecolor="white")
    plt.close(fig)
    print(SAIDA / saida)


def main():
    SAIDA.mkdir(exist_ok=True)
    figura_ktr("tr_01_stg_tmdb_movies.ktr", "fluxo_tr01.png", largura=9, altura=4.2, dobrar=(700, 150),
               base=0.1)
    figura_ktr("tr_06_stg_imdb_principais.ktr", "fluxo_tr06.png", largura=9, altura=3.0)
    figura_curtas("fluxo_transformacoes_curtas.png")
    figura_job("fluxo_job.png")


if __name__ == "__main__":
    main()
