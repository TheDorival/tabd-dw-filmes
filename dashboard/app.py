"""Painel do DW Filmes: Meta SMART e as 12 perguntas de negócio.

Lê os CSVs de resultados/, que são o conteúdo das views do Data Warehouse
(sql/04_views_perguntas.sql) exportado na carga registrada.
Rodar localmente:  streamlit run dashboard/app.py
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RES = Path(__file__).resolve().parent.parent / "resultados"

OURO, NEUTRO, CLARO, SUAVE, LINHA = "#FFC74B", "#5C5B57", "#F3EEE2", "#B8B2A4", "#2A2A28"

GENEROS = {
    "Action": "Ação", "Adventure": "Aventura", "Animation": "Animação", "Comedy": "Comédia",
    "Crime": "Crime", "Documentary": "Documentário", "Drama": "Drama", "Family": "Família",
    "Fantasy": "Fantasia", "History": "História", "Horror": "Terror", "Music": "Música",
    "Mystery": "Mistério", "Romance": "Romance", "Science Fiction": "Ficção científica",
    "Thriller": "Suspense", "War": "Guerra", "Western": "Faroeste", "Foreign": "Estrangeiro",
    "TV Movie": "Filme para TV",
}
JANELAS = {"Verao": "Verão", "Fim de Ano": "Fim de ano", "Premiacoes": "Premiações", "Regular": "Regular"}
ORDEM_JANELAS = ["Premiações", "Verão", "Regular", "Fim de ano"]

st.set_page_config(page_title="DW Filmes", page_icon="🎬", layout="wide")


@alt.theme.register("dw_filmes", enable=True)
def _tema():
    return alt.theme.ThemeConfig(config={
        "background": "transparent",
        "view": {"stroke": None},
        "font": "Inter, Arial, sans-serif",
        "axis": {"labelColor": SUAVE, "titleColor": SUAVE, "gridColor": LINHA, "domainColor": NEUTRO,
                 "tickColor": NEUTRO, "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 400},
        "legend": {"labelColor": SUAVE, "titleColor": SUAVE},
        "text": {"color": CLARO},
        "locale": {"number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["US$ ", ""]}},
    })


@st.cache_data
def ler(nome: str) -> pd.DataFrame:
    df = pd.read_csv(RES / f"{nome}.csv")
    for col in ("genero_principal", "genero"):
        if col in df:
            df[col] = df[col].map(GENEROS).fillna(df[col])
    if "janela_mercado" in df:
        df["janela_mercado"] = df["janela_mercado"].map(JANELAS).fillna(df["janela_mercado"])
    return df


def br(v, casas=1):
    """Número no formato brasileiro."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def destaque(campo: str, valor) -> alt.Color:
    """Ouro para o item em destaque, cinza para os demais."""
    return alt.condition(alt.datum[campo] == valor, alt.value(OURO), alt.value(NEUTRO))


def barras_h(df, x, y, titulo_x, campo_destaque, valor_destaque, tooltip, fmt=".1f", altura=None):
    base = alt.Chart(df).encode(
        y=alt.Y(f"{y}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X(f"{x}:Q", title=titulo_x),
        tooltip=tooltip,
    )
    barras = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        color=destaque(campo_destaque, valor_destaque))
    rotulos = base.mark_text(align="left", dx=6, color=CLARO, fontSize=12).encode(
        text=alt.Text(f"{x}:Q", format=fmt))
    return (barras + rotulos).properties(height=altura or max(220, 30 * len(df)))


def limiar_claro(serie: pd.Series) -> float:
    """Valor a partir do qual a célula do mapa de calor fica clara e pede texto escuro."""
    return float(serie.min() + 0.6 * (serie.max() - serie.min()))


def tabela(df, rotulo="Ver tabela"):
    with st.expander(rotulo):
        st.dataframe(df, hide_index=True, width="stretch")


def pergunta(num, titulo, enunciado):
    st.markdown(f"### P{num} · {titulo}")
    st.caption(enunciado)


