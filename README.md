# Prospecção

Acha negócios locais sem site, prepara a abordagem pelo WhatsApp e gera o site do cliente.

## No PC
- `prospectar.bat`: pede o nicho e a cidade e abre a lista no navegador, com botões de WhatsApp.
- `mensagem.txt`: texto da abordagem. `{nome}` vira o nome do negócio e `{nicho}` o nicho buscado.

## Fontes
- **OpenStreetMap**: grátis, sempre ligado.
- **Google Maps (API oficial Places)**: opcional, com muito mais negócios e telefones. Para ligar, copie a chave e rode `configurar_chave.py google`.
  - Precisa de cartão no Google Cloud. **Ponha um limite de cota** para nunca passar da faixa grátis.
  - O robô guarda só o ID do lugar, como os termos do Google pedem.

## Quem vale abordar
- Quem tem celular **e** não tem site, ou tem site com problema. Instagram no campo "site" não conta como site.
- Problemas que o robô detecta: o domínio não existe mais, a página dá 404 repetido, o certificado está inválido, o site não tem HTTPS ou não se adapta ao celular.
- Timeout e bloqueio nunca contam como problema, para não acusar à toa.
- Cada caso tem a sua mensagem: `mensagem.txt` para quem não tem site e `mensagem-melhorar.txt` para site com problema (`{problema}` vira a frase do problema).

## Na nuvem (GitHub Actions, com o PC desligado)
- Dias úteis às 8h, busca os alvos de `alvos.txt` e manda no Telegram os negócios novos que valem abordar.
- No máximo `PROSPECCAO_LIMITE` contatos por dia (Variable do repositório, padrão 15). O resto fica para o dia seguinte.
- Cada dia começa por um nicho diferente.
- Se uma busca falhar, você recebe um aviso no Telegram.
- Secrets: `TELEGRAM_TOKEN` e `TELEGRAM_CHAT`, gravados pelo `configurar_telegram.py`.
- Antes de mandar, confere se o negócio tem mesmo site (`verificar.py`). Testa o domínio provável e, se o Secret opcional `BRAVE_API_KEY` existir, faz uma busca no Brave.
  - Só conta como "tem site" se a página tiver o **telefone ou o endereço** do negócio.
  - Se só o nome bater, o contato vem com "⚠️ Confira antes".

## Sites de clientes
0. Atalho: `python novo_cliente.py barbearia "Nome" "61 9xxxx-xxxx" "Endereço"` cria o JSON com os textos do nicho, sem preços inventados.
1. Ou copie `sites/clientes/exemplo-barbearia.json` (campos opcionais: categoria, slogan, descricao, destaques, servicos com desc e preco, horarios, depoimentos REAIS, faq, instagram, chamada, credito) para `sites/clientes/<cliente>.json` e preencha os dados.
2. As fotos são opcionais. Ponha numa pasta com o mesmo nome do arquivo, por exemplo `sites/clientes/<cliente>/`, em jpg, png ou webp. Elas viram WebP leve, de até 1.600 px, sem a localização do GPS. Use só fotos do próprio cliente.
3. Envie a alteração para o GitHub (commit e push). O site é publicado no GitHub Pages em `.../<slug>/`.
4. Enquanto `"aprovado": false`, o site mostra a faixa de PRÉVIA e fica fora do Google. Mude para `true` só depois que o dono aprovar.

Segurança: o site é só HTML e CSS. Não tem JavaScript, formulário nem banco de dados. Todo texto é escapado, os links são montados pelo gerador e a CSP bloqueia recursos de fora.

Testes: `python test_prospectar.py` e `python test_nuvem_sites.py`.
