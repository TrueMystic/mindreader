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
def year_of(e, p):
    for v in claims(e, p):
        t = v.get("time", "") if isinstance(v, dict) else ""
        if len(t) > 5:
            try: return int(t[:t.index("-", 1)])
            except Exception: pass
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
def place_groups(type_labels):
    g = set()
    for lb in type_labels:
        l = lb.lower()
        for code, kws in PLACE:
            if any(k in l for k in kws): g.add(code)
    if g & {"church", "mosque", "temple"}: g.add("religious")
    return sorted(g)

def main():
    os.makedirs("data", exist_ok=True)
    big = int(os.environ.get("BIG_SL", "90"))
    cis = int(os.environ.get("CIS_SL", "25"))
    plc = int(os.environ.get("PLACE_SL", "55"))

    people = candidates(f"""SELECT ?x ?sl WHERE {{ ?x wdt:P31 wd:Q5 . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {big}) }}""", "people(world)")
    people_cis = candidates(f"""SELECT ?x ?sl WHERE {{ VALUES ?c {{ wd:Q159 wd:Q184 wd:Q232 wd:Q212 wd:Q15180 wd:Q34266 }}
        ?x wdt:P31 wd:Q5 . ?x wdt:P27 ?c . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {cis}) }}""", "people(cis)")
    people.update(people_cis)
    places = candidates(f"""SELECT ?x ?sl WHERE {{ VALUES ?root {{ wd:Q811979 wd:Q4989906 wd:Q570116 }}
        ?x wdt:P31/wdt:P279* ?root . ?x wikibase:sitelinks ?sl . FILTER(?sl >= {plc}) }}""", "places")
    # не здания (страны, города и т.п.) отсекаем позже по наличию типа

    # Главный источник — популярные статьи Википедии (кого реально ищут люди)
    pop = entities_by_titles(top_titles())
    pe = {k: e for k, e in pop.items() if "Q5" in ids_of(e, "P31")}
    pl_pop = {k: e for k, e in pop.items() if "Q5" not in ids_of(e, "P31")}
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
    for k, e in pe.items():
        if "missing" in e: continue
        ru, en = lab(e, "ru"), lab(e, "en")
        if not (ru or en): continue
        g = ids_of(e, "P21")
        gender = "m" if "Q6581097" in g or "Q2449503" in g else ("f" if "Q6581072" in g or "Q1052281" in g else None)
        occ = occ_groups([lab(aux.get(o, {}), "en") for o in ids_of(e, "P106")])
        cs = [c for c in (country(c) for c in ids_of(e, "P27")) if c]
        img = claims(e, "P18")
        out_people.append({
            "id": k, "n": ru or en, "e": en or ru, "d": desc(e, "ru") or desc(e, "en"),
            "i": img[0] if img else None, "s": len(e.get("sitelinks", {})) or people.get(k, 0),
            "g": gender, "b": year_of(e, "P569"), "dd": year_of(e, "P570"),
            "c": cs[:3], "o": occ,
        })

    out_places = []
    for k, e in pl.items():
        if "missing" in e: continue
        ru, en = lab(e, "ru"), lab(e, "en")
        if not (ru or en): continue
        types = place_groups([lab(aux.get(t, {}), "en") for t in ids_of(e, "P31")])
        if not types: continue
        cs = [c for c in (country(c) for c in ids_of(e, "P17")) if c]
        img = claims(e, "P18")
        h = amount(e, "P2048")
        out_places.append({
            "id": k, "n": ru or en, "e": en or ru, "d": desc(e, "ru") or desc(e, "en"),
            "i": img[0] if img else None, "s": len(e.get("sitelinks", {})) or places.get(k, 0),
            "c": cs[:1], "t": types, "y": year_of(e, "P571"), "h": round(h) if h else None,
        })

    # континенты — подписи
    cont_ids = {v["ct"] for v in countries.values() if v.get("ct")}
    ce = entities(cont_ids, props="labels", langs="ru|en") if cont_ids else {}
    continents = {k: {"ru": lab(v, "ru"), "en": lab(v, "en")} for k, v in ce.items()}

    out_people.sort(key=lambda x: -x["s"]); out_places.sort(key=lambda x: -x["s"])
    meta = {"countries": countries, "continents": continents}
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
