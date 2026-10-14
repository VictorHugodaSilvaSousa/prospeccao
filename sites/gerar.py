"""Gera sites estáticos a partir de sites/clientes/*.json em sites/publicado/<slug>/.

Uso: python sites/gerar.py
Segurança: só HTML+CSS (sem JS, formulário ou banco), todo texto escapado, links montados
pelo gerador (nunca copiados do JSON) e CSP que bloqueia qualquer recurso de fora.
Enquanto "aprovado" for false, o site sai com faixa de PRÉVIA e noindex (não aparece no Google).
"""
import html
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

AQUI = Path(__file__).parent
SAIDA = AQUI / "publicado"
FOTO_OK = {".jpg", ".jpeg", ".png", ".webp"}


def digitos_celular(fone):
    d = re.sub(r"\D", "", fone)
    d = d[2:] if d.startswith("55") and len(d) in (12, 13) else d
    if not (len(d) == 11 and d[2] == "9"):
        raise ValueError(f"WhatsApp inválido (use DDD + celular): {fone}")
    return "55" + d


def validar(c):
    for campo in ("nome", "slug", "whatsapp", "endereco"):
        if not str(c.get(campo, "")).strip():
            raise ValueError(f"Campo obrigatório vazio: {campo}")
    if not re.fullmatch(r"[a-z0-9-]{3,40}", c["slug"]):
        raise ValueError("slug só com letras minúsculas, números e hífen")
    if c.get("instagram") and not re.fullmatch(r"[A-Za-z0-9._]{1,30}", c["instagram"]):
        raise ValueError("instagram: só o @usuario, sem link")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", c.get("cor", "#1f6feb")):
        raise ValueError("cor deve ser no formato #rrggbb")
    digitos_celular(c["whatsapp"])


def pagina(c, fotos):
    e = lambda s: html.escape(str(s))
    zap = f"https://wa.me/{digitos_celular(c['whatsapp'])}?text=" + urllib.parse.quote(
        f"Olá, {c['nome']}! Vim pelo site e gostaria de mais informações.")
    mapa = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(c["endereco"])
    servicos = "".join(
        f"<li><span>{e(s['nome'])}</span><b>{e(s.get('preco', ''))}</b></li>" for s in c.get("servicos", []))
    horarios = "".join(f"<li><span>{e(d)}</span><b>{e(h)}</b></li>" for d, h in c.get("horarios", {}).items())
    galeria = "".join(f'<img src="fotos/{e(f)}" alt="Foto de {e(c["nome"])}" loading="lazy">' for f in fotos)
    insta = (f'<a href="https://instagram.com/{e(c["instagram"])}" rel="noopener noreferrer">@{e(c["instagram"])}</a>'
             if c.get("instagram") else "")
    previa = not c.get("aprovado", False)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
{'<meta name="robots" content="noindex, nofollow">' if previa else ''}
<title>{e(c['nome'])}{' — ' + e(c['slogan']) if c.get('slogan') else ''}</title>
<meta name="description" content="{e(c.get('descricao', c['nome']))}">
<link rel="stylesheet" href="estilo.css">
</head>
<body>
{'<div class="previa">PRÉVIA — site em aprovação pelo estabelecimento</div>' if previa else ''}
<header class="topo">
  <h1>{e(c['nome'])}</h1>
  {f"<p class='slogan'>{e(c['slogan'])}</p>" if c.get('slogan') else ''}
  <a class="botao" href="{e(zap)}" rel="noopener noreferrer">Chamar no WhatsApp</a>
</header>
<main>
  {f"<section><p class='sobre'>{e(c['descricao'])}</p></section>" if c.get('descricao') else ''}
  {f"<section><h2>Serviços</h2><ul class='lista'>{servicos}</ul></section>" if servicos else ''}
  {f"<section><h2>Fotos</h2><div class='galeria'>{galeria}</div></section>" if galeria else ''}
  {f"<section><h2>Horários</h2><ul class='lista'>{horarios}</ul></section>" if horarios else ''}
  <section>
    <h2>Onde estamos</h2>
    <p>{e(c['endereco'])}</p>
    <a class="botao secundario" href="{e(mapa)}" rel="noopener noreferrer">Ver no mapa</a>
  </section>
</main>
<footer>
  <p>{e(c['nome'])} · {insta}</p>
</footer>
</body>
</html>
"""


CSS = """:root{--cor:%s;--texto:#1d1d1f;--suave:#6e6e73;--fundo:#fff;--cartao:#f5f5f7}
@media (prefers-color-scheme:dark){:root{--texto:#f5f5f7;--suave:#a1a1a6;--fundo:#111;--cartao:#1d1d1f}}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--texto);background:var(--fundo);line-height:1.6}
.previa{background:#ffd60a;color:#000;text-align:center;padding:8px;font-weight:600}
.topo{background:var(--cor);color:#fff;text-align:center;padding:72px 16px 56px}
.topo h1{margin:0;font-size:clamp(2rem,6vw,3.2rem);letter-spacing:-.02em}.slogan{margin:8px 0 28px;opacity:.9;font-size:1.15rem}
main{max-width:760px;margin:0 auto;padding:8px 16px 48px}section{margin-top:40px}h2{font-size:1.4rem;margin:0 0 16px}
.sobre{font-size:1.1rem;color:var(--suave)}
.lista{list-style:none;padding:0;margin:0;background:var(--cartao);border-radius:14px}
.lista li{display:flex;justify-content:space-between;gap:16px;padding:14px 18px;border-bottom:1px solid rgba(128,128,128,.2)}.lista li:last-child{border:0}
.galeria{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}.galeria img{width:100%%;aspect-ratio:1;object-fit:cover;border-radius:12px}
.botao{display:inline-block;background:#25d366;color:#fff;font-weight:600;padding:14px 26px;border-radius:999px;text-decoration:none}
.botao:focus-visible{outline:3px solid #fff;outline-offset:3px}.secundario{background:var(--cor)}
footer{text-align:center;color:var(--suave);padding:24px 16px;border-top:1px solid rgba(128,128,128,.2)}footer a{color:inherit}
"""


def gerar(arq):
    c = json.loads(arq.read_text(encoding="utf-8"))
    validar(c)
    destino = SAIDA / c["slug"]
    shutil.rmtree(destino, ignore_errors=True)
    (destino / "fotos").mkdir(parents=True)
    fotos = []
    pasta_fotos = arq.with_suffix("")  # clientes/<arquivo>/ com as fotos, opcional
    if pasta_fotos.is_dir():
        for f in sorted(pasta_fotos.iterdir()):
            if f.suffix.lower() in FOTO_OK and f.stat().st_size < 3_000_000:
                shutil.copy(f, destino / "fotos" / f.name)
                fotos.append(f.name)
    (destino / "index.html").write_text(pagina(c, fotos), encoding="utf-8")
    (destino / "estilo.css").write_text(CSS % c.get("cor", "#1f6feb"), encoding="utf-8")
    return destino


def main():
    erros = 0
    for arq in sorted((AQUI / "clientes").glob("*.json")):
        try:
            print(f"OK  {arq.name} -> {gerar(arq).relative_to(AQUI)}")
        except (ValueError, KeyError, json.JSONDecodeError) as ex:
            erros += 1
            print(f"ERRO {arq.name}: {ex}")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
