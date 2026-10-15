"""Fonte opcional: Google Places API (New), Text Search. Só roda com GOOGLE_PLACES_KEY.

Uso oficial (sem raspar o Maps). Termos do Google: não guardar o conteúdo por muito tempo; por isso
o robô só guarda o ID do lugar (permitido) e manda os contatos direto no Telegram.
Custo: cada página de até 20 lugares é 1 requisição; o Google dá uma cota gratuita mensal.
Defina um limite de cota no Google Cloud para nunca passar do grátis.
"""
import json
import os
import urllib.request

CAMPOS = ",".join(f"places.{c}" for c in (
    "id", "displayName", "formattedAddress", "nationalPhoneNumber", "internationalPhoneNumber",
    "websiteUri", "businessStatus")) + ",nextPageToken"
REDES = ("instagram.com", "facebook.com", "fb.com", "linktr.ee", "wa.me", "whatsapp.com", "tiktok.com",
         "ifood.com.br", "linkedin.com", "youtube.com", "goo.gl", "g.page", "business.site")


def e_rede_social(url):
    """Muito negócio põe o Instagram no campo 'site' do Google: isso NÃO é site próprio."""
    return any(r in url.lower() for r in REDES)


def linha_google(p):
    url = p.get("websiteUri", "")
    social = e_rede_social(url) if url else False
    return {
        "Nome": p.get("displayName", {}).get("text", ""),
        "Tem site": "sim" if url and not social else "NÃO",
        "Site": "" if social else url,
        "Rede social": url if social else "",
        "Telefone": p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber", ""),
        "Endereço": p.get("formattedAddress", "").replace(", Brasil", ""),
        "Conferido": "Google",
        "Fonte": "Google",
        "Id": "g:" + p["id"],
    }


def buscar_google(texto, paginas=3):
    """Até 60 lugares (3 páginas de 20). Fechados de vez ficam de fora."""
    chave = os.environ.get("GOOGLE_PLACES_KEY")
    if not chave:
        return []
    saida, token = [], None
    for _ in range(paginas):
        corpo = {"textQuery": texto, "languageCode": "pt-BR", "regionCode": "BR", "pageSize": 20}
        if token:
            corpo["pageToken"] = token
        req = urllib.request.Request(
            "https://places.googleapis.com/v1/places:searchText", json.dumps(corpo).encode(),
            {"Content-Type": "application/json", "X-Goog-Api-Key": chave, "X-Goog-FieldMask": CAMPOS})
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = json.load(r)
        saida += [linha_google(p) for p in dados.get("places", [])
                  if p.get("businessStatus") != "CLOSED_PERMANENTLY" and p.get("displayName")]
        token = dados.get("nextPageToken")
        if not token:
            break
    return saida
