# Prospecção

Acha negócios locais sem site, prepara a abordagem pelo WhatsApp e gera o site do cliente.

## No PC
- `prospectar.bat`: pede o nicho e a cidade e abre a lista no navegador, com botões de WhatsApp.
- `mensagem.txt`: texto da abordagem. `{nome}` vira o nome do negócio e `{nicho}` o nicho buscado.

## Na nuvem (GitHub Actions, com o PC desligado)
- Segunda e quinta às 8h, busca os alvos de `alvos.txt` e manda no Telegram só os negócios novos.
- Secrets: `TELEGRAM_TOKEN` e `TELEGRAM_CHAT`, gravados pelo `configurar_telegram.py`.
- Antes de mandar, confere se o negócio tem mesmo site (`verificar.py`). Testa o domínio provável e, se o Secret opcional `BRAVE_API_KEY` existir, faz uma busca no Brave.
  - Só conta como "tem site" se a página tiver o **telefone ou o endereço** do negócio.
  - Se só o nome bater, o contato vem com "⚠️ Confira antes".

## Sites de clientes
1. Copie `sites/clientes/exemplo-barbearia.json` (campos opcionais: categoria, slogan, descricao, destaques, servicos com desc e preco, horarios, depoimentos REAIS, instagram, chamada, credito) para `sites/clientes/<cliente>.json` e preencha os dados.
2. As fotos são opcionais. Ponha numa pasta com o mesmo nome do arquivo, por exemplo `sites/clientes/<cliente>/`, em jpg, png ou webp com menos de 3 MB cada. Use só fotos do próprio cliente.
3. Envie a alteração para o GitHub (commit e push). O site é publicado no GitHub Pages em `.../<slug>/`.
4. Enquanto `"aprovado": false`, o site mostra a faixa de PRÉVIA e fica fora do Google. Mude para `true` só depois que o dono aprovar.

Segurança: o site é só HTML e CSS. Não tem JavaScript, formulário nem banco de dados. Todo texto é escapado, os links são montados pelo gerador e a CSP bloqueia recursos de fora.

Testes: `python test_prospectar.py` e `python test_nuvem_sites.py`.