# ---------------------------------------------------------------- cabeçalho
st.title("DW Filmes")
st.markdown(
    "Painel do Data Warehouse de desempenho de filmes (TMDB, IMDb, Rotten Tomatoes e Cinema Hall). "
    "Os números vêm das views de `sql/04_views_perguntas.sql`, exportadas em `resultados/`.")

meta = ler("meta_smart")
base_, inicial, final = meta.iloc[0], meta.iloc[1], meta.iloc[2]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Prejuízo, linha de base", f"{br(base_.taxa_prejuizo_pct)}%",
          help=f"Todos os {int(base_.filmes)} lançamentos de 2011–2015.")
c2.metric("Prejuízo, regra final", f"{br(final.taxa_prejuizo_pct)}%",
          delta=f"-{br(final.reducao_prejuizo_pct)}%", delta_color="inverse",
          help="Meta: no máximo 21,9% (−20%).")
c3.metric("Nota do público, regra final", br(final.nota_media, 2),
          delta=f"+{br(final.diferenca_nota, 2)} ponto", help="Meta: nota ≥ 61,72.")
c4.metric("Combinações recomendadas", int(final.combinacoes), help=f"{int(final.filmes)} filmes em 2011–2015.")

abas = st.tabs(["Meta SMART", "Elenco e direção", "Gênero e janela", "Orçamento e produtoras", "Público"])

