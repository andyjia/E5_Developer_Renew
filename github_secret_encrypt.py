import argparse
import os
import sys
from base64 import b64encode
from nacl import encoding, public


def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key and return the base64 output."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description='Encrypt the secret value using the GitHub public key.')
    parser.add_argument('-p', '--public_key', type=str, help='GitHub public key', required=True)
    parser.add_argument('-s', '--secret_value', type=str,
                        help='Secret value. Prefer piping it via stdin or setting SECRET_VALUE '
                             'so it never shows up in the process list or shell history.')
    args = parser.parse_args()

    if args.secret_value is not None:
        secret_value = args.secret_value
    elif os.environ.get('SECRET_VALUE'):
        secret_value = os.environ['SECRET_VALUE']
    else:
        # Read from stdin and drop a trailing newline
        # (e.g. `cat refresh_token.txt | python github_secret_encrypt.py -p "$PUB_KEY"`).
        secret_value = sys.stdin.read().rstrip('\r\n')

    print(encrypt(args.public_key, secret_value))


if __name__ == "__main__":
    main()
