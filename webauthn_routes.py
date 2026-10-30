"""Fingerprint login via WebAuthn — minimal, Termux-compatible.

Requires the user to access the app at http://localhost:5000 (not 127.0.0.1)
because Chrome rejects IP addresses for WebAuthn.
"""
import json, base64, secrets
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, g, session, jsonify, abort)
from database import query, one, execute


RP_NAME = "Research DMS"


def _b64u_enc(b):
    if isinstance(b, str):
        b = b.encode("utf-8")
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64u_dec(s):
    if isinstance(s, bytes):
        s = s.decode("ascii")
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _hostname():
    return (request.host or "").split(":")[0]


def _rp_id():
    """rp_id sent to browser. Must be a domain, never an IP."""
    h = _hostname()
    if h in ("localhost", "127.0.0.1", "::1"):
        return "localhost"
    return h


def register(app):

    # ─── Admin guard ───
    def admin_only(fn):
        @wraps(fn)
        def w(*a, **kw):
            if not getattr(g, "user", None) or g.user["role"] != "ADMIN":
                abort(403)
            return fn(*a, **kw)
        return w

    # ═══════════════════════════════════════════════════════════
    # Has-credentials check (public — used by login page)
    # ═══════════════════════════════════════════════════════════
    @app.route("/webauthn/has-credentials", methods=["GET", "POST"])
    def webauthn_has_credentials():
        try:
            r = one("""SELECT COUNT(*) AS n FROM webauthn_credentials c
                       JOIN users u ON u.id = c.user_id
                       WHERE u.role='ADMIN' AND u.active=1""")
            n = r["n"] if r else 0
            return jsonify(available=(n > 0), count=n)
        except Exception as e:
            return jsonify(available=False, count=0, error=str(e))

    # ═══════════════════════════════════════════════════════════
    # Manage page (admin only)
    # ═══════════════════════════════════════════════════════════
    @app.route("/webauthn/manage")
    @admin_only
    def webauthn_manage():
        creds = query("""SELECT * FROM webauthn_credentials
                         WHERE user_id = ? ORDER BY id DESC""", (g.user["id"],))
        return render_template("webauthn_manage.html",
                               creds=creds,
                               rp_id=_rp_id(),
                               hostname=_hostname())

    # ═══════════════════════════════════════════════════════════
    # Register — begin
    # ═══════════════════════════════════════════════════════════
    @app.post("/webauthn/register/begin")
    @admin_only
    def webauthn_register_begin():
        # WebAuthn only works if user is on localhost domain
        if _hostname() not in ("localhost", "127.0.0.1", "::1"):
            return jsonify(error=(
                "WebAuthn requires a domain. Please open the app at "
                "http://localhost:5000 instead of using an IP address."
            )), 400

        u = one("SELECT id, username, display_name FROM users WHERE id=?",
                (g.user["id"],))
        if not u:
            return jsonify(error="User not found."), 400

        challenge = secrets.token_bytes(32)
        session["_wa_reg_challenge"] = _b64u_enc(challenge)

        existing = query("""SELECT credential_id FROM webauthn_credentials
                            WHERE user_id = ?""", (u["id"],))
        exclude = [{"type": "public-key", "id": c["credential_id"]}
                   for c in existing]

        display = u["display_name"] or u["username"]
        options = {
            "challenge": _b64u_enc(challenge),
            "rp": {"id": _rp_id(), "name": RP_NAME},
            "user": {
                "id": _b64u_enc(str(u["id"])),
                "name": u["username"],
                "displayName": display,
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "timeout": 120000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "userVerification": "required",
                "residentKey": "required",
                "requireResidentKey": True,
            },
            "excludeCredentials": exclude,
        }
        return jsonify(options)

    # ═══════════════════════════════════════════════════════════
    # Register — complete
    # ═══════════════════════════════════════════════════════════
    @app.post("/webauthn/register/complete")
    @admin_only
    def webauthn_register_complete():
        ch = session.get("_wa_reg_challenge")
        if not ch:
            return jsonify(error="No challenge in session."), 400

        body = request.get_json(silent=True) or {}
        raw_id = body.get("rawId") or body.get("id")
        if not raw_id:
            return jsonify(error="Missing credential id."), 400

        # Verify client data challenge matches
        try:
            cd_b64 = body.get("response", {}).get("clientDataJSON", "")
            cd = json.loads(_b64u_dec(cd_b64))
            if cd.get("type") != "webauthn.create":
                return jsonify(error="Wrong clientData.type."), 400
            if cd.get("challenge") != ch:
                return jsonify(error="Challenge mismatch."), 400
        except Exception as e:
            return jsonify(error=f"Bad clientData: {e}"), 400

        att_obj = body.get("response", {}).get("attestationObject", "")
        transports = ",".join(body.get("transports") or [])
        label = (body.get("deviceName") or "Fingerprint")[:60]

        try:
            execute("""INSERT INTO webauthn_credentials
                       (user_id, credential_id, public_key, sign_count,
                        transports, name)
                       VALUES(?,?,?,?,?,?)""",
                    (g.user["id"], raw_id, att_obj, 0, transports, label))
        except Exception:
            return jsonify(error="This credential is already registered."), 400

        session.pop("_wa_reg_challenge", None)
        try:
            execute("""INSERT INTO audit_log
                       (user_id, action, target_type, target_id)
                       VALUES(?, 'WEBAUTHN_REGISTER', 'user', ?)""",
                    (g.user["id"], g.user["id"]))
        except Exception:
            pass
        return jsonify(ok=True, name=label)

    # ═══════════════════════════════════════════════════════════
    # Login — begin (public)
    # ═══════════════════════════════════════════════════════════
    @app.post("/webauthn/login/begin")
    def webauthn_login_begin():
        challenge = secrets.token_bytes(32)
        session["_wa_auth_challenge"] = _b64u_enc(challenge)

        options = {
            "challenge": _b64u_enc(challenge),
            "timeout": 120000,
            "rpId": _rp_id(),
            "userVerification": "required",
            "allowCredentials": [],
        }
        return jsonify(options)

    # ═══════════════════════════════════════════════════════════
    # Login — complete (public)
    # ═══════════════════════════════════════════════════════════
    @app.post("/webauthn/login/complete")
    def webauthn_login_complete():
        ch = session.get("_wa_auth_challenge")
        if not ch:
            return jsonify(error="No challenge in session."), 400

        body = request.get_json(silent=True) or {}
        raw_id = body.get("rawId") or body.get("id")
        if not raw_id:
            return jsonify(error="Missing credential id."), 400

        cred = one("""SELECT * FROM webauthn_credentials WHERE credential_id = ?""",
                   (raw_id,))
        if not cred:
            return jsonify(error="Credential not found. Enroll first."), 404

        u = one("SELECT * FROM users WHERE id=? AND active=1", (cred["user_id"],))
        if not u:
            return jsonify(error="User account is inactive."), 403
        if u["role"] != "ADMIN":
            return jsonify(error="Fingerprint login is admin-only."), 403

        # Verify client data
        try:
            cd_b64 = body.get("response", {}).get("clientDataJSON", "")
            cd = json.loads(_b64u_dec(cd_b64))
            if cd.get("type") != "webauthn.get":
                return jsonify(error="Wrong clientData.type."), 400
            if cd.get("challenge") != ch:
                return jsonify(error="Challenge mismatch — try again."), 400
        except Exception as e:
            return jsonify(error=f"Bad clientData: {e}"), 400

        # Update last used
        execute("""UPDATE webauthn_credentials
                   SET last_used=CURRENT_TIMESTAMP,
                       sign_count=COALESCE(sign_count,0) + 1
                   WHERE id=?""", (cred["id"],))

        # Log in
        session.pop("_wa_auth_challenge", None)
        session.clear()
        session["user_id"] = u["id"]
        session["_csrf"] = secrets.token_urlsafe(32)
        execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (u["id"],))
        try:
            execute("""INSERT INTO audit_log
                       (user_id, action, target_type, target_id)
                       VALUES(?, 'LOGIN_WEBAUTHN', 'user', ?)""",
                    (u["id"], u["id"]))
        except Exception:
            pass
        return jsonify(ok=True, redirect=url_for("dashboard"))

    # ═══════════════════════════════════════════════════════════
    # Delete / rename
    # ═══════════════════════════════════════════════════════════
    @app.post("/webauthn/credential/<int:cid>/delete")
    @admin_only
    def webauthn_delete(cid):
        c = one("""SELECT * FROM webauthn_credentials
                   WHERE id=? AND user_id=?""", (cid, g.user["id"]))
        if not c:
            abort(404)
        execute("DELETE FROM webauthn_credentials WHERE id=?", (cid,))
        flash("Fingerprint removed.", "success")
        return redirect(url_for("webauthn_manage"))

    @app.post("/webauthn/credential/<int:cid>/rename")
    @admin_only
    def webauthn_rename(cid):
        c = one("""SELECT * FROM webauthn_credentials
                   WHERE id=? AND user_id=?""", (cid, g.user["id"]))
        if not c:
            abort(404)
        name = (request.form.get("name") or "Fingerprint")[:60]
        execute("UPDATE webauthn_credentials SET name=? WHERE id=?", (name, cid))
        flash("Renamed.", "success")
        return redirect(url_for("webauthn_manage"))