# ---------------------------------------------------------------- Meta SMART
with abas[0]:
    st.markdown("### Validação retrospectiva da Meta SMART")
    st.caption("Recomendações geradas só com os lançamentos de 1960–2010 e avaliadas nos de 2011–2015. "
               "A meta exige prejuízo ≤ 21,9% sem que a nota do público caia mais de 2 pontos.")
    m = meta.assign(
        grupo_curto=["Todos os lançamentos", "Regra inicial", "Regra final"],
        situacao=["linha de base", "não cumpre (nota −2,02)", "cumpre as duas metas"])
    barras = alt.Chart(m).mark_bar(cornerRadiusEnd=4, height={"band": 0.6}).encode(
        y=alt.Y("grupo_curto:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X("taxa_prejuizo_pct:Q", title="Taxa de prejuízo (%)", scale=alt.Scale(domain=[0, 30])),
        color=destaque("grupo_curto", "Regra final"),
        tooltip=[alt.Tooltip("grupo_curto:N", title="Grupo"), alt.Tooltip("filmes:Q", title="Filmes"),
                 alt.Tooltip("taxa_prejuizo_pct:Q", title="Prejuízo (%)", format=".1f"),
                 alt.Tooltip("nota_media:Q", title="Nota do público", format=".2f"),
                 alt.Tooltip("situacao:N", title="Situação")])
    rot = barras.mark_text(align="left", dx=6).encode(text=alt.Text("taxa_prejuizo_pct:Q", format=".1f"),
                                                     color=alt.value(CLARO))
    linha = alt.Chart(pd.DataFrame({"meta": [21.9]})).mark_rule(color=CLARO, strokeDash=[6, 4]).encode(x="meta:Q")
    st.altair_chart((barras + rot + linha).properties(height=220), width="stretch")
    st.markdown("A linha tracejada é a meta (21,9%). A regra inicial reduz o prejuízo, mas a nota cai 2,02 pontos "
                "e viola a restrição por 0,02; a regra final acrescenta o critério de nota histórica e cumpre as duas metas.")
    tabela(meta)

# ---------------------------------------------------------------- Elenco e direção
with abas[1]:
    p1 = ler("p01_dupla_diretor_ator")
    p1["dupla"] = p1.diretor + " + " + p1.ator_principal
    pergunta(1, "Dupla de diretor e ator principal",
             "Qual combinação de diretor e ator principal tem o maior ISI médio, com pelo menos três filmes juntos?")
    col_a, col_b = st.columns(2)
    min_filmes = col_a.slider("Mínimo de filmes juntos", 3, int(p1.filmes.max()), 3, key="p1min")
    top = col_b.slider("Quantas duplas mostrar", 5, 25, 10, key="p1top")
    d1 = p1[p1.filmes >= min_filmes].nlargest(top, "isi_medio")
    if d1.empty:
        st.info("Nenhuma dupla com esse mínimo de filmes.")
    else:
        st.altair_chart(barras_h(d1, "isi_medio", "dupla", "ISI médio (0 a 100)", "dupla", d1.iloc[0].dupla,
                                 ["dupla:N", "filmes:Q", alt.Tooltip("isi_medio:Q", format=".1f"),
                                  alt.Tooltip("roi_mediano_pct:Q", title="ROI mediano (%)", format=".0f"),
                                  alt.Tooltip("nota_media:Q", title="Nota do público", format=".1f")]),
                        width="stretch")
    st.markdown("O topo é dominado por franquias (O Senhor dos Anéis, 007, Indiana Jones), todas muito acima "
                "da média geral de 55,9: vale mais como referência do que como regra.")
    tabela(p1.drop(columns="dupla"))

    st.divider()
    p2 = ler("p02_variacao_diretor")
    pergunta(2, "Mesmo diretor, atores principais diferentes",
             "Quanto variam a nota do público e o ROI entre os filmes de um diretor com protagonistas diferentes?")
    k1, k2 = st.columns(2)
    k1.metric("Amplitude mediana da nota", f"{br(p2.amplitude_nota.median())} pontos",
              help=f"{len(p2)} diretores com pelo menos 3 atores principais.")
    k2.metric("Amplitude mediana do ROI mediano", f"{br(p2.amplitude_roi_pct.median(), 0)} p.p.")
    n2 = st.slider("Diretores com mais filmes", 5, 30, 15, key="p2n")
    d2 = p2.nlargest(n2, "filmes").copy()
    ordem = d2.sort_values("amplitude_nota", ascending=False).diretor.tolist()
    enc_y = alt.Y("diretor:N", sort=ordem, title=None)
    tip = ["diretor:N", alt.Tooltip("atores_principais:Q", title="Atores principais"), "filmes:Q",
           alt.Tooltip("nota_min:Q", title="Menor nota"), alt.Tooltip("nota_max:Q", title="Maior nota"),
           alt.Tooltip("amplitude_nota:Q", title="Amplitude")]
    regra = alt.Chart(d2).mark_rule(color=NEUTRO, strokeWidth=2).encode(
        y=enc_y, x=alt.X("nota_min:Q", title="Nota média do público por ator principal", scale=alt.Scale(zero=False)),
        x2="nota_max:Q", tooltip=tip)
    pmin = alt.Chart(d2).mark_point(filled=True, size=90, color=SUAVE).encode(y=enc_y, x="nota_min:Q", tooltip=tip)
    pmax = alt.Chart(d2).mark_point(filled=True, size=90, color=OURO).encode(y=enc_y, x="nota_max:Q", tooltip=tip)
    st.altair_chart((regra + pmin + pmax).properties(height=30 * len(d2)), width="stretch")
    st.caption("Cinza: menor nota média entre os atores principais do diretor. Ouro: maior. "
               "Roteiro, orçamento e época também mudam entre os filmes, então a diferença não é só do ator.")
    tabela(p2)

    st.divider()
    p8 = ler("p08_lancamento_anterior")
    pergunta(8, "Ator principal com lançamento recente",
             "Muda a nota do público quando o ator principal teve outro lançamento nos 12 meses anteriores?")
    com, sem = p8.iloc[0], p8.iloc[1]
    k1, k2, k3 = st.columns(3)
    k1.metric("Com lançamento recente", br(com.nota_media, 2), help=f"{int(com.filmes)} filmes")
    k2.metric("Sem lançamento recente", br(sem.nota_media, 2), help=f"{int(sem.filmes)} filmes")
    k3.metric("Diferença", f"{br(sem.nota_media - com.nota_media, 2)} ponto",
              help=f"Desvio-padrão das notas: {br(com.desvio_nota, 2)} e {br(sem.desvio_nota, 2)}.")
    st.markdown("Diferença muito menor que o desvio-padrão das notas (9 a 10 pontos): não há efeito relevante.")
    tabela(p8)

# ---------------------------------------------------------------- Gênero e janela
with abas[2]:
    p3 = ler("p03_genero_janela")
    pergunta(3, "Melhor janela por gênero",
             "Qual janela de mercado concentra as maiores receitas e notas, por gênero? (mínimo de 10 filmes)")
    medidas = {"Receita mediana (US$ mi de 2010)": ("receita_mediana_mi", "pos_receita", ".0f"),
               "Nota média do público": ("nota_media", "pos_nota", ".1f"),
               "Nota média da crítica": ("critica_media", "pos_critica", ".1f")}
    escolha = st.radio("Medida", list(medidas), horizontal=True, key="p3m")
    campo, pos, fmt = medidas[escolha]
    base3 = alt.Chart(p3).encode(
        x=alt.X("janela_mercado:N", sort=ORDEM_JANELAS, title=None, axis=alt.Axis(orient="top", labelAngle=0)),
        y=alt.Y("genero_principal:N", title=None),
        tooltip=["genero_principal:N", "janela_mercado:N", "filmes:Q",
                 alt.Tooltip(f"{campo}:Q", title=escolha, format=fmt)])
    calor = base3.mark_rect(stroke="#000000", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color(f"{campo}:Q", title=escolha, scale=alt.Scale(range=["#2A2A28", OURO])))
    texto = base3.mark_text(fontSize=12).encode(
        text=alt.Text(f"{campo}:Q", format=fmt),
        color=alt.condition(f"datum['{campo}'] >= {limiar_claro(p3[campo])}", alt.value("#000000"), alt.value(CLARO)))
    st.altair_chart((calor + texto).properties(height=34 * p3.genero_principal.nunique()), width="stretch")
    lideres = p3[p3[pos] == 1].janela_mercado.value_counts()
    st.markdown("Janela líder por gênero nesta medida: " +
                ", ".join(f"**{j}** em {n}" for j, n in lideres.items()) + ". Células vazias: menos de 10 filmes.")
    tabela(p3)

    st.divider()
    p4 = ler("p04_trimestre1_fim_de_ano")
    pergunta(4, "Primeiro trimestre × fim de ano",
             "Como se comparam os lançamentos de janeiro a março com os da janela de fim de ano?")
    t1, fa = p4.iloc[0], p4.iloc[1]
    k = st.columns(5)
    k[0].metric("Receita mediana", f"US$ {br(fa.receita_mediana_mi)} mi",
                delta=f"US$ {br(fa.receita_mediana_mi - t1.receita_mediana_mi)} mi vs. 1º tri")
    k[1].metric("ROI mediano", f"{br(fa.roi_mediano_pct, 0)}%", delta=f"{br(fa.roi_mediano_pct - t1.roi_mediano_pct, 0)} p.p.")
    k[2].metric("Nota do público", br(fa.nota_media), delta=br(fa.nota_media - t1.nota_media))
    k[3].metric("ISI médio", br(fa.isi_medio), delta=br(fa.isi_medio - t1.isi_medio))
    k[4].metric("Taxa de prejuízo", f"{br(fa.taxa_prejuizo_pct)}%",
                delta=f"{br(fa.taxa_prejuizo_pct - t1.taxa_prejuizo_pct)} p.p.", delta_color="inverse")
    st.caption(f"Valores do fim de ano ({int(fa.filmes)} filmes); a variação compara com o 1º trimestre "
               f"({int(t1.filmes)} filmes). O fim de ano vence em todos os indicadores.")
    tabela(p4)

    st.divider()
    p5 = ler("p05_prejuizo_genero_janela")
    p5["combinacao"] = p5.genero_principal + " · " + p5.janela_mercado
    pergunta(5, "Combinações com menor risco de prejuízo",
             "Quais combinações de gênero e janela têm a menor taxa de prejuízo? (mínimo de 15 filmes)")
    n5 = st.slider("Quantas combinações mostrar", 5, len(p5), 10, key="p5n")
    d5 = p5.nsmallest(n5, "taxa_prejuizo_pct")
    graf5 = alt.Chart(d5).encode(
        y=alt.Y("combinacao:N", sort=alt.EncodingSortField("taxa_prejuizo_pct", order="ascending"), title=None,
                axis=alt.Axis(labelLimit=320)),
        x=alt.X("taxa_prejuizo_pct:Q", title="Taxa de prejuízo (%)", scale=alt.Scale(domain=[0, 40])),
        tooltip=["combinacao:N", "filmes:Q", alt.Tooltip("taxa_prejuizo_pct:Q", title="Prejuízo (%)", format=".1f"),
                 alt.Tooltip("nota_media:Q", title="Nota do público", format=".1f")])
    b5 = graf5.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        color=alt.condition(alt.datum.nota_media < 60, alt.value(NEUTRO), alt.value(OURO)))
    r5 = graf5.mark_text(align="left", dx=6, color=CLARO).encode(text=alt.Text("taxa_prejuizo_pct:Q", format=".1f"))
    l5 = alt.Chart(pd.DataFrame({"m": [27.4]})).mark_rule(color=CLARO, strokeDash=[6, 4]).encode(x="m:Q")
    st.altair_chart((b5 + r5 + l5).properties(height=30 * len(d5)), width="stretch")
    st.caption("Linha tracejada: taxa de prejuízo de todos os filmes (27,4%). Em cinza, combinações com nota do "
               "público abaixo de 60, como as de terror: baixo risco não garante boa recepção.")
    tabela(p5.drop(columns="combinacao"))

    st.divider()
    p9 = ler("p09_desvio_isi_genero")
    pergunta(9, "Gêneros mais consistentes",
             "Quais gêneros têm a menor variação (desvio-padrão) do ISI? (mínimo de 50 filmes)")
    d9 = p9.sort_values("desvio_padrao_isi")
    graf9 = alt.Chart(d9).encode(
        y=alt.Y("genero:N", sort=alt.EncodingSortField("desvio_padrao_isi", order="ascending"), title=None),
        x=alt.X("desvio_padrao_isi:Q", title="Desvio-padrão do ISI", scale=alt.Scale(zero=False, domain=[16.5, 19])),
        tooltip=["genero:N", "filmes:Q", alt.Tooltip("isi_medio:Q", format=".1f"),
                 alt.Tooltip("desvio_padrao_isi:Q", title="Desvio-padrão", format=".2f")])
    st.altair_chart((graf9.mark_point(filled=True, size=110).encode(color=destaque("genero", d9.iloc[0].genero))
                     + graf9.mark_text(align="left", dx=10, color=CLARO).encode(
                         text=alt.Text("desvio_padrao_isi:Q", format=".1f")))
                    .properties(height=26 * len(d9)), width="stretch")
    st.caption("O eixo começa em 16,5 para mostrar a diferença: entre o mais e o menos consistente são só 1,5 ponto. "
               "O gênero, sozinho, pouco diferencia o risco.")
    tabela(p9)

    st.divider()
    p11 = ler("p11_sucesso_equilibrado")
    p11["combinacao"] = p11.genero_principal + " · " + p11.janela_mercado
    pergunta(11, "Sucesso financeiro com aprovação da crítica e do público",
             "Quais combinações entregam ROI acima da mediana com crítica e público ≥ 70? (mínimo de 15 filmes)")
    n11 = st.slider("Quantas combinações mostrar", 5, len(p11), 10, key="p11n")
    d11 = p11.nlargest(n11, "taxa_equilibrio_pct")
    st.altair_chart(barras_h(d11, "taxa_equilibrio_pct", "combinacao", "Filmes com sucesso equilibrado (%)",
                             "combinacao", d11.iloc[0].combinacao,
                             ["combinacao:N", "filmes:Q", alt.Tooltip("filmes_equilibrados:Q", title="Equilibrados"),
                              alt.Tooltip("taxa_equilibrio_pct:Q", title="Taxa (%)", format=".1f")]),
                    width="stretch")
    st.caption("Drama no fim de ano tem o maior número absoluto de sucessos equilibrados (56 de 158 filmes).")
    tabela(p11.drop(columns="combinacao"))

