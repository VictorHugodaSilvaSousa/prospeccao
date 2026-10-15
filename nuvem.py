"""Roda na nuvem (GitHub Actions): busca os alvos de alvos.txt e manda no Telegram só os negócios novos.

Precisa de TELEGRAM_TOKEN e TELEGRAM_CHAT; opcionais GOOGLE_PLACES_KEY, BRAVE_API_KEY e
PROSPECCAO_LIMITE (contatos por dia, padrão 15; o resto fica para o próximo dia).
Lembra o que já mandou em vistos.json, só pelo ID do lugar (os termos do Google só permitem guardar o ID).
"""
import datetime
import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from prospectar import buscar, conferir_todos, e_lead

AQUI = Path(__file__).parent
VISTOS = AQUI / "vistos.json"


def alvos():
    lista = []
    for l in (AQUI / "alvos.txt").read_text(encoding="utf-8").splitlines():
        l = l.split("#")[0].strip()
        if l:
            nicho, cidade = (p.strip() for p in l.split("|"))
            lista.append((nicho.lower(), cidade))
    if not lista:
        return []
    k = datetime.date.today().toordinal() % len(lista)  # cada dia começa por um nicho diferente
    return lista[k:] + lista[:k]


def novos(linhas, vistos, cidade="", nicho="", limite=10**9, conferir=conferir_todos):
    """Até `limite` contatos novos que valem abordar (sem site ou site com problema).
    Os conferidos viram 'vistos' (até quem tem site ok, para não gastar busca de novo);
    os que não couberam no limite ficam para o próximo dia."""
    saida = []
    fila = [l for l in linhas if l["WhatsApp"] and l["Id"] not in vistos]
    while fila and len(saida) < limite:
        lote, fila = fila[:limite - len(saida)], fila[limite - len(saida):]
        conferir(lote, cidade, nicho)
        for l in lote:
            vistos.add(l["Id"])
        saida += [l for l in lote if e_lead(l)]
    return saida


def telegram(texto):
    token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT"]
    dados = urllib.parse.urlencode({"chat_id": chat, "text": texto, "parse_mode": "HTML",
                                    "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", dados, timeout=30)


def item(l):
    e = html.escape
    linhas = [f"<b>{e(l['Nome'])}</b>", e(l["Endereço"])]
    if l.get("Problema"):
        linhas.append(f"🔧 Tem site, mas {e(l['Problema'])}: {e(l['Site'])}")
    elif l["Site"].startswith("talvez"):
        linhas.append(f"⚠️ Confira antes: {e(l['Site'])}")
    if l["Rede social"]:
        linhas.append(e(l["Rede social"]))
    linhas.append(f"<a href=\"{e(l['WhatsApp'])}\">Abrir WhatsApp com a mensagem</a>")
    return "\n".join(linhas)


def main():
    vistos = set(json.loads(VISTOS.read_text())) if VISTOS.exists() else set()
    limite = int(os.environ.get("PROSPECCAO_LIMITE") or 15)
    total, falhas = 0, []
    for nicho, cidade in alvos():
        if total >= limite:
            break  # não gasta busca (nem cota do Google) depois de bater o limite do dia
        try:
            _, linhas = buscar(nicho, cidade)
        except Exception as ex:  # um alvo fora do ar não pode impedir os outros nem perder os já enviados
            falhas.append(f"{nicho} | {cidade}")
            print(f"::warning::{nicho} | {cidade} falhou: {ex}")
            continue
        lista = novos(linhas, vistos, cidade, nicho, limite - total)
        total += len(lista)
        print(f"{nicho} | {cidade}: {len(lista)} novos")  # sem nomes: o log do Actions pode ser público
        for i in range(0, len(lista), 5):  # ~650 caracteres por item (link longo); limite do Telegram é 4096
            itens = "\n\n".join(item(l) for l in lista[i:i + 5])
            telegram(f"🧭 <b>{len(lista)} novos: {html.escape(nicho)} em {html.escape(cidade)}</b>\n\n{itens}")
        time.sleep(2)  # política de uso do Nominatim/Overpass: sem rajadas
    print(f"Total: {total} novos, {len(falhas)} alvos com falha")
    VISTOS.write_text(json.dumps(sorted(vistos), ensure_ascii=False))
    if falhas:
        telegram("⚠️ Prospecção: não consegui buscar " + ", ".join(html.escape(f) for f in falhas)
                 + ". Tento de novo no próximo dia.")
    if falhas and not total:
        sys.exit(1)


if __name__ == "__main__":
    main()
