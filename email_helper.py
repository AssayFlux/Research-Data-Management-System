"""SMTP send + email queue."""
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import setting, execute, query


def _cfg():
    return {
        "host":    setting("smtp_host", ""),
        "port":    int(setting("smtp_port", "587") or "587"),
        "user":    setting("smtp_user", ""),
        "pass":    setting("smtp_pass", ""),
        "from":    setting("smtp_from", setting("smtp_user", "")),
        "tls":     setting("smtp_tls", "1") == "1",
    }


def is_configured():
    c = _cfg()
    return bool(c["host"] and c["user"] and c["from"])


def send_now(recipient, subject, body):
    c = _cfg()
    if not is_configured():
        return False, "SMTP not configured"
    try:
        msg = MIMEMultipart()
        msg["From"] = c["from"]
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        ctx = ssl.create_default_context()
        if c["port"] == 465:
            with smtplib.SMTP_SSL(c["host"], c["port"], context=ctx, timeout=20) as s:
                s.login(c["user"], c["pass"])
                s.sendmail(c["from"], [recipient], msg.as_string())
        else:
            with smtplib.SMTP(c["host"], c["port"], timeout=20) as s:
                if c["tls"]:
                    s.starttls(context=ctx)
                s.login(c["user"], c["pass"])
                s.sendmail(c["from"], [recipient], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)


def queue(recipient, subject, body):
    if not recipient:
        return None
    return execute("""INSERT INTO email_queue(recipient, subject, body)
                      VALUES(?,?,?)""", (recipient, subject, body))


def flush_queue():
    """Try sending pending emails. Returns (sent, failed)."""
    rows = query("SELECT * FROM email_queue WHERE status='pending' ORDER BY id LIMIT 50")
    sent = failed = 0
    for r in rows:
        ok, msg = send_now(r["recipient"], r["subject"], r["body"] or "")
        if ok:
            execute("""UPDATE email_queue SET status='sent',
                       sent_at=CURRENT_TIMESTAMP WHERE id=?""", (r["id"],))
            sent += 1
        else:
            execute("""UPDATE email_queue SET status='failed',
                       error=? WHERE id=?""", (msg[:300], r["id"]))
            failed += 1
    return sent, failed