# ---------------------------------------------------------------- Orçamento e produtoras
with abas[3]:
    p6 = ler("p06_produtora_isi_orcamento")
    pergunta(6, "ISI proporcional ao orçamento, por produtora",
             "Qual produtora entrega mais ISI por US$ 10 milhões de orçamento médio? (mínimo de 10 filmes)")
    n6 = st.slider("Quantas produtoras mostrar", 5, len(p6), 12, key="p6n")
    d6 = p6.nlargest(n6, "isi_por_10mi")
    st.altair_chart(barras_h(d6, "isi_por_10mi", "produtora", "ISI médio por US$ 10 mi de orçamento médio",
                             "produtora", d6.iloc[0].produtora,
                             ["produtora:N", "filmes:Q", alt.Tooltip("isi_medio:Q", format=".1f"),
                              alt.Tooltip("orcamento_medio_mi:Q", title="Orçamento médio (US$ mi)", format=".1f"),
                              alt.Tooltip("isi_por_10mi:Q", title="ISI por US$ 10 mi", format=".1f")]),
                    width="stretch")
    st.caption("A métrica favorece estúdios de orçamento baixo. Lions Gate Films e Lionsgate aparecem separadas: "
               "a produtora é identificada pelo nome, sem chave estável.")
    tabela(p6)

    st.divider()
    p7 = ler("p07_faixa_orcamento")
    p7["rotulo"] = p7.apply(lambda r: f"{br(r.orcamento_min_mi)}–{br(r.orcamento_max_mi)}", axis=1)
    pergunta(7, "Faixa de orçamento e ROI",
             "A partir de que faixa de orçamento o ROI mediano deixa de crescer? (dez faixas com o mesmo número de filmes)")
    eixo = alt.X("rotulo:N", sort=p7.rotulo.tolist(), title="Faixa de orçamento (US$ mi de 2010)",
                 axis=alt.Axis(labelAngle=-30))
    tip7 = [alt.Tooltip("rotulo:N", title="Faixa (US$ mi)"), "filmes:Q",
            alt.Tooltip("roi_mediano_pct:Q", title="ROI mediano (%)", format=".0f"),
            alt.Tooltip("taxa_prejuizo_pct:Q", title="Prejuízo (%)", format=".1f")]
    roi = alt.Chart(p7).encode(x=eixo, y=alt.Y("roi_mediano_pct:Q", title="ROI mediano (%)",
                                               scale=alt.Scale(domain=[0, 250])), tooltip=tip7)
    g_roi = (roi.mark_line(color=OURO, strokeWidth=2) + roi.mark_point(filled=True, size=80, color=OURO)
             + roi.mark_text(dy=-12, color=CLARO).encode(text=alt.Text("roi_mediano_pct:Q", format=".0f")))
    prej = alt.Chart(p7).encode(x=eixo, y=alt.Y("taxa_prejuizo_pct:Q", title="Taxa de prejuízo (%)"), tooltip=tip7)
    g_prej = (prej.mark_bar(cornerRadiusEnd=4).encode(color=destaque("faixa", 10))
              + prej.mark_text(dy=-8, color=CLARO).encode(text=alt.Text("taxa_prejuizo_pct:Q", format=".1f")))
    st.altair_chart(alt.vconcat(g_roi.properties(height=240), g_prej.properties(height=200))
                    .resolve_scale(x="shared"), width="stretch")
    st.caption("O ROI mediano é maior na faixa mais barata (inflada por 25 orçamentos implausíveis da fonte), chega ao "
               "mínimo entre US$ 52 e 71 milhões e volta a subir nas duas faixas mais caras. A faixa acima de "
               "US$ 103 milhões tem a menor taxa de prejuízo.")
    tabela(p7.drop(columns="rotulo"))

    st.divider()
    p10 = ler("p10_discriminacao_variaveis")
    p10["epsilon2_pct"] = p10.epsilon2 * 100
    pergunta(10, "Variável que mais discrimina o sucesso",
             "Que parcela da variação do ISI cada variável de decisão explica (ε² de uma ANOVA de um fator)?")
    st.altair_chart(barras_h(p10, "epsilon2_pct", "variavel", "Variação do ISI explicada (ε², %)", "variavel",
                             p10.nlargest(1, "epsilon2").iloc[0].variavel,
                             ["variavel:N", alt.Tooltip("categorias_com_5_ou_mais_filmes:Q", title="Categorias"),
                              alt.Tooltip("epsilon2_pct:Q", title="ε² (%)", format=".1f")]),
                    width="stretch")
    st.caption("Nenhuma variável explica sozinha mais de 8%: a decisão precisa combinar fatores. "
               "Categorias com menos de 5 filmes foram agrupadas em “Outros”.")
    tabela(p10.drop(columns="epsilon2_pct"))

