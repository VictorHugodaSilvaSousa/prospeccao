"""Confere se um negócio tem mesmo site (o OpenStreetMap quase nunca tem esse dado).

1. Domínio provável: nomedonegocio.com.br/.com.
2. Busca no Brave Search, se BRAVE_API_KEY estiver definida (aproveita o Instagram que aparecer).
Um candidato só vale como "sim" com prova local (telefone ou endereço na página); só o nome = "talvez".
"""
import json
import os
import re
import socket
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

GENERICOS = {"barbearia", "barber", "barbershop", "shop", "salao", "studio", "espaco", "restaurante", "bar",
             "lanchonete", "pizzaria", "academia", "fitness", "padaria", "clinica", "pet", "loja", "store",
             "cafe", "the", "de", "da", "do", "das", "dos", "e", "ltda", "me", "eireli", "and", "o", "a"}
END_COMUNS = {"quadra", "bloco", "loja", "lote", "conjunto", "casa", "sala", "rua", "avenida", "setor", "plano",
              "piloto", "norte", "brasilia", "distrito", "federal", "centro", "comercial", "shopping", "chacara",
              "area", "especial", "residencial", "vila", "jardim", "parque", "sobreloja", "terreo", "edificio"}
DIRETORIOS = ("instagram.", "facebook.", "ifood.", "google.", "tripadvisor.", "guiamais.", "apontador.",
              "booksy.", "linkedin.", "wikipedia.", "yelp.", "waze.", "youtube.", "tiktok.", "twitter.", "x.com",
              "kekanto.", "restaurantguru.", "cnpj", "econodata.", "solutudo.", "telelistas.", "wa.me",
              "whatsapp.", "trinks.", "agendaedu.", "gympass.", "totalpass.", "rappi.", "aiqfome.", "99app.",
              "mercadolivre.", "olx.", "reclameaqui.", "foursquare.", "listamais.", "encontra")
UA = "Mozilla/5.0 (compatible; prospeccao-local/1.0)"
_brave = threading.Lock()


def normal(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", s)


def chaves(nome):
    """Palavras que identificam o negócio (sem 'barbearia', 'de' etc.)."""
    return [p for p in normal(nome) if p not in GENERICOS and len(p) >= 4]


def e_do_negocio(url, nome):
    host = urllib.parse.urlsplit(url).hostname or ""
    if any(d in host or d in url for d in DIRETORIOS):
        return False
    rotulo = "".join(normal(host.removeprefix("www.").split(".")[0]))
    ks = chaves(nome)
    return bool(ks) and all(k in rotulo for k in ks)


def baixar(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read(500_000).decode("utf-8", "ignore")
    except Exception:
        return ""


def prova_local(texto, l):
    """O site é DESTE negócio? Nome igual não basta (achamos transportadora e restaurante na Itália):
    precisa ter o telefone ou pelo menos 2 palavras do endereço."""
    digitos = re.sub(r"\D", "", texto)
    for f in re.split(r"[;,/]", l.get("Telefone", "")):
        d = re.sub(r"\D", "", f)
        if len(d) >= 8 and d[-8:] in digitos:
            return True
    palavras = set(normal(texto))
    end = [p for p in normal(l.get("Endereço", ""))
           if len(p) >= 4 and not p.isdigit() and p not in GENERICOS | END_COMUNS]
    return len(end) >= 2 and sum(p in palavras for p in set(end)) >= 2


def classificar(url, l):
    """'sim' com prova local, 'talvez' quando o site cita o nome mas não prova que é daqui, '' se não é."""
    texto = baixar(url)
    if not texto:
        return ""
    if prova_local(texto, l):
        return "sim"
    ks = chaves(l["Nome"])
    palavras = set(normal(texto))
    return "talvez" if ks and all(k in palavras for k in ks) else ""


def dominio_provavel(nome):
    base = "".join(normal(nome))
    if len(base) < 5:
        return []
    saida = []
    for dom in (f"{base}.com.br", f"{base}.com"):
        try:
            socket.getaddrinfo(dom, 443)
            saida.append(f"https://{dom}")
        except OSError:
            pass
    return saida


def brave(nome, cidade):
    """(sites candidatos, instagram) achados na busca; ([], "") sem chave ou sem resultado."""
    chave = os.environ.get("BRAVE_API_KEY")
    if not chave:
        return [], ""
    q = urllib.parse.urlencode({"q": f'"{nome}" {cidade}', "country": "BR", "search_lang": "pt-br", "count": 10})
    req = urllib.request.Request(f"https://api.search.brave.com/res/v1/web/search?{q}",
                                 headers={"X-Subscription-Token": chave, "Accept": "application/json"})
    with _brave:  # o plano de créditos aceita 1 busca por segundo
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                urls = [x["url"] for x in json.load(r).get("web", {}).get("results", [])]
        except Exception as ex:
            print(f"  busca falhou ({ex})")
            return [], ""
        finally:
            time.sleep(1.1)
    sites = [u for u in urls if e_do_negocio(u, nome)][:3]
    insta = next((u for u in urls if re.match(r"https://(www\.)?instagram\.com/[A-Za-z0-9._]+/?$", u)
                  and not re.search(r"\.com/(p|reel|explore|stories|accounts)/?$", u)), "")
    return sites, insta


def conferir(l, cidade):
    """Preenche no dict do negócio: Tem site ('sim' só com prova), Site, Conferido e Rede social."""
    talvez = ""
    candidatos, insta = dominio_provavel(l["Nome"]), ""
    for etapa in (0, 1):
        if etapa == 1:  # só gasta busca se o domínio provável não resolveu
            candidatos, insta = brave(l["Nome"], cidade)
        for url in candidatos:
            r = classificar(url, l)
            if r == "sim":
                l["Site"], l["Tem site"] = url, "sim"
                break
            talvez = talvez or (url if r == "talvez" else "")
        if l["Tem site"] == "sim":
            break
    if talvez and l["Tem site"] != "sim":
        l["Site"] = f"talvez: {talvez}"
    if insta and not l["Rede social"]:
        l["Rede social"] = insta
    l["Conferido"] = "domínio + busca" if os.environ.get("BRAVE_API_KEY") else "só domínio"
    return l
