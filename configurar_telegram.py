"""Liga o robô do Telegram à prospecção na nuvem, sem o token passar por chat ou tela.

1. Crie o robô no @BotFather e COPIE o token (Ctrl+C).
2. Rode: .venv\\Scripts\\python.exe configurar_telegram.py
O token é lido da área de transferência (que é limpa em seguida), o chat é pareado com um código
de uso único e os dois viram Secrets do repositório (criptografados com a chave pública do GitHub).
"""
import base64
import json
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from nacl import encoding, public

REPO = "VictorHugodaSilvaSousa/prospeccao"


def api(url, data=None, token=None, metodo=None):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "prospeccao"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    corpo = json.dumps(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, corpo, h, method=metodo)
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read()
        return json.loads(txt) if txt else {}


def area_transferencia(limpar=False):
    cmd = "Set-Clipboard -Value $null" if limpar else "Get-Clipboard"
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def main():
    tg = area_transferencia()
    if not tg or ":" not in tg or " " in tg:
        sys.exit("Copie o token do @BotFather (Ctrl+C) e rode de novo.")
    base = f"https://api.telegram.org/bot{tg}"
    try:
        bot = api(f"{base}/getMe")["result"]["username"]
    except Exception:
        sys.exit("Token recusado pelo Telegram. Copie de novo do @BotFather.")
    area_transferencia(limpar=True)
    codigo = secrets.token_hex(4)
    print(f"Robô @{bot} ok. Abra no celular e toque em COMEÇAR:\n  https://t.me/{bot}?start={codigo}")
    chat, offset, fim = None, 0, time.time() + 300
    while not chat and time.time() < fim:
        for u in api(f"{base}/getUpdates?timeout=20&offset={offset}")["result"]:
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            if m.get("text") == f"/start {codigo}" and m["chat"]["type"] == "private":
                chat = str(m["chat"]["id"])
    if not chat:
        sys.exit("Não recebi o /start em 5 minutos. Rode de novo.")
    api(f"{base}/getUpdates?offset={offset}")  # confirma as mensagens lidas
    api(f"{base}/sendMessage", urllib.parse.urlencode(
        {"chat_id": chat, "text": "✅ Prospecção ligada. Os contatos novos chegam aqui segunda e quinta às 8h."}).encode())

    gh = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                        capture_output=True, text=True).stdout
    gh = next(l[9:] for l in gh.splitlines() if l.startswith("password="))
    url = f"https://api.github.com/repos/{REPO}/actions/secrets"
    chave = api(f"{url}/public-key", token=gh)
    caixa = public.SealedBox(public.PublicKey(chave["key"].encode(), encoding.Base64Encoder()))
    for nome, valor in (("TELEGRAM_TOKEN", tg), ("TELEGRAM_CHAT", chat)):
        cifrado = base64.b64encode(caixa.encrypt(valor.encode())).decode()
        api(f"{url}/{nome}", {"encrypted_value": cifrado, "key_id": chave["key_id"]}, gh, "PUT")
    print("Secrets TELEGRAM_TOKEN e TELEGRAM_CHAT gravados no GitHub. Pronto!")


if __name__ == "__main__":
    main()
