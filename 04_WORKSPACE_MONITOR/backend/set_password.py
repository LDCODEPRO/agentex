"""
AGENTE-X Cockpit | Gerador de hash de senha
Roda 100% local. Pede a senha (sem eco na tela, via getpass) e imprime
o hash bcrypt -- cole esse valor em COCKPIT_PASSWORD_HASH no .env.
A senha em texto puro nunca e salva nem enviada a lugar nenhum.

Uso: python set_password.py
"""
import getpass

import bcrypt

if __name__ == "__main__":
    pw = getpass.getpass("Nova senha do cockpit (nao aparece na tela): ")
    pw2 = getpass.getpass("Confirme a senha: ")
    if pw != pw2:
        print("Senhas nao coincidem.")
        raise SystemExit(1)
    if len(pw) < 8:
        print("Use pelo menos 8 caracteres.")
        raise SystemExit(1)
    hashed = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print("\nCole esta linha no .env (local e/ou VPS):\n")
    print(f"COCKPIT_PASSWORD_HASH={hashed}")
