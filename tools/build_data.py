"""Сборка базы для игры «Угадай, кого я загадал» из Wikidata.
Запускается на GitHub Actions (там есть интернет), результат — data/people.json, data/places.json.
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = "MindReaderGame/1.0 (https://truemystic.github.io/mindreader/)"
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

def get(url, data=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/sparql-results+json, application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            log("  retry", i + 1, type(e).__name__, str(e)[:160])
            time.sleep(5 * (i + 1))
    raise RuntimeError("failed: " + url[:200])

PFX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
"""

def sparql(q):
    q = PFX + q
    for name, ep in [("qlever", "https://qlever.cs.uni-freiburg.de/api/wikidata"), ("wdqs", "https://query.wikidata.org/sparql")]:
        try:
            url = ep + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
            j = get(url, tries=2)
            rows = j["results"]["bindings"]
            log("  sparql via", name, "rows:", len(rows))
            if rows: return rows
        except Exception as e:
            log("  sparql", name, "failed:", str(e)[:200])
    return []

def qid(uri): return uri.rsplit("/", 1)[-1]

def candidates(q, label):
    rows = sparql(q)
    out = {}
    for r in rows:
        k = qid(r["x"]["value"]); sl = int(float(r["sl"]["value"]))
        out[k] = max(out.get(k, 0), sl)
    log(label, "candidates:", len(out))
    return out

def entities(ids, props="labels|descriptions|claims|sitelinks", langs="ru|en"):
    res = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(chunk), "props": props, "languages": langs, "format": "json"})
        j = get(url)
        res.update(j.get("entities", {}))
        if i % 1000 == 0: log("  entities", i, "/", len(ids))
        time.sleep(0.2)
    return res

def top_titles():
    """Самые читаемые статьи ru/en Википедии за последние 12 месяцев."""
    import datetime
    views = {}
    d = datetime.date.today().replace(day=1)
    months = []
    for _ in range(12):
        d = (d - datetime.timedelta(days=1)).replace(day=1); months.append(d)
    for wiki in ["ru", "en"]:
        for m in months:
            url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{wiki}.wikipedia/all-access/{m.year}/{m.month:02d}/all-days"
            try:
                j = get(url, tries=2)
                for a in j["items"][0]["articles"]:
                    t = a["article"]
                    if ":" in t or t in ("Main_Page", "Заглавная_страница", "-"): continue
                    views[(wiki, t)] = views.get((wiki, t), 0) + a["views"]
            except Exception as e:
                log("  pageviews fail", wiki, m, str(e)[:100])
    log("top titles:", len(views))
    return views

def entities_by_titles(views):
    res = {}
    for wiki in ["ru", "en"]:
        titles = [t for (w, t) in views if w == wiki]
        for i in range(0, len(titles), 50):
            chunk = titles[i:i + 50]
            url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
                "action": "wbgetentities", "sites": wiki + "wiki", "titles": "|".join(t.replace("_", " ") for t in chunk),
                "props": "labels|descriptions|claims|sitelinks", "languages": "ru|en", "format": "json"})
            try:
                j = get(url)
                for k, e in j.get("entities", {}).items():
                    if k.startswith("Q") and "missing" not in e: res[k] = e
            except Exception as e:
                log("  titles fail", str(e)[:100])
            time.sleep(0.2)
        log("  resolved", wiki, "→ entities total", len(res))
    return res

def lab(e, lang):
    return (e.get("labels", {}).get(lang) or {}).get("value", "")
def desc(e, lang):
    return (e.get("descriptions", {}).get(lang) or {}).get("value", "")
