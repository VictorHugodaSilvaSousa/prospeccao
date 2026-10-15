from prospectar import celular, filtro, linha


def test_celular():
    assert celular("+55 61 98434 3749; +55 61 99151 5179") == "5561984343749"
    assert celular("+55 61 3391 5952") == ""  # fixo
    assert celular("(061) 3391-5952; 61 99151-5179") == "5561991515179"
    assert celular("") == ""


def test_linha():
    l = linha({"name": "Barbearia X", "contact:phone": "61 9999", "addr:street": "QNA 1", "addr:housenumber": "10"})
    assert l["Tem site"] == "NÃO" and l["Telefone"] == "61 9999" and l["Endereço"] == "QNA 1 10"
    assert linha({"name": "Y", "website": "https://y.com"})["Tem site"] == "sim"
    l = linha({"name": "Z", "website": "https://www.instagram.com/z/"})
    assert l["Tem site"] == "NÃO" and l["Rede social"] == "https://www.instagram.com/z/"


def test_filtro():
    assert filtro("barbearia") == '["shop"="hairdresser"]'
    assert filtro("shop=bakery") == '["shop"="bakery"]'


if __name__ == "__main__":
    test_linha(); test_filtro(); test_celular(); print("ok")
