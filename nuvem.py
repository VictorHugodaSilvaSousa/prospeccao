"""Roda na nuvem (GitHub Actions): busca os alvos de alvos.txt e manda no Telegram só os negócios novos.

Precisa das variáveis TELEGRAM_TOKEN e TELEGRAM_CHAT. Lembra o que já mandou em vistos.json.
"""
import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from prospectar import buscar

AQUI = Path(__file__).parent
VISTOS = AQUI / "vistos.json"


def alvos():
    for l in (AQUI / "alvos.txt").read_text(encoding="utf-8").splitlines():
        l = l.split("#")[0].strip()
        if l:
            nicho, cidade = (p.strip() for p in l.split("|"))
            yield nicho.lower(), cidade


def novos(linhas, vistos):
    """Só quem não tem site, tem WhatsApp e ainda não foi mandado; marca como visto."""
    saida = []
    for l in linhas:
        chave = l["Nome"] + "|" + l["Endereço"]
        if l["Tem site"] == "NÃO" and l["WhatsApp"] and chave not in vistos:
            vistos.add(chave)
            saida.append(l)
    return saida


def telegram(texto):
    token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT"]
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto, "parse_mode": "HTML",
                                    "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", dados, timeout=30)


def main():
    vistos = set(json.loads(VISTOS.read_text())) if VISTOS.exists() else set()
    total = falhas = 0
    for nicho, cidade in alvos():
        try:
            _, linhas = buscar(nicho, cidade)
        except Exception as ex:  # um alvo fora do ar não pode impedir os outros nem perder os já enviados
            falhas += 1
            print(f"::warning::{nicho} | {cidade} falhou: {ex}")
            continue
        lista = novos(linhas, vistos)
        total += len(lista)
        print(f"{nicho} | {cidade}: {len(lista)} novos")  # sem nomes: o log do Actions pode ser público
        for i in range(0, len(lista), 5):  # ~600 caracteres por item (link longo); limite do Telegram é 4096
            itens = "\n\n".join(
                f"<b>{html.escape(l['Nome'])}</b>\n{html.escape(l['Endereço'])}\n"
                f"<a href=\"{html.escape(l['WhatsApp'])}\">Abrir WhatsApp com a mensagem</a>"
                for l in lista[i:i + 5])
            telegram(f"🧭 <b>{len(lista)} novos: {html.escape(nicho)} em {html.escape(cidade)}</b>\n\n{itens}")
        time.sleep(2)  # política de uso do Nominatim/Overpass: sem rajadas
    print(f"Total: {total} novos, {falhas} alvos com falha")
    VISTOS.write_text(json.dumps(sorted(vistos), ensure_ascii=False))
    if falhas and not total:
        sys.exit(1)


if __name__ == "__main__":
    main()
