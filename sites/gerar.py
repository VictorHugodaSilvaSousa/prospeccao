"""Gera sites estáticos a partir de sites/clientes/*.json em sites/publicado/<slug>/.

Uso: python sites/gerar.py
Segurança: só HTML+CSS (sem JS, formulário ou banco), todo texto escapado, links montados
pelo gerador (nunca copiados do JSON) e CSP que bloqueia qualquer recurso de fora.
Enquanto "aprovado" for false, o site sai com faixa de PRÉVIA e noindex (não aparece no Google).
"""
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

AQUI = Path(__file__).parent
SAIDA = AQUI / "publicado"
FOTO_OK = {".jpg", ".jpeg", ".png", ".webp"}
BASE = os.environ.get("SITE_BASE", "").rstrip("/")  # ex.: https://usuario.github.io/prospeccao (o workflow define)
ZAP_SVG = ('<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22"><path fill="currentColor" d="M12 2a10 '
           '10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 '
           '8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 '
           '1-3.3-2.9c-.3-.4.2-.4.7-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 '
           '2.2 5.2 5.2 0 0 0 1.1 2.8 11.9 11.9 0 0 0 4.6 4c1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.5'
           '-.3z"/></svg>')
PIN_SVG = ('<svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2a7 7 '
           '0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>')


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


def texto_sobre(cor):
    """Preto ou branco, o que tiver mais contraste com a cor da marca (WCAG)."""
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#111111" if (lum + 0.05) / 0.05 > 1.05 / (lum + 0.05) else "#ffffff"


def pagina(c, fotos):
    e = lambda s: html.escape(str(s))
    nome = c["nome"]
    zap = f"https://wa.me/{digitos_celular(c['whatsapp'])}?text=" + urllib.parse.quote(
        f"Olá, {nome}! Vim pelo site e gostaria de mais informações.")
    mapa = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{nome}, {c['endereco']}")
    previa = not c.get("aprovado", False)

    destaques = "".join(f"<li>{e(d)}</li>" for d in c.get("destaques", []))
    def servico(s):
        desc = f"<p>{e(s['desc'])}</p>" if s.get("desc") else ""
        preco = f"<span class='preco'>{e(s['preco'])}</span>" if s.get("preco") else ""
        return f"<article class='servico'><div><h3>{e(s['nome'])}</h3>{desc}</div>{preco}</article>"

    servicos = "".join(servico(s) for s in c.get("servicos", []))
    horarios = "".join(f"<li><span>{e(d)}</span><b>{e(h)}</b></li>" for d, h in c.get("horarios", {}).items())
    galeria = "".join(f'<img src="fotos/{e(f)}" alt="Foto de {e(nome)}" loading="lazy" decoding="async">'
                      for f in fotos)
    depoimentos = "".join(
        f"<figure class='depo'><blockquote>“{e(d['texto'])}”</blockquote><figcaption>{e(d['autor'])}</figcaption></figure>"
        for d in c.get("depoimentos", []))
    insta = (f'<a href="https://instagram.com/{e(c["instagram"])}" rel="noopener noreferrer">Instagram @{e(c["instagram"])}</a>'
             if c.get("instagram") else "")
    credito = f"<p class='credito'>Site feito por {e(c['credito'])}</p>" if c.get("credito") else ""
    faq = "".join(f"<details><summary>{e(f['pergunta'])}</summary><p>{e(f['resposta'])}</p></details>"
                  for f in c.get("faq", []))
    url = f"{BASE}/{c['slug']}/" if BASE else ""
    meta_url = (f'<link rel="canonical" href="{e(url)}">\n<meta property="og:url" content="{e(url)}">'
                + (f'\n<meta property="og:image" content="{e(url)}fotos/{e(fotos[0])}">' if fotos else "")) if url else ""
    ld = json.dumps({"@context": "https://schema.org", "@type": c.get("tipo_schema", "LocalBusiness"), "name": nome,
                     "description": c.get("descricao", ""), "telephone": "+" + digitos_celular(c["whatsapp"]),
                     "address": c["endereco"]}, ensure_ascii=False).replace("<", "\\u003c")
    secao = lambda id_, titulo, corpo, extra="": (
        f"<section id='{id_}' class='secao {extra}'><h2>{titulo}</h2>{corpo}</section>" if corpo else "")
    nav = "".join(f"<a href='#{i}'>{t}</a>" for i, t, ok in (
        ("servicos", "Serviços", servicos), ("fotos", "Fotos", galeria), ("horarios", "Horários", horarios),
        ("local", "Como chegar", True)) if ok)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
{'<meta name="robots" content="noindex, nofollow">' if previa else ''}
<title>{e(nome)}{' | ' + e(c['slogan']) if c.get('slogan') else ''}</title>
<meta name="description" content="{e(c.get('descricao', nome))}">
<meta property="og:title" content="{e(nome)}">
<meta property="og:description" content="{e(c.get('slogan') or c.get('descricao', ''))}">
<meta name="theme-color" content="{e(c.get('cor', '#1f6feb'))}">
{meta_url}
<link rel="icon" href="data:image/svg+xml,{urllib.parse.quote(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='{c.get('cor', '#1f6feb')}'/><text x='32' y='44' font-size='34' font-family='sans-serif' font-weight='700' text-anchor='middle' fill='{texto_sobre(c.get('cor', '#1f6feb'))}'>{e(nome[:1].upper())}</text></svg>")}">
<link rel="stylesheet" href="estilo.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
{'<div class="previa" role="note">PRÉVIA: site aguardando aprovação do estabelecimento</div>' if previa else ''}
<header class="barra">
  <a class="marca" href="#topo">{e(nome)}</a>
  <nav aria-label="Seções">{nav}</nav>
  <a class="botao pequeno" href="{e(zap)}" rel="noopener noreferrer">{ZAP_SVG}<span>Agendar</span></a>