# ---------------------------------------------------------------- Público
with abas[4]:
    p12 = ler("p12_perfil_espectador")
    pergunta(12, "Perfil do espectador por gênero",
             "Qual faixa etária concentra a compra de ingressos e a intenção de recompra em cada gênero?")
    medidas12 = {"Intenção de recompra (%)": ("taxa_recompra_pct", ".1f"),
                 "Ingressos": ("ingressos", ".0f"),
                 "Participação nos ingressos do gênero (%)": ("pct_ingressos_do_genero", ".1f")}
    esc12 = st.radio("Medida", list(medidas12), horizontal=True, key="p12m")
    c12, f12 = medidas12[esc12]
    base12 = alt.Chart(p12).encode(
        x=alt.X("faixa_etaria:N", title="Faixa etária", axis=alt.Axis(orient="top", labelAngle=0)),
        y=alt.Y("genero:N", title=None),
        tooltip=["genero:N", "faixa_etaria:N", "ingressos:Q",
                 alt.Tooltip("taxa_recompra_pct:Q", title="Recompra (%)", format=".1f"),
                 alt.Tooltip("preco_medio:Q", title="Preço médio", format=".2f")])
    st.altair_chart((base12.mark_rect(stroke="#000000", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color(f"{c12}:Q", title=esc12, scale=alt.Scale(range=["#2A2A28", OURO])))
        + base12.mark_text(fontSize=13).encode(
            text=alt.Text(f"{c12}:Q", format=f12),
            color=alt.condition(f"datum['{c12}'] >= {limiar_claro(p12[c12])}", alt.value("#000000"), alt.value(CLARO))))
        .properties(height=60 * p12.genero.nunique()), width="stretch")
    st.caption("A faixa de 35 a 44 anos compra mais ingressos (349 de 1.440); drama na faixa de 55 a 60 anos tem a "
               "maior intenção de recompra (67,6%). Base pequena (cerca de 60 ingressos por combinação) e sem filme "
               "ou data: orienta comunicação e público-alvo, não a decisão sobre um título.")
    tabela(p12)

st.divider()
st.caption("DW Filmes · Tópicos Avançados em Banco de Dados (IFAL) · Daniel Lage Cortez, Leonardo José Lucas Ferro "
           "Moreira e Marcelo Alves Feitoza · [repositório](https://github.com/TheDorival/tabd-dw-filmes)")
