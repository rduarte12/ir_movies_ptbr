/* Apresentação do FilmUSP: navegação e slides interativos.
   Todos os números vêm de presentation.json, gerado pelo serviço de busca real. */
(function () {
  "use strict";

  const D = JSON.parse(document.getElementById("fu-data").textContent);
  const M = D.manifest;
  const PLACEHOLDER = window.FU_PLACEHOLDER;
  const POSTER_BASE = "https://image.tmdb.org/t/p/";

  // ---------- utilitários ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      e.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return e;
  }
  const nf = (n) => n.toLocaleString("pt-BR");
  const dec = (x, d = 3) => Number(x).toFixed(d).replace(".", ",");
  const pct = (x) => (x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";
  const movie = (id) => D.movies[String(id)] || { id, title: "?", year: "" };
  const label = (m) => (m.year ? `${m.title} (${m.year})` : m.title);
  // Pôster embutido no HTML quando o build usou --embed-posters; senão, o servidor da TMDB.
  const EMBEDDED = D.posters || {};
  function poster(m, size = "w154") {
    const src = !m.poster_path ? PLACEHOLDER : (EMBEDDED[m.poster_path] || POSTER_BASE + size + m.poster_path);
    const img = h("img", { class: "poster", alt: `Pôster de ${m.title}`, src });
    img.addEventListener("error", () => { img.src = PLACEHOLDER; }, { once: true });
    return img;
  }
  function normalize(word) {
    return word.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]/g, "");
  }
  // Seletor de consultas reaproveitado por vários slides.
  function picker(name, queries, onPick, initial = 0) {
    const root = document.querySelector(`[data-picker="${name}"]`);
    const buttons = queries.map((q, i) => h("button", {
      class: "chip", type: "button", "aria-pressed": String(i === initial),
      onclick: () => select(i),
    }, `“${q}”`));
    function select(i) {
      buttons.forEach((b, j) => b.setAttribute("aria-pressed", String(i === j)));
      onPick(i);
    }
    root.append(...buttons);
    select(initial);
  }

  // ---------- rodapé (atribuição TMDB em todos os slides) ----------
  const slides = Array.from(document.querySelectorAll(".slide"));
  slides.forEach((s, i) => {
    s.setAttribute("data-footer",
      `${i + 1} / ${slides.length}   ·   FilmUSP   ·   ${M.tmdb_attribution}.`);
  });

  // ---------- capa e acervo ----------
  const ex0 = D.examples[0];
  $("#cover-words").append(...ex0.trace.stems.map((s) => h("span", { class: "tok stem" }, s)));
  $("#cover-posters").append(...ex0.hits.slice(0, 5).map((hit) => poster(movie(hit.movie_id))));

  const snap = M.snapshot;
  const stats = [
    [nf(M.n_movies), "filmes com sinopse em português"],
    [nf(snap.candidates_tested), "filmes populares analisados"],
    [nf(D.vocabulary.n_terms_total), "palavras diferentes que o buscador conhece"],
    [nf(M.embeddings.dimension), "números que descrevem o sentido de cada filme"],
    [nf(snap.overview_word_count.median), "palavras numa sinopse típica"],
    [nf(snap.rejections_by_reason.no_overview), "filmes ficaram de fora por não ter sinopse em português"],
  ];
  $("#stats").append(...stats.map(([b, s]) => h("div", { class: "stat" }, h("b", {}, b), h("span", {}, s))));
  $("#mini-grid").append(...ex0.hits.slice(0, 5).map((hit) => {
    const m = movie(hit.movie_id);
    return h("figure", {}, poster(m), h("figcaption", {}, label(m)));
  }));

  // ---------- 3 · pipeline ----------
  function renderPipeline(i) {
    const ex = D.examples[i];
    const t = ex.trace;
    const oov = new Set(ex.oov_terms);
    const top = ex.hits[0];
    const topMovie = movie(top.movie_id);
    const maxW = Math.max(...ex.query_weights.map((w) => w.q_weight), 1e-9);
    const step = (title, what, ...body) => h("div", { class: "pstep" },
      h("h4", {}, title), h("p", { class: "what" }, what), h("div", { class: "body" }, ...body));
    const root = $("#pipeline");
    root.replaceChildren(
      step("1 · Sua frase", "Do jeitinho que você digitou.",
        h("p", { style: "font-size:20px;margin:0" }, `“${ex.query}”`)),
      step("2 · Palavras", "Tudo minúsculo, sem acento, só letras e números.",
        h("div", {}, t.original_tokens.map((w) => h("span", { class: "tok" }, w)))),
      step("3 · Palavras comuns saem", "“de”, “um”, “que”… aparecem em todo texto e não ajudam a escolher um filme.",
        h("div", {}, t.original_tokens.map((w) =>
          h("span", { class: t.stopped.includes(w) ? "tok stop" : "tok" }, w)))),
      step("4 · Raiz da palavra", "Variações viram uma só: “assustador” e “assustadora” → “assust”.",
        h("div", {}, Object.entries(t.stem_to_surface).map(([stem, forms]) =>
          h("div", { style: "margin-bottom:6px" },
            h("span", { class: "tok" }, forms[0]), h("span", { class: "arrow" }, " → "),
            h("span", { class: oov.has(stem) ? "tok oov" : "tok stem" }, stem))))),
      step("5 · Pesos e pontuação", "Cada palavra ganha um peso: quanto mais rara, mais vale. Depois a frase é comparada com cada sinopse.",
        h("div", {}, ex.query_weights.map((w) => h("div", { class: "wbar" },
          h("span", {}, w.stem),
          h("span", { class: "track" }, h("span", { class: "fill", style: `width:${(100 * w.q_weight / maxW).toFixed(1)}%;display:block` })),
          h("span", { class: "num" }, dec(w.q_weight, 2))))),
        h("div", { class: "result-pill" }, "1º lugar: ", h("strong", {}, label(topMovie)), h("br"),
          "pontuação: ", h("b", {}, dec(top.score)))),
    );
  }
  picker("pipeline", D.examples.map((e) => e.query), renderPipeline);

  // ---------- 4 · raridade ----------
  const N = D.vocabulary.n_docs;
  const THR = M.config.rare_idf_threshold;
  const stopSet = new Set(D.stopwords);
  const byWord = new Map();
  const byStem = new Map();
  for (const [word, stem, df, idf, display] of D.vocabulary.entries) {
    const e = { word: display || word, stem, df, idf };
    if (!byWord.has(word)) byWord.set(word, e);
    byStem.set(stem, e);
  }
  $("#rarity-list").append(...D.vocabulary.entries.slice(0, 4000).map((e) => h("option", { value: e[4] || e[0] })));
  function lookup(raw) {
    const w = normalize(raw);
    if (!w) return null;
    if (stopSet.has(w)) return { kind: "stop", word: w };
    if (byWord.has(w)) return { kind: "ok", ...byWord.get(w) };
    for (let n = w.length; n >= 4; n--) {
      const s = w.slice(0, n);
      if (byStem.has(s)) return { kind: "approx", typed: w, ...byStem.get(s) };
    }
    return { kind: "none", word: w };
  }
  const presets = ["drama", "familia", "amor", "policial", "robo", "tubarao", "astronauta"]
    .map(lookup).filter((x) => x && x.kind === "ok");
  const idfMin = 1.5, idfMax = Math.log((1 + N) / (1 + 1)) + 1;
  const yOf = (idf) => 100 * (idfMax - idf) / (idfMax - idfMin);
  function renderScale(current) {
    const sc = $("#rarity-scale");
    sc.replaceChildren(h("p", { class: "scale-title", style: "position:absolute;top:-22px;left:8px" }, "↑ mais rara, vale mais"));
    for (const v of [2, 3, 4, 5, 6, 7, 8]) {
      sc.append(h("div", { class: "tick", style: `top:${yOf(v)}%` }), h("div", { class: "tlabel", style: `top:${yOf(v)}%` }, `idf ${v}`));
    }
    sc.append(h("div", { class: "thr", style: `top:${yOf(THR)}%` }, h("span", {}, `daqui para cima: “palavra rara” (${dec(THR, 1)})`)));
    const pts = presets.slice();
    if (current && (current.kind === "ok" || current.kind === "approx") && !pts.some((p) => p.stem === current.stem)) pts.push(current);
    // O ponto fica na altura exata; só o rótulo desce um pouco quando dois ficam colados.
    const placed = pts.map((p) => ({ p, y: yOf(p.idf), ly: yOf(p.idf) })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < placed.length; i++) placed[i].ly = Math.max(placed[i].y, placed[i - 1].ly + 6);
    for (const { p, y, ly } of placed) {
      const on = current && p.stem === current.stem;
      sc.append(h("i", { class: on ? "dot on" : "dot", style: `top:${y}%` }),
        h("div", { class: on ? "pt on" : "pt", style: `top:${ly}%` }, `${p.word} · ${nf(p.df)} filmes`));
    }
  }
  function renderRarity() {
    const r = lookup($("#rarity-input").value);
    const card = $("#rarity-card");
    if (!r) { card.replaceChildren(h("p", { class: "small" }, "Digite uma palavra.")); renderScale(null); return; }
    if (r.kind === "stop") {
      card.replaceChildren(h("div", { class: "big" }, $("#rarity-input").value.trim(), " ", h("span", { class: "badge stop" }, "ignorada")),
        h("p", { class: "row" }, "É uma palavra comum, como “de”, “um” e “que”. Ela sai antes da busca e não vale nada."));
      renderScale(null); return;
    }
    if (r.kind === "none") {
      card.replaceChildren(h("div", { class: "big" }, $("#rarity-input").value.trim()),
        h("p", { class: "row" }, "Não está na lista: não aparece nos filmes, aparece em um só ou é nome de pessoa ou lugar."));
      renderScale(null); return;
    }
    const rare = r.idf >= THR;
    card.replaceChildren(
      h("div", { class: "big" }, r.kind === "approx" ? $("#rarity-input").value.trim() : r.word, " ",
        h("span", { class: rare ? "badge rare" : "badge common" }, rare ? "palavra rara" : "palavra comum")),
      h("p", { class: "row" }, "Aparece em ", h("strong", {}, `${nf(r.df)} de ${nf(N)} filmes`), ` (${pct(r.df / N)}).`),
      h("p", { class: "row" }, "Raiz da palavra: ", h("span", { class: "tok stem" }, r.stem),
        r.kind === "approx" ? h("span", { class: "small" }, ` (mesmo radical de “${r.word}”)`) : null),
      h("p", { class: "row" }, "Peso da raridade: ", h("strong", {}, dec(r.idf, 2))),
    );
    renderScale(r);
  }
  $("#rarity-presets").append(...presets.map((p) => h("button", {
    class: "chip", type: "button", onclick: () => { $("#rarity-input").value = p.word; renderRarity(); },
  }, p.word)));
  $("#rarity-input").addEventListener("input", renderRarity);
  renderRarity();

  // ---------- 5 · cosseno ----------
  const cosState = { q1: 3, q2: 2, d1: 4, d2: 1 };
  const W1 = "tubarão", W2 = "praia";
  const sliderDefs = [
    ["q1", `frase · “${W1}”`, ""], ["q2", `frase · “${W2}”`, ""],
    ["d1", `sinopse · “${W1}”`, "doc"], ["d2", `sinopse · “${W2}”`, "doc"],
  ];
  $("#cos-sliders").append(...sliderDefs.map(([k, lab, cls]) => {
    const out = h("span", { class: "num" }, cosState[k]);
    const inp = h("input", { type: "range", min: "0", max: "5", step: "0.5", value: cosState[k], "aria-label": lab });
    inp.addEventListener("input", () => { cosState[k] = Number(inp.value); out.textContent = inp.value.replace(".", ","); renderCos(); });
    return h("label", { class: `sl ${cls}` }, h("span", {}, lab), inp, out);
  }));
  function unit(a, b) { const n = Math.hypot(a, b); return n ? [a / n, b / n] : [0, 0]; }
  function renderCos() {
    const [q1, q2] = unit(cosState.q1, cosState.q2);
    const [d1, d2] = unit(cosState.d1, cosState.d2);
    const cos = q1 * d1 + q2 * d2;
    const ang = Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
    $("#cos-table").replaceChildren(h("table", {},
      h("tr", {}, h("th", {}, "palavra"), h("th", {}, "peso na frase"), h("th", {}, "peso na sinopse"), h("th", {}, "frase × sinopse")),
      h("tr", {}, h("td", {}, W1), h("td", {}, dec(q1)), h("td", {}, dec(d1)), h("td", {}, dec(q1 * d1))),
      h("tr", {}, h("td", {}, W2), h("td", {}, dec(q2)), h("td", {}, dec(d2)), h("td", {}, dec(q2 * d2))),
      h("tr", { class: "total" }, h("td", { colspan: "3" }, "soma = cosseno = pontuação"), h("td", {}, dec(cos))),
    ), h("p", { class: "small" }, "Os pesos são ajustados para cada seta ter tamanho 1. Assim, a soma das contribuições é exatamente a pontuação, e é essa conta que o FilmUSP mostra na tela."));
    const R = 260, ox = 50, oy = 310;
    const svg = $("#cos-svg");
    const p = (x, y) => `${ox + x * R},${oy - y * R}`;
    const a0 = Math.atan2(q2, q1), a1 = Math.atan2(d2, d1);
    const r = 70;
    const arc = `M ${p(Math.cos(a0) * r / R, Math.sin(a0) * r / R)} A ${r} ${r} 0 0 ${a1 > a0 ? 0 : 1} ${p(Math.cos(a1) * r / R, Math.sin(a1) * r / R)}`;
    svg.innerHTML = `
      <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs>
      <line x1="${ox}" y1="${oy}" x2="${ox + R + 20}" y2="${oy}" stroke="#5a5f6b" stroke-width="1.5"/>
      <line x1="${ox}" y1="${oy}" x2="${ox}" y2="${oy - R - 20}" stroke="#5a5f6b" stroke-width="1.5"/>
      <text x="${ox + R + 10}" y="${oy + 22}" font-size="15" text-anchor="end" fill="#333">${W1} →</text>
      <text x="${ox - 8}" y="${oy - R - 26}" font-size="15" fill="#333">↑ ${W2}</text>
      <path d="M ${p(1, 0)} A ${R} ${R} 0 0 0 ${p(0, 1)}" fill="none" stroke="#d4d9e2" stroke-dasharray="4 4"/>
      <path d="${arc}" fill="none" stroke="#ff8a00" stroke-width="3"/>
      <line x1="${ox}" y1="${oy}" x2="${p(q1, q2).split(",")[0]}" y2="${p(q1, q2).split(",")[1]}" stroke="#0b5fa5" stroke-width="5" marker-end="url(#ah)"/>
      <line x1="${ox}" y1="${oy}" x2="${p(d1, d2).split(",")[0]}" y2="${p(d1, d2).split(",")[1]}" stroke="#ff8a00" stroke-width="5" marker-end="url(#ah)"/>
      <text x="${ox + q1 * (R + 14)}" y="${oy - q2 * (R + 14)}" font-size="16" font-weight="700" fill="#0b5fa5">frase</text>
      <text x="${ox + d1 * (R + 14)}" y="${oy - d2 * (R + 14) + 16}" font-size="16" font-weight="700" fill="#b35f00">sinopse</text>
      <text x="${ox + 150}" y="${oy - 230}" font-size="20" font-weight="800" fill="#111">cos = ${dec(cos)}</text>
      <text x="${ox + 150}" y="${oy - 204}" font-size="15" fill="#333">ângulo ≈ ${Math.round(ang)}°</text>`;
  }
  renderCos();

  // ---------- 6 · explicabilidade ----------
  let exIdx = 0;
  function renderExplainFilm(j) {
    const ex = D.examples[exIdx];
    const hit = ex.hits[j];
    Array.from($("#explain-films").children).forEach((b, k) => b.setAttribute("aria-pressed", String(k === j)));
    $("#explain-left").innerHTML = hit.level1 + hit.level2;
    $("#explain-right").innerHTML = hit.level3;
  }
  function renderExplain(i) {
    exIdx = i;
    const ex = D.examples[i];
    const films = ex.hits.filter((x) => x.level1);
    $("#explain-films").replaceChildren(...films.map((hit, j) => {
      const m = movie(hit.movie_id);
      return h("button", { class: "film-btn", type: "button", "aria-pressed": "false", onclick: () => renderExplainFilm(j) },
        poster(m), h("span", {}, h("span", { class: "t" }, `${hit.rank}º · ${label(m)}`), h("span", { class: "s" }, `pontuação ${dec(hit.score)}`)));
    }));
    renderExplainFilm(0);
  }
  picker("explain", D.examples.map((e) => e.query), renderExplain);

  // ---------- 7 · significado ----------
  $("#emb-dim").textContent = M.embeddings.dimension;
  const colDefs = [
    ["tfidf", "Só palavras", "contando palavras iguais (TF-IDF)", ""],
    ["semantic", "Só sentido", "vetores de características", ""],
    ["hybrid", "FilmUSP", "os dois juntos", "hy"],
  ];
  const ord = (r) => (r ? `${r}º` : "fora dos 200 primeiros");
  function renderMeaning(i) {
    const c = D.meaning_cases[i];
    const target = c.target_id ? movie(c.target_id) : null;
    $("#meaning-cols").replaceChildren(...colDefs.map(([key, title, sub, cls]) => h("div", { class: `mcol ${cls}` },
      h("h4", {}, title), h("p", { class: "sub" }, sub),
      c.lists[key].map((id, k) => {
        const m = movie(id);
        return h("div", { class: id === c.target_id ? "mrow target" : "mrow" },
          h("span", { class: "r" }, `${k + 1}º`), poster(m), h("span", {}, label(m)));
      }),
      target ? h("div", { class: "mrank" }, `${target.title}: `, h("strong", {}, ord(c.target_rank[key]))) : null,
    )));
    const r = c.target_rank;
    let note = "";
    if (target) {
      const tf = r.tfidf || Infinity, se = r.semantic || Infinity, hy = r.hybrid || Infinity;
      if (se > hy && tf < se) note = `Aqui o sentido sozinho erra (${target.title} em ${ord(r.semantic)}), mas as palavras em comum seguram o filme no resultado do FilmUSP (${ord(r.hybrid)}). Por isso ele usa os dois.`;
      else if (tf > hy) note = `Só com palavras, ${target.title} fica em ${ord(r.tfidf)}: a frase descreve o filme sem usar as palavras da sinopse. Somando o sentido, ele sobe para ${ord(r.hybrid)}.`;
      else note = `${target.title}: ${ord(r.tfidf)} só com palavras, ${ord(r.semantic)} só com sentido e ${ord(r.hybrid)} no FilmUSP.`;
    }
    $("#meaning-note").textContent = note;
  }
  picker("meaning", D.meaning_cases.map((c) => c.query), renderMeaning);

  // ---------- 8 · RRF ----------
  const KCFG = M.config.semantic.rrf_k;
  const NCAND = M.config.semantic.candidates;
  $("#rrf-steps").append(
    h("div", { class: "rstep" }, h("b", {}, "1 · Sentido. "), `Sua frase vira um vetor, e os ${nf(NCAND)} filmes de sentido mais próximo entram na disputa.`),
    h("div", { class: "rstep" }, h("b", {}, "2 · Palavras. "), "Entre eles, o buscador confere quais sinopses usam as palavras da sua frase."),
    h("div", { class: "rstep" }, h("b", {}, "3 · Combinação. "), "Cada filme ganha pontos pela posição nas duas listas. Quem vai bem nas duas sobe."),
  );
  let rrfIdx = 0;
  const kInput = $("#rrf-k");
  kInput.value = String(KCFG);
  function rrfRank(cands, k) {
    return cands.map((c) => ({ ...c, rrf: 1 / (k + c.sem_rank) + (c.tf_rank ? 1 / (k + c.tf_rank) : 0) }))
      .sort((a, b) => (b.rrf - a.rrf) || (a.sem_rank - b.sem_rank));
  }
  function renderRRF() {
    const k = Number(kInput.value);
    $("#rrf-k-value").textContent = String(k);
    $("#rrf-k-note").textContent = `Com k pequeno, o topo de cada lista vale muito mais; com k grande, a disputa fica equilibrada. No FilmUSP, k = ${KCFG}.`;
    const ranked = rrfRank(D.rrf[rrfIdx].candidates, k).slice(0, 10);
    const head = h("tr", {}, h("th", {}, "#"), h("th", {}, "filme"), h("th", {}, "posição no sentido"), h("th", {}, "posição nas palavras"), h("th", {}, "pontos"), h("th", {}, "mudou"));
    $("#rrf-table").replaceChildren(head, ...ranked.map((c, i) => {
      const delta = c.sem_rank - (i + 1);
      const mv = delta > 0 ? h("span", { class: "mv up" }, `▲ ${delta}`) : delta < 0 ? h("span", { class: "mv down" }, `▼ ${-delta}`) : h("span", { class: "mv same" }, "=");
      return h("tr", {}, h("td", {}, `${i + 1}º`), h("td", { class: "title" }, label(movie(c.movie_id))),
        h("td", {}, `${c.sem_rank}º`), c.tf_rank ? h("td", {}, `${c.tf_rank}º`) : h("td", { class: "na" }, "—"),
        h("td", {}, dec(c.rrf, 4)), h("td", {}, mv));
    }), h("caption", {}, "— : a sinopse não tem nenhuma palavra da sua frase; o filme só ganha os pontos do sentido."));
  }
  kInput.addEventListener("input", renderRRF);
  picker("rrf", D.rrf.map((r) => r.query), (i) => { rrfIdx = i; renderRRF(); });
  window.__fuRRF = rrfRank; // usado pelo teste de conferência com o serviço

  // ---------- 9 · arquitetura ----------
  const boxes = [
    { id: "tmdb", x: 20, y: 40, w: 150, t: "TMDB", s: "catálogo de filmes",
      d: ["The Movie Database (TMDB)", "Um grande catálogo de filmes, aberto para consulta. De lá vêm título, sinopse em português, gêneros, elenco, nota e os pôsteres."] },
    { id: "collect", x: 200, y: 40, w: 170, t: "Coleta e filtros", s: "filmes em português",
      d: ["Coleta e filtros", `Dos ${nf(snap.candidates_tested)} filmes mais populares, ficam os que têm sinopse em português com pelo menos ${snap.filters.min_overview_words} palavras. Filmes adultos ficam de fora.`] },
    { id: "snapshot", x: 400, y: 40, w: 190, t: "Acervo congelado", s: `${nf(M.n_movies)} filmes`,
      d: ["Acervo congelado", `Os ${nf(M.n_movies)} filmes ficam guardados num arquivo e não mudam durante a feira. Assim, a mesma frase traz sempre os mesmos filmes.`] },
    { id: "tfidf", x: 400, y: 122, w: 190, t: "Índice de palavras", s: `${nf(D.vocabulary.n_terms_total)} palavras`,
      d: ["Índice de palavras (TF-IDF)", `Uma tabela que diz, para cada palavra, em quais filmes ela aparece e quanto ela vale. Conhece ${nf(D.vocabulary.n_terms_total)} palavras diferentes.`] },
    { id: "vectors", x: 190, y: 122, w: 190, t: "Vetores", s: `de características · ${M.embeddings.dimension}`,
      d: ["Vetores de características", `Um modelo de linguagem leu todas as sinopses, uma única vez, e transformou cada uma em ${M.embeddings.dimension} números que resumem o sentido do texto.`] },
    { id: "query", x: 20, y: 270, w: 140, t: "Sua frase", s: "do seu jeito",
      d: ["Sua frase", "Escrita do seu jeito, em português, com até 300 letras."] },
    { id: "cand", x: 190, y: 270, w: 190, t: "Pelo sentido", s: `${nf(NCAND)} candidatos`,
      d: ["Candidatos pelo sentido", `O mesmo modelo transforma a sua frase em vetor. O FilmUSP compara esse vetor com os ${nf(M.n_movies)} filmes e separa os ${nf(NCAND)} de sentido mais próximo.`] },
    { id: "score", x: 400, y: 270, w: 190, t: "Pelas palavras", s: "nota de cada filme",
      d: ["Pontuação pelas palavras", "Entre os candidatos, cada filme ganha uma nota pelas palavras que tem em comum com a sua frase. É essa nota que aparece na tela, com a conta explicada."] },
    { id: "rrf", x: 620, y: 270, w: 110, t: "Combinar", s: `RRF · k = ${KCFG}`,
      d: ["Combinação (RRF)", `Junta as duas listas: cada filme ganha pontos pela posição no sentido e pela posição nas palavras (k = ${KCFG}). Quem vai bem nas duas fica no topo.`] },
    { id: "ui", x: 748, y: 255, w: 142, t: "Tela", s: "com explicação",
      d: ["Tela do FilmUSP", "Pôsteres, detalhes do filme e a explicação em três níveis. Cores claras e letras grandes, para ler bem no projetor e no celular."] },
    { id: "log", x: 748, y: 350, w: 142, t: "Registro", s: "anônimo",
      d: ["Registro anônimo", "Cada busca é anotada sem nenhum dado pessoal: a frase, os filmes do topo e o tempo de resposta. Serve para entender como o público usa o buscador."] },
  ];
  const overview = ["Visão geral", `Duas etapas: preparar (uma vez só, antes da feira) e buscar (a cada frase). Uma busca leva cerca de 15 milésimos de segundo no notebook. Toque numa caixa para saber mais.`];
  const BH = 58;
  const svgArch = $("#arch-svg");
  const center = (b) => [b.x + b.w / 2, b.y + BH / 2];
  const edges = [["tmdb", "collect"], ["collect", "snapshot"], ["snapshot", "tfidf"], ["snapshot", "vectors"],
    ["query", "cand"], ["cand", "score"], ["score", "rrf"], ["rrf", "ui"], ["ui", "log"], ["vectors", "cand"], ["tfidf", "score"]];
  const B = Object.fromEntries(boxes.map((b) => [b.id, b]));
  function edgePath(a, b) {
    const A = B[a], C = B[b];
    if (a === "snapshot" && b === "vectors") return `M ${A.x + 30} ${A.y + BH} V 110 H ${C.x + C.w / 2} V ${C.y}`;
    if (A.y + BH <= C.y && Math.abs((A.x + A.w / 2) - (C.x + C.w / 2)) < 2) return `M ${A.x + A.w / 2} ${A.y + BH} V ${C.y}`;
    if (a === "ui" && b === "log") return `M ${A.x + A.w / 2} ${A.y + BH} L ${C.x + C.w / 2} ${C.y}`;
    return `M ${A.x + A.w} ${A.y + BH / 2} L ${C.x} ${C.y + BH / 2}`;
  }
  svgArch.innerHTML = `
    <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5a5f6b"/></marker></defs>
    <rect class="group" x="5" y="0" width="890" height="195" rx="14"/><text class="glabel" x="20" y="26">PREPARAR · UMA VEZ</text>
    <text class="glabel" x="630" y="150" style="font-weight:400;letter-spacing:0">Se o sentido falhar, a busca</text>
    <text class="glabel" x="630" y="168" style="font-weight:400;letter-spacing:0">continua só com as palavras.</text>
    <rect class="group" x="5" y="215" width="890" height="210" rx="14"/><text class="glabel" x="20" y="242">BUSCAR · A CADA FRASE</text>
    ${edges.map(([a, b]) => `<path d="${edgePath(a, b)}" fill="none" stroke="#5a5f6b" stroke-width="2" marker-end="url(#arr)"/>`).join("")}
    ${boxes.map((b) => `<g class="box" data-id="${b.id}" tabindex="0" role="button"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${BH}" rx="10"/>
      <text class="t" x="${b.x + 12}" y="${b.y + 24}">${b.t}</text><text class="s" x="${b.x + 12}" y="${b.y + 45}">${b.s}</text></g>`).join("")}`;
  // As caixas da linha de cima ficam acima do rótulo do grupo.
  function showArch(id) {
    const [t, d] = id ? B[id].d : overview;
    svgArch.querySelectorAll(".box").forEach((g) => g.classList.toggle("on", g.dataset.id === id));
    $("#arch-detail").replaceChildren(h("h4", {}, t), h("p", {}, d));
  }
  svgArch.querySelectorAll(".box").forEach((g) => {
    g.addEventListener("click", () => showArch(g.dataset.id));
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showArch(g.dataset.id); } });
  });
  showArch(null);

  // ---------- 10 · escolhas ----------
  const T = M.config;
  const choices = [
    ["Sempre o mesmo resultado", "A mesma frase traz sempre os mesmos filmes. Assim dá para repetir e explicar qualquer busca."],
    ["Feito para o português", "Maiúsculas e acentos não atrapalham, “de” e “um” não contam, e “assustador” e “assustadora” valem como a mesma palavra."],
    ["A conta sempre fecha", "Os pontos de cada palavra somam exatamente a pontuação que aparece na tela."],
    ["Explicação sempre à vista", "Três níveis ao mesmo tempo: quem só quer olhar vê os destaques; quem gosta de números vê a conta inteira."],
    ["Palavra rara tem regra", `O selo “palavra rara” segue uma regra fixa (peso a partir de ${dec(T.rare_idf_threshold, 1)}), e não um palpite.`],
    ["Modelo leve", "O modelo de linguagem roda no próprio notebook, sem depender da internet, e responde em milésimos de segundo."],
    ["Sentido ordena, palavras explicam", "O sentido ajuda a escolher a ordem dos filmes; a nota mostrada continua sendo a das palavras, para a explicação fechar a conta."],
    ["Nunca para", "Se o modelo de linguagem falhar, o FilmUSP continua funcionando só com as palavras."],
  ];
  $("#choices").append(...choices.map(([t, y]) => h("div", { class: "choice" },
    h("h4", {}, t), h("p", { class: "why" }, y))));

  $("#tmdb-final").textContent = `${M.tmdb_attribution}. Dados e pôsteres: The Movie Database (TMDB).`;

  // ---------- navegação ----------
  let cur = 0;
  const counter = $("#counter");
  const isFlow = () => window.innerWidth < 820 || (window.innerWidth < 1000 && window.innerHeight > window.innerWidth);
  function fit() {
    document.body.classList.toggle("flow-mode", isFlow());
    const s = Math.min(window.innerWidth / 1280, window.innerHeight / 720) * 0.96;
    document.documentElement.style.setProperty("--scale", String(s));
  }
  function go(i, push = true) {
    cur = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, j) => s.classList.toggle("active", j === cur));
    counter.textContent = `${cur + 1} / ${slides.length}`;
    if (push) history.replaceState(null, "", `#/${cur + 1}`);
  }
  function fromHash() { const m = location.hash.match(/^#\/(\d+)/); return m ? Number(m[1]) - 1 : 0; }
  document.addEventListener("keydown", (e) => {
    if (document.body.classList.contains("flow-mode")) return;
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" && e.target.type === "text") return;
    if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); go(cur + 1); }
    else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(cur - 1); }
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(slides.length - 1);
  });
  $("#prev").addEventListener("click", () => go(cur - 1));
  $("#next").addEventListener("click", () => go(cur + 1));
  let tx = null;
  document.addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (tx === null || document.body.classList.contains("flow-mode")) return;
    const dx = e.changedTouches[0].clientX - tx; tx = null;
    if (Math.abs(dx) > 60) go(cur + (dx < 0 ? 1 : -1));
  });
  window.addEventListener("hashchange", () => go(fromHash(), false));
  window.addEventListener("resize", fit);
  fit();
  go(fromHash(), false);
})();
