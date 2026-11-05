#!/usr/bin/env python3
"""Amigo Oculto: sorteia, gera um link secreto por pessoa e envia por e-mail.

Nunca imprime quem tirou quem.

  python3 sortear.py --simular        links de teste com nomes fictícios
  python3 sortear.py --verificar      testa as regras do sorteio (sem revelar nada)
  python3 sortear.py --teste          envia um e-mail de teste só para você
  python3 sortear.py --enviar         sorteio real + envio para todos
  python3 sortear.py --reenviar Nome  reenvia o link de alguém, sem ressortear
"""
import argparse
import base64
import json
import secrets
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQ_PARTICIPANTES = PASTA / "participantes.json"
ARQ_RESULTADO = PASTA / "resultado.secreto"
ARQ_ENV = PASTA / ".env"

FICTICIOS = ["Papai Noel", "Mamãe Noel", "Rudolph", "Grinch", "Frosty", "Elfo Zé"]


def erro(msg):
    sys.exit(f"✗ {msg}")


def carregar_env():
    env = {}
    if ARQ_ENV.exists():
        for linha in ARQ_ENV.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                env[chave.strip()] = valor.strip().strip("\"'")
    return env


def carregar_participantes():
    if not ARQ_PARTICIPANTES.exists():
        erro("participantes.json não encontrado (copie participantes.exemplo.json).")
    dados = json.loads(ARQ_PARTICIPANTES.read_text(encoding="utf-8"))
    pessoas = dados["participantes"]
    nomes = [p["nome"] for p in pessoas]
    if len(nomes) < 3:
        erro("São necessárias pelo menos 3 pessoas.")
    if len(set(nomes)) != len(nomes):
        erro("Há nomes repetidos em participantes.json.")
    proibidos = {tuple(par) for par in dados.get("proibidos", [])}
    for a, b in proibidos:
        if a not in nomes or b not in nomes:
            erro(f"Par proibido com nome desconhecido: {a} -> {b}")
    return pessoas, nomes, proibidos


def sortear(nomes, proibidos):
    """Um único círculo fechado: cada pessoa tira a próxima da roda embaralhada."""
    rng = secrets.SystemRandom()
    for _ in range(100_000):
        roda = list(nomes)
        rng.shuffle(roda)
        pares = {roda[i]: roda[(i + 1) % len(roda)] for i in range(len(roda))}
        if not any(par in proibidos for par in pares.items()):
            return pares
    erro("Não existe sorteio possível com essas regras.")


