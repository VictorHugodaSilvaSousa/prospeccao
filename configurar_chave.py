"""Cadastra uma chave opcional (Google Places ou Brave) na nuvem e no PC, sem ela passar por chat ou tela.

1. Copie a chave (Ctrl+C) no painel do Google Cloud ou do Brave.
2. Rode: .venv\\Scripts\\python.exe configurar_chave.py google   (ou: brave)
A chave é testada, vira Secret do repositório, vai para o .env local (fora do git) e a área de transferência é limpa.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from configurar_telegram import area_transferencia, gravar_secrets

NOMES = {"google": "GOOGLE_PLACES_KEY", "brave": "BRAVE_API_KEY"}


def testar(qual, chave):
    if qual == "google":
        req = urllib.request.Request(
            "https://places.googleapis.com/v1/places:searchText",
            json.dumps({"textQuery": "padaria em Brasília", "pageSize": 1}).encode(),
            {"Content-Type": "application/json", "X-Goog-Api-Key": chave, "X-Goog-FieldMask": "places.id"})
    else:
        q = urllib.parse.urlencode({"q": "padaria Brasília", "count": 1})
        req = urllib.request.Request(f"https://api.search.brave.com/res/v1/web/search?{q}",
                                     headers={"X-Subscription-Token": chave, "Accept": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except urllib.error.HTTPError as ex:
        sys.exit(f"A chave foi recusada ({ex.code}): {ex.read()[:300].decode('utf-8', 'ignore')}")


def main():
    qual = (sys.argv[1:] or [""])[0].lower()
    if qual not in NOMES:
        sys.exit(__doc__)
    chave = area_transferencia()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{20,80}", chave or ""):
        sys.exit("Copie a chave (Ctrl+C) e rode de novo.")
    testar(qual, chave)
    area_transferencia(limpar=True)
    nome = NOMES[qual]
    gravar_secrets({nome: chave})
    env = Path(__file__).with_name(".env")
    linhas = [l for l in (env.read_text(encoding="utf-8").splitlines() if env.exists() else [])
              if not l.startswith(nome + "=")]
    env.write_text("\n".join(linhas + [f"{nome}={chave}"]) + "\n", encoding="utf-8")
    print(f"{nome} testada e gravada (GitHub + .env local). Pronto!")


if __name__ == "__main__":
    main()
