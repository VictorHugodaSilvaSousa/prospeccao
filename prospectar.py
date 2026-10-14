"""Acha negócios locais no OpenStreetMap e marca quais não têm site.

Uso:
    python prospectar.py barbearia "Brasília"
    python prospectar.py shop=bakery "Taguatinga, DF"
Gera prospeccao-<nicho>-<cidade>.xlsx com os sem site primeiro.
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from verificar import conferir

MODELO = Path(__file__).with_name("mensagem.txt")
UA ="prospeccao-local/1.0 (uso pessoal)"  # Nominatim exige User-Agent identificável
NICHOS = {
    "barbearia": '["shop"="hairdresser"]',
    "salao": '["shop"="hairdresser"]',
    "beleza": '["shop"="beauty"]',
    "padaria": '["shop"="bakery"]',
    "pizzaria": '["amenity"="restaurant"]["cuisine"~"pizza"]',
    "restaurante": '["amenity"="restaurant"]',
    "lanchonete": '["amenity"="fast_food"]',
    "cafe": '["amenity"="cafe"]',
    "academia": '["leisure"="fitness_centre"]',
    "dentista": '["amenity"="dentist"]',
    "clinica": '["amenity"="clinic"]',
    "petshop": '["shop"="pet"]',
    "veterinario": '["amenity"="veterinary"]',
    "oficina": '["shop"="car_repair"]',
    "roupas": '["shop"="clothes"]',
    "mercado": '["shop"="supermarket"]',
    "farmacia": '["amenity"="pharmacy"]',
}
SITE = ("website", "contact:website", "url")
SOCIAL = ("contact:instagram", "contact:facebook")
FONE = ("phone", "contact:phone", "contact:mobile", "contact:whatsapp")


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter")


def overpass(data):
    """Servidores públicos vivem lotados (429/504): tenta os espelhos, 2 voltas com pausa."""
    erro = None
    for volta in range(2):
        for url in OVERPASS:
            try:
                return get(url, data)
            except (urllib.error.URLError, TimeoutError) as ex:
                erro = ex
                print(f"  {url.split('/')[2]} falhou ({ex}); tentando outro...")
        time.sleep(30)
    raise erro


def filtro(nicho):
    if nicho in NICHOS:
        return NICHOS[nicho]
    if re.fullmatch(r"[\w:]+=[\w;:-]+", nicho):
        k, v = nicho.split("=")
        return f'["{k}"="{v}"]'
    sys.exit(f"Nicho desconhecido: {nicho}. Use um de {', '.join(NICHOS)} ou chave=valor do OSM.")


def area_id(cidade):
    q = urllib.parse.urlencode({"q": cidade, "format": "json", "limit": 5, "countrycodes": "br"})
    for r in get(f"https://nominatim.openstreetmap.org/search?{q}"):
        if r["osm_type"] == "relation":
            return 3600000000 + int(r["osm_id"]), r["display_name"]
    sys.exit(f"Cidade não encontrada como área: {cidade}")


def linha(tags):
    """Converte as tags OSM de um negócio numa linha da planilha."""
    pega = lambda ks: next((tags[k] for k in ks if tags.get(k)), "")
    end = ", ".join(p for p in (
        " ".join(p for p in (tags.get("addr:street", ""), tags.get("addr:housenumber", "")) if p),
        tags.get("addr:suburb", ""),
    ) if p)
    site = pega(SITE)
    return {
        "Nome": tags.get("name", ""),
        "Tem site": "sim" if site else "NÃO",
        "Site": site,
        "Rede social": pega(SOCIAL),
        "Telefone": pega(FONE),
        "Endereço": end,
        "Conferido": "",
    }


def celular(fones):
    """Primeiro celular BR (com 9 na frente) como 55DDD9XXXXXXXX; fixo não tem WhatsApp garantido."""
    for f in re.split(r"[;,/]", fones):
        d = re.sub(r"\D", "", f)
        d = d[2:] if d.startswith("55") and len(d) in (12, 13) else d.lstrip("0")
        if len(d) == 11 and d[2] == "9":
            return "55" + d
    return ""


def mensagem(modelo, l, nicho):
    return modelo.format(nome=l["Nome"], nicho=nicho)


def conferir_todos(linhas, cidade):
    with ThreadPoolExecutor(6) as ex:  # cada conferência espera rede; em paralelo leva segundos, não minutos
        list(ex.map(lambda l: conferir(l, cidade), linhas))


def buscar(nicho, cidade):
    """Retorna (nome da área, negócios ordenados com sem site e com WhatsApp primeiro)."""
    f = filtro(nicho)
    aid, nome = area_id(cidade)
    print(f"Buscando {nicho} em {nome}...")
    query = f"[out:json][timeout:170];area({aid})->.a;nwr{f}(area.a);out tags center;"
    data = urllib.parse.urlencode({"data": query}).encode()
    elementos = overpass(data)["elements"]
    linhas = [linha(e.get("tags", {})) for e in elementos if e.get("tags", {}).get("name")]
    modelo = open(MODELO, encoding="utf-8").read().strip()
    for l in linhas:
        cel = celular(l["Telefone"])
        l["Mensagem"] = mensagem(modelo, l, nicho)
        l["WhatsApp"] = f"https://wa.me/{cel}?text={urllib.parse.quote(l['Mensagem'])}" if cel else ""
        l["Status"] = ""
    linhas.sort(key=lambda l: (l["Tem site"] == "sim", not l["WhatsApp"], not l["Telefone"], l["Nome"]))
    return nome, linhas


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    nicho, cidade = sys.argv[1].lower(), sys.argv[2]
    nome, linhas = buscar(nicho, cidade)
    alvo = [l for l in linhas if l["Tem site"] == "NÃO" and l["WhatsApp"]]
    print(f"Conferindo se {len(alvo)} têm site de verdade...")
    conferir_todos(alvo, cidade)
    linhas.sort(key=lambda l: (l["Tem site"] == "sim", not l["WhatsApp"], not l["Telefone"], l["Nome"]))

    wb = Workbook()
    ws = wb.active
    ws.title = "Prospecção"
    cols = ["Nome", "Tem site", "WhatsApp", "Status", "Telefone", "Rede social", "Site", "Endereço", "Conferido",
            "Mensagem"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True)
    for l in linhas:
        ws.append([l[c] for c in cols])
        if l["WhatsApp"]:
            c = ws.cell(ws.max_row, 3, "Abrir conversa")
            c.hyperlink, c.style = l["WhatsApp"], "Hyperlink"
    for col, w in zip("ABCDEFGHIJ", (40, 10, 16, 14, 20, 30, 35, 45, 16, 80)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    slug = re.sub(r"\W+", "-", f"{nicho}-{cidade}".lower()).strip("-")
    arq = f"prospeccao-{slug}.xlsx"
    wb.save(arq)
    sem = sum(l["Tem site"] == "NÃO" for l in linhas)
    zap = sum(bool(l["WhatsApp"]) for l in linhas)
    print(f"{len(linhas)} negócios, {sem} sem site, {zap} com link de WhatsApp. Planilha: {arq}")
    pagina = Path(arq).with_suffix(".html").resolve()
    pagina.write_text(html_tabela(f"{nicho} — {nome}", linhas), encoding="utf-8")
    print(f"Página: {pagina.name}")
    webbrowser.open(pagina.as_uri())  # o PC pode não ter Excel; navegador sempre tem


def html_tabela(titulo, linhas):
    e = html.escape
    zap = lambda u: f'<a href="{e(u)}" target="_blank">WhatsApp</a>' if u else ""
    tr = "".join(
        f"<tr><td>{e(l['Nome'])}</td><td>{e(l['Tem site'])}</td><td>{zap(l['WhatsApp'])}</td>"
        f"<td>{e(l['Telefone'])}</td><td>{e(l['Rede social'])}</td><td>{e(l['Endereço'])}</td></tr>"
        for l in linhas
    )
    return f"""<!doctype html><meta charset="utf-8"><title>{e(titulo)}</title>
<style>body{{font-family:sans-serif;margin:16px}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee;position:sticky;top:0}}
a{{background:#25d366;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none}}</style>
<h2>{e(titulo)}</h2><p>{len(linhas)} negócios. Clique em WhatsApp para abrir a conversa com a mensagem pronta.</p>
<table><tr><th>Nome</th><th>Tem site</th><th>Contato</th><th>Telefone</th><th>Rede social</th><th>Endereço</th></tr>{tr}</table>"""


if __name__ == "__main__":
    main()
