"""
SMTP credential diagnostic for the SES <-> Supabase hop (spike, not
production code). Reads credentials from `.smtp_creds` next to this
file (gitignored): line 1 = SMTP username, line 2 = SMTP password.

Performs STARTTLS auth against the eu-north-1 SES endpoint and, if auth
succeeds, sends a test mail (verified sender -> verified recipient, so
sandbox-safe). Prints the exact SMTP conversation result at each stage.

Run: python tasks/auth_stack_v2/spike/test_smtp.py
"""

import pathlib
import smtplib
import sys
from email.message import EmailMessage

HOST = "email-smtp.eu-north-1.amazonaws.com"
PORT = 587
ADDRESS = "navdeep@marketworks.in"
CREDS = pathlib.Path(__file__).parent / ".smtp_creds"


def main() -> int:
    if not CREDS.exists():
        print(f"create {CREDS} first: line 1 username, line 2 password")
        return 1
    lines = CREDS.read_text().strip().splitlines()
    if len(lines) < 2:
        print(".smtp_creds needs 2 lines: username, then password")
        return 1
    user, password = lines[0].strip(), lines[1].strip()
    print(f"username: {user[:4]}...{user[-4:]} (len {len(user)})")
    print(f"password: <hidden> (len {len(password)})")

    try:
        with smtplib.SMTP(HOST, PORT, timeout=15) as smtp:
            print(f"connected to {HOST}:{PORT}")
            smtp.starttls()
            print("STARTTLS ok")
            smtp.login(user, password)
            print("AUTH ok — credentials are valid for eu-north-1")
            msg = EmailMessage()
            msg["From"] = ADDRESS
            msg["To"] = ADDRESS
            msg["Subject"] = "SMTP credential test (auth_stack_v2 spike)"
            msg.set_content(
                "SMTP auth + send both work — Supabase config is the "
                "remaining suspect."
            )
            smtp.send_message(msg)
            print("SEND ok — full SMTP chain works")
        return 0
    except smtplib.SMTPAuthenticationError as exc:
        print(f"AUTH FAILED ({exc.smtp_code}): {exc.smtp_error!r}")
        print("=> wrong username/password for this region — recreate the")
        print("   SMTP credentials with the console set to eu-north-1")
        return 1
    except smtplib.SMTPResponseException as exc:
        print(f"SMTP error ({exc.smtp_code}): {exc.smtp_error!r}")
        if exc.smtp_code == 554:
            print("=> auth OK but sending denied — IAM policy on the SMTP")
            print("   user is missing ses:SendRawEmail")
        return 1


if __name__ == "__main__":
    sys.exit(main())