</header>
<section id="topo" class="hero{' com-foto' if fotos else ''}">
  <div class="hero-conteudo">
    {f"<p class='etiqueta'>{e(c['categoria'])}</p>" if c.get('categoria') else ''}
    <h1>{e(nome)}</h1>
    {f"<p class='slogan'>{e(c['slogan'])}</p>" if c.get('slogan') else ''}
    <div class="acoes">
      <a class="botao" href="{e(zap)}" rel="noopener noreferrer">{ZAP_SVG}<span>Chamar no WhatsApp</span></a>
      <a class="botao fantasma" href="#local">{PIN_SVG}<span>Como chegar</span></a>
    </div>
  </div>
</section>
<main id="conteudo">
  {f"<section class='secao sobre'><p>{e(c['descricao'])}</p>{f'<ul class=destaques>{destaques}</ul>' if destaques else ''}</section>" if c.get('descricao') or destaques else ''}
  {secao('servicos', 'Serviços', f"<div class='servicos'>{servicos}</div>" if servicos else '')}
  {secao('fotos', 'Fotos', f"<div class='galeria'>{galeria}</div>" if galeria else '')}
  {secao('depoimentos', 'O que dizem os clientes', f"<div class='depos'>{depoimentos}</div>" if depoimentos else '')}
  <div class="duas">
    {secao('horarios', 'Horários', f"<ul class='horarios'>{horarios}</ul>" if horarios else '')}
    <section id="local" class="secao">
      <h2>Como chegar</h2>
      <p class="endereco">{PIN_SVG}<span>{e(c['endereco'])}</span></p>
      <a class="botao secundario" href="{e(mapa)}" rel="noopener noreferrer">Abrir no mapa</a>
    </section>
  </div>
  {secao('faq', 'Perguntas frequentes', f"<div class='faq'>{faq}</div>" if faq else '')}
  <section class="chamada">
    <h2>{e(c.get('chamada', 'Vamos agendar o seu horário?'))}</h2>
    <a class="botao" href="{e(zap)}" rel="noopener noreferrer">{ZAP_SVG}<span>Falar no WhatsApp</span></a>
  </section>
</main>
<footer>
  <p><b>{e(nome)}</b></p>
  <p>{e(c['endereco'])}</p>
  {f'<p>{insta}</p>' if insta else ''}
  {credito}