def gerar_token(quem, tirou, nomes):
    """16 bytes de chave + JSON embaralhado com XOR, em base64url."""
    dados = json.dumps({"q": quem, "t": tirou, "n": nomes}, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
    chave = secrets.token_bytes(16)
    cifrado = bytes(b ^ chave[i % 16] for i, b in enumerate(dados))
    return base64.urlsafe_b64encode(chave + cifrado).decode("ascii").rstrip("=")


def gerar_link(url_base, quem, tirou, nomes):
    return f"{url_base.rstrip('/')}/#{gerar_token(quem, tirou, nomes)}"


def montar_email(remetente, destinatario, nome, link, teste=False):
    msg = EmailMessage()
    prefixo = "[TESTE] " if teste else ""
    msg["Subject"] = f"{prefixo}🎄 Amigo Oculto · Secret Santa · Pige de Noël — {nome}"
    msg["From"] = formataddr(("Amigo Oculto 🎄", remetente))
    msg["To"] = formataddr((nome, destinatario))

    msg.set_content(f"""Olá, {nome}!
O sorteio do nosso amigo oculto de Natal foi feito. Abra o seu link secreto (longe de olhares curiosos!) para descobrir quem você tirou.

Hi, {nome}!
Our Christmas Secret Santa draw is done. Open your secret link (away from curious eyes!) to find out who you got.

Bonjour, {nome} !
La pige de notre échange de cadeaux de Noël est faite. Ouvre ton lien secret (loin des regards curieux !) pour découvrir qui tu as pigé.

{link}

Este link é só seu. This link is yours only. Ce lien est juste pour toi.
""")

    n = escape(nome)
    bloco = ('<p style="margin:0 0 4px;font-size:20px;font-weight:bold;color:#12303f">{ola}</p>'
             '<p style="margin:0 0 22px;font-size:16px;line-height:1.5;color:#3d5560">{txt}</p>')
    textos = "".join(bloco.format(ola=ola, txt=txt) for ola, txt in [
        (f"🇧🇷 Olá, {n}!",
         "O sorteio do nosso amigo oculto de Natal foi feito. Abra o seu link secreto, "
         "longe de olhares curiosos, para descobrir quem você tirou."),
        (f"🇨🇦 Hi, {n}!",
         "Our Christmas Secret Santa draw is done. Open your secret link, "
         "away from curious eyes, to find out who you got."),
        (f"⚜️ Bonjour, {n} !",
         "La pige de notre échange de cadeaux de Noël est faite. Ouvre ton lien secret, "
         "loin des regards curieux, pour découvrir qui tu as pigé."),
    ])
    msg.add_alternative(f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#0b2233">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b2233;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#fffaf2;border-radius:18px;overflow:hidden;font-family:Georgia,'Times New Roman',serif">
<tr><td align="center" style="background:#b3202a;padding:28px 20px;color:#fffaf2">
<div style="font-size:40px;line-height:1">🎄🍁❄️</div>
<div style="font-size:26px;font-weight:bold;margin-top:10px">Amigo Oculto</div>
<div style="font-size:15px;opacity:.9;margin-top:4px">Secret Santa · Pige de Noël</div>
</td></tr>
<tr><td style="padding:28px 26px 8px">{textos}</td></tr>
<tr><td align="center" style="padding:4px 26px 26px">
<a href="{escape(link)}" style="display:inline-block;background:#1c6b4a;color:#ffffff;text-decoration:none;font-size:17px;font-weight:bold;padding:16px 26px;border-radius:999px;line-height:1.5">
🎁 Descobrir quem eu tirei<br>Find out who I got<br>Découvrir qui j'ai pigé</a>
</td></tr>
<tr><td align="center" style="padding:0 26px 26px;font-size:13px;color:#7b8a90;line-height:1.5">
🤫 Este link é só seu. · This link is yours only. · Ce lien est juste pour toi.
</td></tr>
</table>
</td></tr></table>
</body></html>""", subtype="html")
    return msg


def conectar(env):
    usuario = env.get("GMAIL_USER", "")
    senha = env.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not usuario or not senha:
        erro("Preencha GMAIL_USER e GMAIL_APP_PASSWORD no arquivo .env "
             "(senha de app: https://myaccount.google.com/apppasswords).")
    smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context())
    try:
        smtp.login(usuario, senha)
    except smtplib.SMTPAuthenticationError:
        erro("O Gmail recusou o login. Confira a senha de app no .env.")
    return smtp, usuario


def url_base(env):
    url = env.get("URL_BASE", "")
    if not url:
        erro("Preencha URL_BASE no arquivo .env.")
    return url


def cmd_simular(env):
    quem, tirou = "Você", FICTICIOS[0]
    token = gerar_token(quem, tirou, [quem] + FICTICIOS)
    print("Links de teste (nomes fictícios):")
    print(f"  local:     file://{PASTA / 'index.html'}#{token}")
    if env.get("URL_BASE"):
        print(f"  publicado: {env['URL_BASE'].rstrip('/')}/#{token}")


def cmd_verificar():
    _, nomes, proibidos = carregar_participantes()
    for _ in range(10_000):
        pares = sortear(nomes, proibidos)
        assert set(pares) == set(pares.values()) == set(nomes)
        assert all(a != b for a, b in pares.items())
        assert not any(par in proibidos for par in pares.items())
        atual, passos = nomes[0], 0
        while True:
            atual, passos = pares[atual], passos + 1
            if atual == nomes[0]:
                break
        assert passos == len(nomes), "a roda abriu mais de uma vez"
    print(f"✓ 10.000 sorteios com {len(nomes)} pessoas: círculo único, "
          "ninguém tira a si mesmo, nenhum par proibido.")


def cmd_teste(env):
    base = url_base(env)
    smtp, usuario = conectar(env)
    link = gerar_link(base, "Ian", FICTICIOS[0], ["Ian"] + FICTICIOS)
    smtp.send_message(montar_email(usuario, usuario, "Ian", link, teste=True))
    smtp.quit()
    print(f"✓ E-mail de teste enviado para {usuario} (nomes fictícios, nenhum sorteio real).")


def cmd_enviar(env):
    if ARQ_RESULTADO.exists():
        erro("O sorteio já foi feito (resultado.secreto existe). Use --reenviar Nome. "
             "Para sortear de novo, apague resultado.secreto antes.")
    pessoas, nomes, proibidos = carregar_participantes()
    base = url_base(env)
    print(f"Sorteio REAL para {len(nomes)} pessoas: {', '.join(nomes)}")
    if input('Digite SORTEAR para confirmar: ').strip() != "SORTEAR":
        erro("Cancelado.")
    smtp, usuario = conectar(env)
    pares = sortear(nomes, proibidos)
    resultado = {p["nome"]: {"email": p["email"],
                             "link": gerar_link(base, p["nome"], pares[p["nome"]], nomes)}
                 for p in pessoas}
    ARQ_RESULTADO.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    falhas = []
    for nome, r in resultado.items():
        try:
            smtp.send_message(montar_email(usuario, r["email"], nome, r["link"]))
            print(f"✓ E-mail enviado para {nome}")
        except smtplib.SMTPException as e:
            falhas.append(nome)
            print(f"✗ Falha ao enviar para {nome}: {e}")
    smtp.quit()
    if falhas:
        print("Reenvie com: " + " ; ".join(f'python3 sortear.py --reenviar "{n}"' for n in falhas))
    else:
        print("🎄 Tudo enviado! Feliz Natal!")


def cmd_reenviar(env, nome):
    if not ARQ_RESULTADO.exists():
        erro("Ainda não houve sorteio (resultado.secreto não existe).")
    resultado = json.loads(ARQ_RESULTADO.read_text(encoding="utf-8"))
    if nome not in resultado:
        erro(f"Nome não encontrado. Opções: {', '.join(resultado)}")
    smtp, usuario = conectar(env)
    r = resultado[nome]
    smtp.send_message(montar_email(usuario, r["email"], nome, r["link"]))
    smtp.quit()
    print(f"✓ E-mail reenviado para {nome}")


def main():
    ap = argparse.ArgumentParser(description="Sorteio de amigo oculto")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--simular", action="store_true", help="gera links de teste fictícios")
    g.add_argument("--verificar", action="store_true", help="testa as regras do sorteio")
    g.add_argument("--teste", action="store_true", help="envia um e-mail de teste só para você")
    g.add_argument("--enviar", action="store_true", help="sorteio real + envio")
    g.add_argument("--reenviar", metavar="NOME", help="reenvia o link de uma pessoa")
    args = ap.parse_args()
    env = carregar_env()
    if args.simular:
        cmd_simular(env)
    elif args.verificar:
        cmd_verificar()
    elif args.teste:
        cmd_teste(env)
    elif args.enviar:
        cmd_enviar(env)
    else:
        cmd_reenviar(env, args.reenviar)


if __name__ == "__main__":
    main()
