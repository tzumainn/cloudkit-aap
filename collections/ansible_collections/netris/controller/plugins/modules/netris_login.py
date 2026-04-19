# Copyright (c) 2025 OSAC Project. Apache-2.0.

"""Obtain Netris API session cookie (connect.sid) via POST /api/auth."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            username=dict(type="str", required=True),
            password=dict(type="str", required=True, no_log=True),
            timeout=dict(type="int", default=30),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=False,
    )
    base = module.params["url"].rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "https" or not parsed.netloc:
        module.fail_json(msg="url must be an absolute https:// controller URL")
    auth_url = base + "/api/auth"
    data = json.dumps({
        "user": module.params["username"],
        "password": module.params["password"],
        "auth_scheme_id": 1,
    }).encode("utf-8")
    req = urllib.request.Request(auth_url, data=data, method="POST", headers={"Content-Type": "application/json"})
    ctx = ssl.create_default_context()
    if not module.params["validate_certs"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=module.params["timeout"]) as resp:
            if resp.status != 200:
                module.fail_json(msg="Netris login failed: status %s" % resp.status, status=resp.status)
            # Get Set-Cookie (may be multiple headers)
            set_cookies = resp.headers.get_all("Set-Cookie") or [resp.headers.get("Set-Cookie", "")]
            set_cookie = "; ".join(h for h in set_cookies if h)
    except urllib.error.HTTPError as e:
        module.fail_json(msg="Netris login failed: %s" % e, status=e.code)
    except urllib.error.URLError as e:
        module.fail_json(msg="Netris login failed: %s" % e.reason)
    if not set_cookie:
        module.fail_json(msg="Netris login did not return Set-Cookie")
    sid = None
    for part in set_cookie.split(";"):
        part = part.strip()
        if part.startswith("connect.sid="):
            sid = part.split("=", 1)[1].strip()
            if len(sid) >= 2 and sid[0] == '"' and sid[-1] == '"':
                sid = sid[1:-1]
            break
    if not sid:
        module.fail_json(msg="Netris login did not return connect.sid cookie")
    module.exit_json(changed=False, session_cookie=sid)


if __name__ == "__main__":
    main()
