# Amigo Oculto 🎄

Página de sorteio de amigo oculto: cada pessoa recebe por e-mail um link secreto que revela, com animação, quem ela tirou. Em português, inglês e francês.

O nome sorteado viaja embaralhado dentro do próprio link. Este repositório não contém nomes nem e-mails.

## Como usar

1. Copie `participantes.exemplo.json` para `participantes.json` e preencha.
2. Crie um arquivo `.env`:

   ```
   GMAIL_USER=voce@gmail.com
   GMAIL_APP_PASSWORD=senha de app do Google
   URL_BASE=https://usuario.github.io/amigo-oculto/
   ```

3. Rode:

   ```bash
   python3 sortear.py --verificar        # testa as regras, sem revelar nada
   python3 sortear.py --simular          # links de teste com nomes fictícios
   python3 sortear.py --teste            # e-mail de teste só para você
   python3 sortear.py --enviar           # sorteio real + envio para todos
   python3 sortear.py --reenviar "Nome"  # reenvia um link, sem ressortear
   ```

O sorteio forma um único círculo fechado e respeita os pares em `proibidos` (`["A", "B"]` = A não pode tirar B). O script nunca mostra quem tirou quem.
