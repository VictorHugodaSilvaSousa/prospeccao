"""Cria sites/clientes/<slug>.json para um contato, com textos-base do nicho, pronto para virar prévia.

Uso:
    python novo_cliente.py barbearia "Barbearia do Zé" "61 99999-9999" "QNA 1, Taguatinga - DF"
Depois: revise o JSON COM O DONO (serviços, preços, horários, fotos) e envie para o GitHub.
Nunca inventa preço ou depoimento; o site sai como PRÉVIA ("aprovado": false) até o dono aprovar.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

PASTA = Path(__file__).parent / "sites" / "clientes"
PADRAO = {
    "cor": "#1f6feb", "tipo_schema": "LocalBusiness", "destaques": ["Atendimento pelo WhatsApp", "Pix e cartão"],
    "servicos": [], "chamada": "Fale com a gente pelo WhatsApp",
    "faq": [{"pergunta": "Quais as formas de pagamento?", "resposta": "Pix, cartão de crédito e débito."}],
}
NICHOS = {
    "barbearia": {"cor": "#1f3a5f", "tipo_schema": "BarberShop", "categoria": "Barbearia",
                  "slogan": "Corte, barba e atendimento sem fila.",
                  "destaques": ["Hora marcada, sem fila", "Pix e cartão"],
                  "servicos": ["Corte", "Barba", "Corte + barba", "Sobrancelha"],
                  "chamada": "Garanta seu horário ainda hoje",
                  "faq": [{"pergunta": "Precisa agendar?", "resposta": "Recomendamos agendar pelo WhatsApp para não esperar."}]},
    "salao": {"cor": "#7a2e5b", "tipo_schema": "BeautySalon", "categoria": "Salão de beleza",
              "slogan": "Cuidado e beleza no seu tempo.", "servicos": ["Corte", "Escova", "Coloração", "Manicure"],
              "chamada": "Agende seu horário pelo WhatsApp"},
    "beleza": {"cor": "#8a3b6b", "tipo_schema": "BeautySalon", "categoria": "Estética e beleza",
               "servicos": ["Design de sobrancelhas", "Limpeza de pele", "Depilação"]},
    "restaurante": {"cor": "#8c2f1b", "tipo_schema": "Restaurant", "categoria": "Restaurante",
                    "slogan": "Comida feita com carinho, todos os dias.",
                    "destaques": ["Pedidos pelo WhatsApp", "Pix e cartão"], "chamada": "Faça seu pedido pelo WhatsApp"},
    "pizzaria": {"cor": "#b3261e", "tipo_schema": "Restaurant", "categoria": "Pizzaria",
                 "slogan": "Pizza quentinha, do forno pra sua casa.", "chamada": "Peça sua pizza pelo WhatsApp"},
    "lanchonete": {"cor": "#c2570c", "tipo_schema": "FastFoodRestaurant", "categoria": "Lanchonete",
                   "chamada": "Peça pelo WhatsApp"},
    "padaria": {"cor": "#8a5a2b", "tipo_schema": "Bakery", "categoria": "Padaria", "chamada": "Encomende pelo WhatsApp"},
    "cafe": {"cor": "#5b3a29", "tipo_schema": "CafeOrCoffeeShop", "categoria": "Cafeteria"},
    "academia": {"cor": "#0f5132", "tipo_schema": "ExerciseGym", "categoria": "Academia",
                 "slogan": "Treine perto de casa, com acompanhamento.",
                 "servicos": ["Musculação", "Aula experimental"], "chamada": "Agende sua aula experimental"},
    "dentista": {"cor": "#0b5c7a", "tipo_schema": "Dentist", "categoria": "Consultório odontológico",
                 "chamada": "Agende sua avaliação pelo WhatsApp"},
    "clinica": {"cor": "#0b5c7a", "tipo_schema": "MedicalClinic", "categoria": "Clínica",
                "chamada": "Agende sua consulta pelo WhatsApp"},
    "petshop": {"cor": "#2f6f3e", "tipo_schema": "PetStore", "categoria": "Pet shop",
                "servicos": ["Banho", "Tosa", "Banho + tosa"], "chamada": "Agende o banho do seu pet"},
    "veterinario": {"cor": "#2f6f3e", "tipo_schema": "VeterinaryCare", "categoria": "Clínica veterinária",
                    "chamada": "Agende uma consulta para o seu pet"},
    "oficina": {"cor": "#374151", "tipo_schema": "AutoRepair", "categoria": "Oficina mecânica",
                "servicos": ["Revisão", "Troca de óleo", "Freios", "Suspensão"], "chamada": "Peça seu orçamento"},
    "roupas": {"cor": "#3f3d56", "tipo_schema": "ClothingStore", "categoria": "Loja de roupas"},
    "mercado": {"cor": "#1e6b3a", "tipo_schema": "GroceryStore", "categoria": "Mercado"},
    "farmacia": {"cor": "#0e7c66", "tipo_schema": "Pharmacy", "categoria": "Farmácia"},
}


def slug(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "cliente"


def montar(nicho, nome, whatsapp, endereco):
    p = {**PADRAO, **NICHOS.get(nicho, {})}
    cidade = endereco.split(",")[-1].strip() if "," in endereco else ""
    return {
        "nome": nome, "slug": slug(nome), "aprovado": False,
        "categoria": f"{p.get('categoria', nicho.title())}{' em ' + cidade if cidade else ''}",
        "slogan": p.get("slogan", ""),
        "descricao": "",  # preencher com o dono: história, diferencial, há quanto tempo atende
        "destaques": p["destaques"], "cor": p["cor"], "tipo_schema": p["tipo_schema"],
        "whatsapp": whatsapp, "instagram": "", "endereco": endereco,
        "servicos": [{"nome": s} for s in p["servicos"]],  # preços: só os que o dono informar
        "horarios": {}, "faq": p["faq"], "chamada": p["chamada"], "credito": "Victor Hugo",
    }


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    c = montar(sys.argv[1].lower(), *sys.argv[2:])
    arq = PASTA / f"{c['slug']}.json"
    if arq.exists():
        sys.exit(f"Já existe: {arq}")
    arq.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PASTA / c["slug"]).mkdir(exist_ok=True)
    print(f"Criado {arq}\nFotos do cliente em: {PASTA / c['slug']}\nRevise com o dono e rode: python sites/gerar.py")


if __name__ == "__main__":
    main()
