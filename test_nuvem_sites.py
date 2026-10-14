import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sites"))
from gerar import pagina, validar  # noqa: E402
from nuvem import novos  # noqa: E402
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
    l = {"Nome": "A", "Endereço": "R1", "Tem site": "NÃO", "WhatsApp": "https://wa.me/1"}
    d = dict(l, Nome="D")  # a conferência descobre que D tem site

    def conferir(ls, _):
        for x in ls:
            if x["Nome"] == "D":
                x["Tem site"] = "sim"

    vistos = set()
    lista = [l, dict(l, **{"Tem site": "sim", "Nome": "B"}), dict(l, WhatsApp="", Nome="C"), d]
    assert novos(lista, vistos, conferir=conferir) == [l]
    assert "D|R1" in vistos  # não confere D de novo na próxima
    assert novos([l], vistos, conferir=conferir) == []  # não repete


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
    test_escapa_html(); test_validar(); test_novos(); test_verificar(); print("ok")
