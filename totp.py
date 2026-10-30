"""TOTP (RFC 6238) using only stdlib. Falls back gracefully if pyotp is installed."""
import hmac, hashlib, base64, struct, time, secrets

def _try_pyotp():
    try:
        import pyotp
        return pyotp
    except ImportError:
        return None


def gen_secret(nbytes=20):
    return base64.b32encode(secrets.token_bytes(nbytes)).decode("ascii").rstrip("=")


def _hotp(key, counter, digits=6):
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = ((h[offset] & 0x7F) << 24
            | (h[offset + 1] & 0xFF) << 16
            | (h[offset + 2] & 0xFF) << 8
            | (h[offset + 3] & 0xFF))
    return str(code % (10 ** digits)).zfill(digits)


def now_code(secret, step=30, digits=6):
    pyotp = _try_pyotp()
    if pyotp:
        return pyotp.TOTP(secret, digits=digits, interval=step).now()
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    counter = int(time.time() // step)
    return _hotp(key, counter, digits)


def verify_code(secret, code, step=30, digits=6, window=1):
    """Accept code within ±window steps of now."""
    if not secret or not code: return False
    code = str(code).strip().replace(" ", "")
    if len(code) != digits or not code.isdigit(): return False
    pyotp = _try_pyotp()
    if pyotp:
        return pyotp.TOTP(secret, digits=digits, interval=step).verify(code, valid_window=window)
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    counter = int(time.time() // step)
    for offset in range(-window, window + 1):
        if _hotp(key, counter + offset, digits) == code:
            return True
    return False


def otpauth_url(secret, label, issuer):
    from urllib.parse import quote
    return (f"otpauth://totp/{quote(label)}?secret={secret}"
            f"&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30")


def backup_codes(n=8):
    return [secrets.token_hex(4).upper() for _ in range(n)]


def qr_png_b64(text, size=6):
    try:
        import qrcode, io
        qr = qrcode.QRCode(version=None,
                           error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=size, border=2)
        qr.add_data(text); qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None
