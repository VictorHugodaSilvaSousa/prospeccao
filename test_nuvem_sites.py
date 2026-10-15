import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sites"))
sys.path.insert(0, str(Path(__file__).parent))
from gerar import pagina, validar  # noqa: E402
from google_places import linha_google  # noqa: E402
from nuvem import novos  # noqa: E402
from prospectar import juntar  # noqa: E402
from verificar import chaves, e_do_negocio, prova_local  # noqa: E402

BASE = {"nome": "Barbearia X", "slug": "barbearia-x", "whatsapp": "61 99999-9999", "endereco": "QNA 1"}


def test_escapa_html():
    c = dict(BASE, nome='<script>alert(1)</script>', descricao='"><img src=x onerror=alert(1)>')
    p = pagina(c, [])
    assert "<script>alert" not in p and "<img src=x" not in p
    assert 'content="noindex' in p  # sem aprovado = prévia fora do Google
    assert "noindex" not in pagina(dict(BASE, aprovado=True), [])
    p = pagina(dict(BASE, nome="</script><b>x", servicos=[{"nome": "<i>", "desc": "<u>", "preco": "<s>"}]), [])
    assert "</script><b>" not in p and "<i>" not in p and "<u>" not in p and "<s>" not in p


def test_novo_cliente_e_fotos(tmp=None):
    import tempfile
    from novo_cliente import montar
    from gerar import otimizar
    c = montar("barbearia", "Barbearia do Zé", "61 99999-8888", "QNA 1, Taguatinga - DF")
    validar(c)
    assert c["slug"] == "barbearia-do-ze" and not c["aprovado"] and all("preco" not in s for s in c["servicos"])
    assert "<details>" in pagina(c, [])  # FAQ do nicho
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        Image.new("RGB", (4000, 3000), "red").save(d / "grande.jpg", quality=95)
        nome = otimizar(d / "grande.jpg", d)
        with Image.open(d / nome) as im:
            assert nome == "grande.webp" and max(im.size) == 1600 and not im.getexif()


def test_validar():
    validar(BASE)
    for ruim in ({"slug": "../x"}, {"whatsapp": "61 3333-3333"}, {"instagram": "javascript:alert(1)"},
                 {"cor": "red;}body{display:none"}, {"nome": ""}):
        try:
            validar(dict(BASE, **ruim))
        except ValueError:
            continue
        raise AssertionError(f"deveria recusar {ruim}")


def test_novos():
    l = {"Id": "a", "Nome": "A", "Tem site": "NÃO", "WhatsApp": "https://wa.me/1", "Problema": ""}

    def conferir(ls, *_):
        for x in ls:
            if x["Id"] == "d":
                x["Tem site"] = "sim"  # a conferência descobre que D tem site ok
            if x["Id"] == "b":
                x["Problema"] = "o site está fora do ar"

    vistos = set()
    b = dict(l, Id="b", **{"Tem site": "sim"})
    lista = [l, b, dict(l, Id="c", WhatsApp=""), dict(l, Id="d")]
    assert novos(lista, vistos, conferir=conferir) == [l, b]  # sem site + site quebrado
    assert "d" in vistos and "c" not in vistos  # D não é conferido de novo; C nem tem celular
    assert novos(lista, vistos, conferir=conferir) == []  # não repete


def test_limite():
    ls = [{"Id": str(i), "Nome": str(i), "Tem site": "NÃO", "WhatsApp": "x", "Problema": ""} for i in range(5)]
    vistos = set()
    assert len(novos(ls, vistos, limite=2, conferir=lambda *_: None)) == 2
    assert vistos == {"0", "1"}  # os outros 3 ficam para amanhã
    assert [l["Id"] for l in novos(ls, vistos, limite=10, conferir=lambda *_: None)] == ["2", "3", "4"]


def test_google():
    p = {"id": "X1", "displayName": {"text": "Barbearia Y"}, "formattedAddress": "QNA 1, Taguatinga - DF, Brasil",
         "internationalPhoneNumber": "+55 61 99999-8888", "websiteUri": "https://instagram.com/barbeariay"}
    l = linha_google(p)
    assert l["Tem site"] == "NÃO" and l["Rede social"].startswith("https://instagram") and l["Id"] == "g:X1"
    assert linha_google(dict(p, websiteUri="https://barbeariay.com.br"))["Tem site"] == "sim"
    osm = [{"Nome": "Barbearia  Y", "Telefone": ""}, {"Nome": "Outra", "Telefone": "(61) 99999-8888"},
           {"Nome": "Nova", "Telefone": ""}]
    assert [x["Nome"] for x in juntar([l], osm)] == ["Barbearia Y", "Nova"]  # sem duplicar por nome ou fone


def test_verificar():
    assert chaves("Barbearia do Zé Alfes") == ["alfes"]
    assert e_do_negocio("https://www.alfesbarber.com.br/", "Alfes Barbershop")
    assert not e_do_negocio("https://www.instagram.com/alfes", "Alfes Barbershop")
    assert not e_do_negocio("https://www.ifood.com.br/alfes", "Alfes Barbershop")
    assert not e_do_negocio("https://outrabarbearia.com.br", "Alfes Barbershop")
    assert not e_do_negocio("https://qualquer.com", "Barbearia")  # nome só genérico: não arrisca
    l = {"Telefone": "+55 61 98434 3749", "Endereço": "SCLN 116 Bloco D Loja 14, Plano Piloto - Asa Norte"}
    assert prova_local("Ligue (61) 98434-3749", l)
    assert not prova_local("Bons Amigos Transportes, bloco loja asa norte, (11) 4002-8922", l)
    assert prova_local("Estamos na SCLN 116, Asa Norte", dict(l, Telefone="")) is False  # só 1 palavra própria
    assert prova_local("Rua Taguatinga Ceilândia", {"Telefone": "", "Endereço": "QNM 10, Ceilândia, Taguatinga"})


if __name__ == "__main__":
    test_escapa_html(); test_novo_cliente_e_fotos(); test_validar(); test_novos(); test_limite(); test_google(); test_verificar(); print("ok")
