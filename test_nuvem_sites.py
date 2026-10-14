import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sites"))
from gerar import pagina, validar  # noqa: E402
from nuvem import novos  # noqa: E402

BASE = {"nome": "Barbearia X", "slug": "barbearia-x", "whatsapp": "61 99999-9999", "endereco": "QNA 1"}


def test_escapa_html():
    c = dict(BASE, nome='<script>alert(1)</script>', descricao='"><img src=x onerror=alert(1)>')
    p = pagina(c, [])
    assert "<script>alert" not in p and "<img src=x" not in p
    assert 'content="noindex' in p  # sem aprovado = prévia fora do Google
    assert "noindex" not in pagina(dict(BASE, aprovado=True), [])


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
    vistos = set()
    assert novos([l, dict(l, **{"Tem site": "sim", "Nome": "B"}), dict(l, WhatsApp="", Nome="C")], vistos) == [l]
    assert novos([l], vistos) == []  # não repete


if __name__ == "__main__":
    test_escapa_html(); test_validar(); test_novos(); print("ok")