</footer>
<a class="flutuante" href="{e(zap)}" rel="noopener noreferrer" aria-label="Chamar no WhatsApp">{ZAP_SVG}</a>
</body>
</html>
"""


CSS = """:root{--cor:%(cor)s;--sobre-cor:%(sobre)s;--texto:#16181d;--suave:#5b616e;--fundo:#fbfbfd;--cartao:#fff;
--borda:rgba(20,20,40,.09);--sombra:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(0,0,0,.06);--zap:#1da851;--raio:18px}
@media (prefers-color-scheme:dark){:root{--texto:#f2f3f5;--suave:#a4a9b4;--fundo:#0e0f12;--cartao:#17191e;
--borda:rgba(255,255,255,.08);--sombra:0 8px 24px rgba(0,0,0,.4)}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;color:var(--texto);
background:var(--fundo);line-height:1.6;-webkit-font-smoothing:antialiased}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
a{color:inherit}svg{flex:none}
.pular{position:absolute;left:-999px;top:8px;background:#000;color:#fff;padding:8px 12px;z-index:99}.pular:focus{left:8px}
.previa{background:#ffd60a;color:#111;text-align:center;padding:8px 16px;font-weight:600;font-size:.9rem}
.barra{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:16px;padding:10px max(16px,calc((100%% - 1080px)/2));
background:color-mix(in srgb,var(--fundo) 82%%,transparent);backdrop-filter:saturate(1.6) blur(14px);border-bottom:1px solid var(--borda)}
.marca{font-weight:800;text-decoration:none;letter-spacing:-.01em;margin-right:auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.barra nav{display:flex;gap:18px}.barra nav a{text-decoration:none;color:var(--suave);font-size:.95rem}.barra nav a:hover{color:var(--texto)}
@media (max-width:720px){.barra nav{display:none}}
.hero{position:relative;color:var(--sobre-cor);text-align:center;padding:clamp(72px,14vw,140px) 16px clamp(64px,10vw,110px);
background:radial-gradient(1200px 500px at 50%% -10%%,color-mix(in srgb,var(--cor) 55%%,#fff) 0%%,transparent 60%%),
linear-gradient(160deg,color-mix(in srgb,var(--cor) 80%%,#000) 0%%,var(--cor) 55%%,color-mix(in srgb,var(--cor) 70%%,#000) 100%%);overflow:hidden}
.hero.com-foto{color:#fff;background:linear-gradient(180deg,rgba(0,0,0,.35),rgba(0,0,0,.65)),url("%(capa)s") center/cover}
.hero-conteudo{max-width:760px;margin:0 auto;position:relative}
.etiqueta{display:inline-block;margin:0 0 14px;padding:4px 12px;border-radius:999px;font-size:.8rem;font-weight:600;
letter-spacing:.08em;text-transform:uppercase;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28)}
.hero h1{margin:0;font-size:clamp(2.3rem,7vw,4.2rem);line-height:1.05;letter-spacing:-.03em;font-weight:800}
.slogan{margin:16px auto 34px;font-size:clamp(1.05rem,2.4vw,1.3rem);opacity:.92;max-width:560px}
.acoes{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.botao{display:inline-flex;align-items:center;gap:10px;background:var(--zap);color:#fff;font-weight:700;padding:14px 24px;
border-radius:999px;text-decoration:none;box-shadow:0 6px 20px rgba(29,168,81,.35);transition:transform .15s,box-shadow .15s}
.botao:hover{transform:translateY(-2px);box-shadow:0 10px 26px rgba(29,168,81,.45)}
.botao:focus-visible,.barra a:focus-visible,.flutuante:focus-visible{outline:3px solid var(--cor);outline-offset:3px}
.botao.pequeno{padding:9px 16px;font-size:.92rem;box-shadow:none}
.botao.fantasma{background:rgba(255,255,255,.14);color:inherit;border:1px solid rgba(255,255,255,.35);box-shadow:none}
.hero:not(.com-foto) .botao.fantasma{border-color:color-mix(in srgb,var(--sobre-cor) 35%%,transparent)}
.botao.secundario{background:var(--cor);color:var(--sobre-cor);box-shadow:none}
main{max-width:1080px;margin:0 auto;padding:0 16px 40px}
.secao{margin-top:64px}.secao h2,.chamada h2{font-size:clamp(1.5rem,3.4vw,2rem);letter-spacing:-.02em;margin:0 0 22px}
.sobre{max-width:760px;margin-left:auto;margin-right:auto;text-align:center}.sobre p{font-size:1.15rem;color:var(--suave);margin:0}
.destaques{list-style:none;padding:0;margin:28px 0 0;display:flex;flex-wrap:wrap;gap:10px;justify-content:center}
.destaques li{background:var(--cartao);border:1px solid var(--borda);padding:8px 16px;border-radius:999px;font-weight:600;font-size:.95rem}
.destaques li::before{content:"✓";color:var(--zap);margin-right:8px;font-weight:800}
.servicos{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.servico{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;background:var(--cartao);
border:1px solid var(--borda);border-radius:var(--raio);padding:20px 22px;box-shadow:var(--sombra)}
.servico h3{margin:0;font-size:1.08rem}.servico p{margin:6px 0 0;color:var(--suave);font-size:.94rem}
.preco{font-weight:800;white-space:nowrap;color:var(--cor)}
@media (prefers-color-scheme:dark){.preco{color:color-mix(in srgb,var(--cor) 45%%,#fff)}}
.galeria{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.galeria img{width:100%%;aspect-ratio:4/3;object-fit:cover;border-radius:14px;display:block}
.depos{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.depo{margin:0;background:var(--cartao);border:1px solid var(--borda);border-radius:var(--raio);padding:22px;box-shadow:var(--sombra)}
.depo blockquote{margin:0 0 12px;font-size:1.02rem}.depo figcaption{color:var(--suave);font-weight:600;font-size:.9rem}
.duas{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0 28px}
.horarios{list-style:none;padding:0;margin:0;background:var(--cartao);border:1px solid var(--borda);border-radius:var(--raio);box-shadow:var(--sombra)}
.horarios li{display:flex;justify-content:space-between;gap:16px;padding:14px 20px;border-bottom:1px solid var(--borda)}.horarios li:last-child{border:0}
.endereco{display:flex;gap:10px;align-items:flex-start;font-size:1.05rem;margin:0 0 18px}.endereco svg{color:var(--cor);margin-top:3px}
.chamada{margin-top:72px;text-align:center;padding:48px 20px;border-radius:28px;background:var(--cartao);border:1px solid var(--borda);box-shadow:var(--sombra)}
footer{text-align:center;color:var(--suave);padding:36px 16px 96px;font-size:.95rem}footer p{margin:4px 0}
.credito{margin-top:18px!important;font-size:.82rem;opacity:.75}
.faq{display:grid;gap:10px;max-width:820px}.faq details{background:var(--cartao);border:1px solid var(--borda);border-radius:14px;padding:4px 20px}
.faq summary{cursor:pointer;font-weight:700;padding:14px 0;list-style:none;display:flex;justify-content:space-between;gap:12px}
.faq summary::-webkit-details-marker{display:none}.faq summary::after{content:"+";font-size:1.3rem;line-height:1;color:var(--cor)}
.faq details[open] summary::after{content:"–"}.faq details p{margin:0 0 16px;color:var(--suave)}
.faq summary:focus-visible{outline:3px solid var(--cor);outline-offset:3px;border-radius:6px}
.flutuante{position:fixed;right:18px;bottom:18px;width:58px;height:58px;border-radius:50%%;background:var(--zap);color:#fff;
display:grid;place-items:center;box-shadow:0 8px 24px rgba(0,0,0,.25);z-index:20}.flutuante svg{width:30px;height:30px}
"""


def otimizar(origem, pasta):
    """Foto de celular tem 3–8 MB; no site vira WebP de até 1600px (~200 KB), sem dados de GPS (EXIF).
    Sem Pillow instalado, copia como está."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        shutil.copy(origem, pasta / origem.name)
        return origem.name
    nome = origem.stem + ".webp"
    with Image.open(origem) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")  # gira certo e descarta o EXIF
        im.thumbnail((1600, 1600))
        im.save(pasta / nome, "WEBP", quality=80, method=6)
    return nome


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
            if f.suffix.lower() in FOTO_OK and f.stat().st_size < 15_000_000 and re.fullmatch(r"[\w.-]+", f.name):
                fotos.append(otimizar(f, destino / "fotos"))
    cor = c.get("cor", "#1f6feb")
    (destino / "index.html").write_text(pagina(c, fotos), encoding="utf-8")
    (destino / "estilo.css").write_text(
        CSS % {"cor": cor, "sobre": texto_sobre(cor), "capa": f"fotos/{fotos[0]}" if fotos else ""}, encoding="utf-8")
    return destino


def main():
    erros, aprovados = 0, []
    for arq in sorted((AQUI / "clientes").glob("*.json")):
        try:
            print(f"OK  {arq.name} -> {gerar(arq).relative_to(AQUI)}")
            c = json.loads(arq.read_text(encoding="utf-8"))
            if c.get("aprovado"):
                aprovados.append(c["slug"])
        except (ValueError, KeyError, json.JSONDecodeError) as ex:
            erros += 1
            print(f"ERRO {arq.name}: {ex}")
    # Raiz sem lista de clientes (prévias não ficam expostas); sitemap só com os aprovados.
    (SAIDA / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
                                      '<title>Sites</title><p>Nada aqui.</p>', encoding="utf-8")
    robots = "User-agent: *\nAllow: /\n"
    if BASE:
        urls = "".join(f"<url><loc>{html.escape(BASE)}/{s}/</loc></url>" for s in aprovados)
        (SAIDA / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns='
                                           f'"http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
                                           encoding="utf-8")
        robots += f"Sitemap: {BASE}/sitemap.xml\n"
    (SAIDA / "robots.txt").write_text(robots, encoding="utf-8")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