def claims(e, p):
    out = []
    for c in e.get("claims", {}).get(p, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if v is not None: out.append(v)
    return out
def ids_of(e, p): return [v["id"] for v in claims(e, p) if isinstance(v, dict) and "id" in v]
def ids_ranked(e, p):
    cs = [c for c in e.get("claims", {}).get(p, []) if c.get("rank") != "deprecated"]
    cs.sort(key=lambda c: 0 if c.get("rank") == "preferred" else 1)
    out = []
    for c in cs:
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "id" in v: out.append(v["id"])
    return out
def year_of(e, p):
    for v in claims(e, p):
        t = v.get("time", "") if isinstance(v, dict) else ""
        if len(t) > 5:
            try: return int(t[:t.index("-", 1)])
            except Exception: pass
    return None
def height_cm(e):
    for v in claims(e, "P2048"):
        try:
            a = float(v["amount"]); u = v.get("unit", "")
            if u.endswith("Q174728"): return round(a)
            if u.endswith("Q11573"): return round(a * 100)
        except Exception: pass
    return None
def max_amount(e, p):
    best = None
    for v in claims(e, p):
        try: a = float(v["amount"]); best = a if best is None else max(best, a)
        except Exception: pass
    return best
AWARDS = [("oscar", ["academy award"]), ("grammy", ["grammy"]), ("nobel", ["nobel prize"]), ("ballon", ["ballon d'or"]),
          ("globe", ["golden globe"]), ("emmy", ["emmy award"]), ("hero", ["hero of the soviet union", "hero of the russian federation", "hero of socialist labour"]),
          ("knight", ["knight", "order of the british empire", "dame"])]
HAIR = [("blond", ["blond", "fair"]), ("red", ["red hair", "ginger", "auburn"]), ("bald", ["bald"]), ("grey", ["grey", "gray", "white hair"]), ("dark", ["black", "brown", "dark"])]
EYES = [("blue", ["blue", "grey", "gray"]), ("green", ["green", "hazel"]), ("brown", ["brown", "black", "dark"])]
def pick(labels, table):
    for lb in labels:
        l = lb.lower()
        for code, kws in table:
            if any(k in l for k in kws): return code
    return None
def amount(e, p):
    for v in claims(e, p):
        try: return float(v["amount"])
        except Exception: pass
    return None

# Группы профессий: ключевые слова в английском названии профессии → код
OCC = [
    ("actor", ["actor", "actress"]), ("singer", ["singer", "vocalist"]), ("rapper", ["rapper", "hip hop"]),
    ("musician", ["musician", "guitarist", "pianist", "drummer", "composer", "disc jockey", "record producer", "songwriter"]),
    ("director", ["film director", "filmmaker", "film producer", "screenwriter"]),
    ("football", ["association football player", "footballer"]), ("basketball", ["basketball player"]),
    ("tennis", ["tennis player"]), ("hockey", ["ice hockey player"]), ("boxer", ["boxer"]),
    ("fighter", ["mixed martial artist", "martial artist", "wrestler", "judoka", "kickboxer"]),
    ("racer", ["racing driver", "racecar driver", "formula one driver"]), ("chess", ["chess player"]),
    ("athlete", ["athlete", "swimmer", "sprinter", "gymnast", "skater", "cyclist", "golfer", "baseball", "american football", "volleyball", "skier", "sport"]),
    ("politician", ["politician", "diplomat", "statesperson", "statesman"]),
    ("monarch", ["monarch", "king", "queen", "emperor", "empress", "pharaoh", "tsar", "sultan"]),
    ("military", ["military", "general", "officer", "soldier", "admiral", "commander"]),
    ("scientist", ["physicist", "chemist", "mathematician", "biologist", "scientist", "astronomer", "inventor", "engineer", "economist", "psychologist", "computer scientist"]),
    ("writer", ["writer", "novelist", "poet", "playwright", "author", "journalist"]),
    ("business", ["businessperson", "entrepreneur", "business executive", "investor", "chief executive"]),
    ("blogger", ["youtuber", "blogger", "streamer", "influencer", "internet celebrity", "vlogger", "tiktoker"]),
    ("tv", ["television presenter", "talk show host", "comedian", "radio personality", "humorist"]),
    ("model", ["model"]), ("artist", ["painter", "sculptor", "visual artist", "artist", "architect", "photographer", "illustrator"]),
    ("philosopher", ["philosopher", "theologian"]), ("religious", ["priest", "pope", "religious", "prophet", "saint", "bishop", "monk", "rabbi", "imam"]),
    ("cosmonaut", ["astronaut", "cosmonaut"]), ("dancer", ["dancer", "ballet"]),
]
def occ_groups(occ_labels):
    g = set()
    for lb in occ_labels:
        l = lb.lower()
        for code, kws in OCC:
            if any(k in l for k in kws): g.add(code)
    if g & {"football", "basketball", "tennis", "hockey", "boxer", "fighter", "racer", "chess"}: g.add("athlete")
    if g & {"rapper"}: g.add("singer")
    if g & {"singer", "rapper"}: g.add("musician")
    return sorted(g)

# Типы зданий/мест
PLACE = [
    ("tower", ["tower"]), ("bridge", ["bridge"]), ("skyscraper", ["skyscraper"]),
    ("church", ["church", "cathedral", "basilica", "chapel", "abbey", "monastery"]), ("mosque", ["mosque"]),
    ("temple", ["temple", "shrine", "pagoda", "stupa", "synagogue"]),
    ("palace", ["palace", "royal residence", "official residence"]), ("castle", ["castle", "fortress", "fort", "citadel", "kremlin"]),
    ("stadium", ["stadium", "arena", "sports venue", "circuit"]), ("museum", ["museum", "gallery"]),
    ("statue", ["statue", "monument", "memorial", "sculpture", "colossal"]), ("pyramid", ["pyramid"]),
    ("theatre", ["theatre", "opera house", "concert hall"]), ("dam", ["dam"]), ("wall", ["wall"]),
    ("square", ["square", "plaza"]), ("park", ["park", "garden"]), ("ruins", ["ruins", "archaeological site", "ancient"]),
    ("lighthouse", ["lighthouse"]), ("airport", ["airport"]), ("station", ["railway station", "station"]),
    ("tomb", ["tomb", "mausoleum", "necropolis"]), ("hotel", ["hotel", "casino"]), ("government", ["parliament", "capitol", "legislature", "city hall", "government building"]),
]
PLACE_TYPES = {
  "tower": ["Q12518","Q11166728","Q1440300"], "skyscraper": ["Q11303"], "bridge": ["Q12280","Q537127","Q1825472","Q158218"],
  "church": ["Q16970","Q2977","Q163687","Q44613","Q108325","Q56242215","Q1088552"], "mosque": ["Q32815"],
  "temple": ["Q44539","Q842402","Q5393308","Q34627","Q845945"], "palace": ["Q16560","Q53536964"],
  "castle": ["Q23413","Q57821","Q1785071","Q88291"], "stadium": ["Q483110","Q641226"], "museum": ["Q33506","Q207694","Q17431399"],
  "statue": ["Q179700","Q4989906","Q5003624","Q575759","Q860861"], "pyramid": ["Q12516"], "theatre": ["Q24354","Q153562","Q1060829"],
  "dam": ["Q12323"], "wall": ["Q42948","Q57346"], "square": ["Q174782"], "park": ["Q22698","Q46169","Q1107656"],
  "ruins": ["Q839954","Q109607","Q15661340"], "lighthouse": ["Q39715"], "airport": ["Q1248784","Q644371"],
  "station": ["Q55488","Q928830","Q18543139"], "tomb": ["Q381885","Q162875"], "hotel": ["Q27686","Q133215"],
  "government": ["Q16831714","Q543654"],
  "mountain": ["Q8502"], "volcano": ["Q8072","Q169358"], "waterfall": ["Q34038"], "lake": ["Q23397"], "canyon": ["Q150784"],
  "island": ["Q23442"], "river": ["Q4022"], "desert": ["Q8514"], "glacier": ["Q35666"], "cave": ["Q35509"], "reef": ["Q184358"], "beach": ["Q40080"],
}
NATURE = {"mountain","volcano","waterfall","lake","canyon","island","river","desert","glacier","cave","reef","beach"}
TYPE2G = {q: g for g, qs in PLACE_TYPES.items() for q in qs}
def place_groups_q(type_ids):
    g = {TYPE2G[t] for t in type_ids if t in TYPE2G}
    if g & {"church", "mosque", "temple"}: g.add("religious")
    if g & NATURE: g.add("nature")
    return sorted(g)

def place_groups(type_labels):
    g = set()
    for lb in type_labels:
        l = lb.lower()
        for code, kws in PLACE:
            if any(k in l for k in kws): g.add(code)
    if g & {"church", "mosque", "temple"}: g.add("religious")
    return sorted(g)

def trim(people, places):
    """Ужимаем базу для телефона: убираем малоизвестное и лишние поля."""
    people = [p for p in people if p["s"] >= 20]
    people.sort(key=lambda x: -x["s"]); people = people[:7000]
    for p in people:
        p["d"] = (p.get("d") or "")[:70]
        if p.get("e") == p.get("n"): p.pop("e", None)
        for k in ("o2", "c", "aw", "tm"):
            if not p.get(k): p.pop(k, None)
        p.pop("id", None)
    skip = {"airport", "station"}
    places = [x for x in places if x["s"] >= 30 and not (set(x["t"]) & skip and len(set(x["t"]) - skip - {"religious", "nature"}) == 0)]
    places.sort(key=lambda x: -x["s"]); places = places[:2500]
    for x in places:
        x["t"] = [t for t in x["t"] if t not in skip]
        x["d"] = (x.get("d") or "")[:70]
        if x.get("e") == x.get("n"): x.pop("e", None)
        x.pop("id", None)
    return people, places

def main():
    os.makedirs("data", exist_ok=True)
    big = int(os.environ.get("BIG_SL", "90"))
    cis = int(os.environ.get("CIS_SL", "25"))
    plc = int(os.environ.get("PLACE_SL", "55"))

    people = candidates(f"""SELECT ?x ?sl WHERE {{ ?x wdt:P31 wd:Q5 . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {big}) }}""", "people(world)")
    people_cis = candidates(f"""SELECT ?x ?sl WHERE {{ VALUES ?c {{ wd:Q159 wd:Q184 wd:Q232 wd:Q212 wd:Q15180 wd:Q34266 }}
        ?x wdt:P31 wd:Q5 . ?x wdt:P27 ?c . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {cis}) }}""", "people(cis)")
    people.update(people_cis)
    places = {}
    for g, qs in PLACE_TYPES.items():
        vals = " ".join("wd:" + q for q in qs)
        lim = 40 if g in NATURE else 25
        places.update(candidates(f"""SELECT ?x ?sl WHERE {{ VALUES ?t {{ {vals} }} ?x wdt:P31 ?t . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {lim}) }}""", "places:" + g))
    log("places total:", len(places))
    COUNTRY_BATCHES = [
        "Q30 Q145 Q174193 Q179876 Q16", "Q142 Q70972 Q71084 Q183 Q43287 Q7318 Q27306 Q41304", "Q38 Q172579 Q29 Q80702 Q55 Q31 Q39 Q40 Q28513",
        "Q36 Q213 Q218 Q28 Q34 Q20 Q35 Q33 Q27 Q45 Q41", "Q1747689 Q17167 Q2277 Q11772 Q12548 Q12560 Q43", "Q148 Q8733 Q17 Q188712 Q668 Q884 Q794 Q79 Q801",
        "Q96 Q155 Q414 Q298 Q739 Q408 Q664 Q258 Q1033 Q115", "Q15180 Q159 Q34266 Q212 Q184 Q232 Q265 Q230 Q399 Q227"]
    for batch in COUNTRY_BATCHES:
        vals = " ".join("wd:" + q for q in batch.split())
        people.update(candidates(f"""SELECT ?x ?sl WHERE {{ VALUES ?c {{ {vals} }} ?x wdt:P27 ?c . ?x wdt:P31 wd:Q5 . ?x wikibase:sitelinks ?sl . FILTER(?sl >= 70) }}""", "people:" + batch[:20]))
    # не здания (страны, города и т.п.) отсекаем позже по наличию типа

    # Главный источник — популярные статьи Википедии (кого реально ищут люди)
    pop = entities_by_titles(top_titles())
    pe = {k: e for k, e in pop.items() if "Q5" in ids_of(e, "P31")}
    pl_pop = {k: e for k, e in pop.items() if "Q5" not in ids_of(e, "P31") and place_groups_q(ids_of(e, "P31"))}
    log("popular: people", len(pe), "other", len(pl_pop))
    extra_p = [k for k in people if k not in pe]
    if extra_p:
        log("fetching extra people:", len(extra_p)); pe.update(entities(extra_p))
    extra_pl = [k for k in places if k not in pl_pop]
    pl = dict(pl_pop)
    if extra_pl:
        log("fetching extra places:", len(extra_pl)); pl.update(entities(extra_pl))

    aux_ids = set()
    for e in pe.values():
        aux_ids.update(ids_of(e, "P106")); aux_ids.update(ids_of(e, "P27"))
        for pp in ("P166", "P1884", "P1340", "P1344"): aux_ids.update(ids_of(e, pp))
        aux_ids.update(ids_ranked(e, "P54")[:6])
    for e in pl.values():
        aux_ids.update(ids_of(e, "P31")); aux_ids.update(ids_of(e, "P17"))
    log("fetching aux labels:", len(aux_ids))
    aux = entities(aux_ids, props="labels|claims", langs="ru|en")

    countries = {}
    def country(cid):
        if cid in countries: return cid
        e = aux.get(cid)
        if not e: return None
        conts = ids_of(e, "P30")
        countries[cid] = {"ru": lab(e, "ru") or lab(e, "en"), "en": lab(e, "en"), "ct": conts[0] if conts else None}
        return cid

    out_people = []
    teams = {}
    for k, e in pe.items():
        if "missing" in e: continue
        ru, en = lab(e, "ru"), lab(e, "en")
        if not (ru or en): continue
        g = ids_of(e, "P21")
        gender = "m" if "Q6581097" in g or "Q2449503" in g else ("f" if "Q6581072" in g or "Q1052281" in g else None)
        occ_ids = ids_ranked(e, "P106")
        occ = occ_groups([lab(aux.get(o, {}), "en") for o in occ_ids[:2]])
        occ2 = [x for x in occ_groups([lab(aux.get(o, {}), "en") for o in occ_ids[2:]]) if x not in occ]
        cs = [c for c in (country(c) for c in ids_of(e, "P27")) if c]
        img = claims(e, "P18")
        rec = {
            "id": k, "n": ru or en, "e": en or ru, "d": (desc(e, "ru") or desc(e, "en"))[:90],
            "i": img[0] if img else None, "s": len(e.get("sitelinks", {})) or people.get(k, 0),
            "g": gender, "b": year_of(e, "P569"), "dd": year_of(e, "P570"),
            "c": cs[:3], "o": occ, "o2": occ2,
        }
        # «неожиданные» признаки для вопросов в стиле Акинатора
        aw = sorted({c for c in (pick([lab(aux.get(a, {}), "en")], AWARDS) for a in ids_of(e, "P166")) if c})
        if any("olympic" in lab(aux.get(x, {}), "en").lower() for x in ids_of(e, "P1344")): aw.append("olympic")
        if aw: rec["aw"] = aw
        sp = len(ids_of(e, "P26"))
        if sp: rec["sp"] = sp
        ch = max_amount(e, "P1971") or len(ids_of(e, "P40"))
        if ch: rec["ch"] = int(ch)
        if "Q789447" in ids_of(e, "P552"): rec["lh"] = 1
        elif ids_of(e, "P552"): rec["lh"] = 0
        hr = pick([lab(aux.get(x, {}), "en") for x in ids_of(e, "P1884")], HAIR)
        if hr: rec["hr"] = hr
        ey = pick([lab(aux.get(x, {}), "en") for x in ids_of(e, "P1340")], EYES)
        if ey: rec["ey"] = ey
        h = height_cm(e)
        if h and 120 < h < 240: rec["h"] = h
        fol = max_amount(e, "P8687")
        if fol: rec["fol"] = round(fol / 1e6, 1)
        if "P2003" in e.get("claims", {}): rec["ig"] = 1
        tm = [t for t in ids_ranked(e, "P54")[:6] if t in aux]
        if tm:
            rec["tm"] = tm
            for t in tm: teams[t] = lab(aux[t], "ru") or lab(aux[t], "en")
        out_people.append(rec)

    out_places = []
    for k, e in pl.items():
        if "missing" in e: continue
        ru, en = lab(e, "ru"), lab(e, "en")
        if not (ru or en): continue
        types = place_groups_q(ids_of(e, "P31"))
        if not types: continue
        cs = [c for c in (country(c) for c in ids_of(e, "P17")) if c]
        img = claims(e, "P18")
        h = amount(e, "P2048") or amount(e, "P2044")
        out_places.append({
            "id": k, "n": ru or en, "e": en or ru, "d": (desc(e, "ru") or desc(e, "en"))[:90],
            "i": img[0] if img else None, "s": len(e.get("sitelinks", {})) or places.get(k, 0),
            "c": cs[:1], "t": types, "y": year_of(e, "P571"), "h": round(h) if h else None,
        })

    # континенты — подписи
    cont_ids = {v["ct"] for v in countries.values() if v.get("ct")}
    ce = entities(cont_ids, props="labels", langs="ru|en") if cont_ids else {}
    continents = {k: {"ru": lab(v, "ru"), "en": lab(v, "en")} for k, v in ce.items()}

    out_people, out_places = trim(out_people, out_places)
    meta = {"countries": countries, "continents": continents, "teams": teams}
    for name, obj in [("people", out_people), ("places", out_places), ("meta", meta)]:
        with open(f"data/{name}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    log("DONE people:", len(out_people), "places:", len(out_places), "countries:", len(countries))

if __name__ == "__main__":
    try:
        main()
    finally:
        os.makedirs("data", exist_ok=True)
        with open("data/build_log.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(LOG))
