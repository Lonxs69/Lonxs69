"""Retoca el SVG de github-profile-3d-contrib:
- una ola de luz recorre el calendario 3D en bucle (antes solo crecía una vez al cargar)
- un barrido gira sobre el radar
- la dona de lenguajes se rehace con los bytes de código de los repos públicos
Solo usa la librería estándar de Python."""
import json, math, os, re, sys, urllib.request
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
Q = lambda tag: f"{{{NS}}}{tag}"

SRC = sys.argv[1]
LABELS = {"Shell": "Bash"}
MAX_LANGS = 9

tree = ET.parse(SRC)
root = tree.getroot()
parent = {c: p for p in root.iter() for c in p}

def translate_of(el):
    m = re.match(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)", el.get("transform", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)

# ---------------------------------------------------------------- ola del calendario
tiles = []
for g in root.iter(Q("g")):
    rects = [c for c in g if c.tag == Q("rect")]
    if len(rects) == 3 and (rects[0].get("class") or "").startswith("cont-top-"):
        x, y = translate_of(g)
        h = float(rects[1].get("height"))
        base_y = y + h * 1.15  # pie de la columna, sin la altura
        tiles.append((g, (x / 20 + base_y / 11.547) / 2))

if tiles:
    lo = min(t for _, t in tiles)
    hi = max(t for _, t in tiles)
    for g, t in tiles:
        delay = f"{(t - lo) / ((hi - lo) or 1) * 3.2:.2f}s"
        kids = [c for c in g if c.tag != Q("animateTransform")]
        wave = ET.Element(Q("g"), {"class": "wv", "style": f"animation-delay:{delay}"})
        for c in kids:
            g.remove(c)
            wave.append(c)
        top = kids[0]
        wave.append(ET.Element(Q("rect"), {
            "x": "0", "y": "0", "width": top.get("width"), "height": top.get("height"),
            "transform": top.get("transform"), "class": "gl", "style": f"animation-delay:{delay}"}))
        g.append(wave)

# ---------------------------------------------------------------- barrido del radar
radar = next((p for p in root.iter(Q("polygon")) if p.get("class") == "radar"), None)
if radar is not None:
    ET.SubElement(radar, Q("animateTransform"), {
        "attributeName": "transform", "type": "scale", "values": "1;1.06;1",
        "dur": "4s", "begin": "3s", "repeatCount": "indefinite"})
    rp = parent[radar]
    r = 156
    a = math.radians(40)
    sweep = ET.Element(Q("g"))
    ET.SubElement(sweep, Q("path"), {
        "d": f"M0 0L{r} 0A{r} {r} 0 0 0 {r * math.cos(a):.1f} {-r * math.sin(a):.1f}Z",
        "fill": "#8b5cf6", "fill-opacity": "0.2"})
    ET.SubElement(sweep, Q("line"), {"x1": "0", "y1": "0", "x2": str(r), "y2": "0",
                                     "stroke": "#c4b5fd", "stroke-width": "2", "stroke-opacity": "0.8"})
    ET.SubElement(sweep, Q("animateTransform"), {
        "attributeName": "transform", "type": "rotate", "values": "0;360",
        "dur": "6s", "repeatCount": "indefinite"})
    rp.insert(list(rp).index(radar), sweep)

# ---------------------------------------------------------------- dona de lenguajes
def fetch_languages():
    token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("USERNAME")
    if not token or not user:
        return []
    query = ('query($u:String!){user(login:$u){repositories(ownerAffiliations:OWNER,isFork:false,'
             'privacy:PUBLIC,first:100){nodes{languages(first:20){edges{size node{name color}}}}}}}')
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": query, "variables": {"u": user}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    totals = {}
    for repo in data["data"]["user"]["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            size, color = totals.get(n, (0, e["node"]["color"] or "#8b88a8"))
            totals[n] = (size + e["size"], color)
    return sorted(((n, s, c) for n, (s, c) in totals.items()), key=lambda x: -x[1])[:MAX_LANGS]

try:
    langs = fetch_languages()
except Exception as exc:  # si falla la API se deja la dona original
    print("lenguajes: sin datos,", exc)
    langs = []

pie = next((g for g in root.iter(Q("g")) if g.get("transform") == "translate(130, 130)"
            and any(p.tag == Q("path") for p in g)), None)
if langs and pie is not None:
    box = parent[pie]
    for c in list(box):
        box.remove(c)
    total = sum(s for _, s, _ in langs)
    R, r = 117, 65
    donut = ET.SubElement(box, Q("g"), {"transform": "translate(130, 130)"})
    spin = ET.SubElement(donut, Q("g"))
    ang = -math.pi / 2
    for name, size, color in langs:
        da = 2 * math.pi * size / total
        a0, a1 = ang, ang + da
        big = 1 if da > math.pi else 0
        p = lambda rad, a: f"{rad * math.cos(a):.2f},{rad * math.sin(a):.2f}"
        d = f"M{p(R, a0)}A{R},{R},0,{big},1,{p(R, a1)}L{p(r, a1)}A{r},{r},0,{big},0,{p(r, a0)}Z"
        path = ET.SubElement(spin, Q("path"), {"d": d, "style": f"fill: {color};", "class": "stroke-bg",
                                               "stroke-width": "2px"})
        ET.SubElement(path, Q("title")).text = f"{LABELS.get(name, name)} {size * 100 / total:.1f}%"
        ang = a1
    ET.SubElement(spin, Q("animateTransform"), {
        "attributeName": "transform", "type": "rotate", "values": "0;360",
        "dur": "40s", "repeatCount": "indefinite"})
    step = 26
    legend = ET.SubElement(box, Q("g"), {"transform": "translate(273, 0)"})
    y0 = 130 - step * len(langs) / 2
    for i, (name, size, color) in enumerate(langs):
        y = y0 + i * step
        ET.SubElement(legend, Q("rect"), {"x": "0", "y": f"{y + 4:.1f}", "width": "16", "height": "16",
                                          "rx": "3", "style": f"fill: {color};"})
        t = ET.SubElement(legend, Q("text"), {"dominant-baseline": "middle", "x": "26", "y": f"{y + 12:.1f}",
                                              "class": "fill-fg", "font-size": "19px"})
        t.text = LABELS.get(name, name)
        pct = ET.SubElement(legend, Q("text"), {"dominant-baseline": "middle", "x": "150", "y": f"{y + 12:.1f}",
                                                "class": "fill-weak", "font-size": "17px"})
        pct.text = f"{size * 100 / total:.1f}%"

# ---------------------------------------------------------------- estilos
style = root.find(Q("style"))
style.text = (style.text or "") + """
.wv { animation: wv 6s ease-in-out infinite both; }
@keyframes wv { 0%, 14%, 100% { transform: translateY(0); } 7% { transform: translateY(-9px); } }
.gl { fill: #d8ccff; opacity: 0; animation: gl 6s ease-in-out infinite both; }
@keyframes gl { 0%, 14%, 100% { opacity: 0; } 7% { opacity: 0.6; } }
"""

tree.write(SRC, encoding="unicode")
print(f"ok: {len(tiles)} casillas, {len(langs)} lenguajes")
