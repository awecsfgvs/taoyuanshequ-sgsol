# -*- coding: utf-8 -*-
"""桃园社区 API 客户端：已破解签名。

sign = md5( "".join(f"{k}={v}" for k in sorted(params ∪ {timestamp})) + SALT )

SALT = EXWcjIzThnRLbLXguxzkxnToYcDlPTQp   (api/base.js 里的 c)
"""
import hashlib
import json
import os
import sys
import time

import requests

BASE = "https://olwxbbs.sanguosha.com"
SALT = "EXWcjIzThnRLbLXguxzkxnToYcDlPTQp"
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) "
      "NetType/WIFI MiniProgramEnv/Windows WindowsWechat")
REFERER = "https://servicewechat.com/wx88a45073e0660980/193/page-frame.html"


def sign(params: dict) -> dict:
    """返回带 timestamp + sign 的新参数字典（不改原对象）。"""
    p = {k: v for k, v in params.items() if k not in ("sign",)}
    p["timestamp"] = int(time.time())
    raw = "".join(f"{k}={p[k]}" for k in sorted(p)) + SALT
    p["sign"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
    if os.environ.get("TY_DEBUG_SIGN"):
        print(f"    [sign] {raw} -> {p['sign']}")
    return p


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "authorization": token,
        "user-agent": UA,
        "referer": REFERER,
        "xweb_xhr": "1",
        "content-type": "application/json",
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
    })
    return s


def call(s, path, params=None, method="GET", body=None, signed=True, timeout=20):
    url = BASE + path
    if signed:
        params = sign(params or {})
    if method == "GET":
        r = s.get(url, params=params, timeout=timeout)
    else:
        r = s.post(url, params=params, data=json.dumps(body or {}), timeout=timeout)
    try:
        j = r.json()
    except Exception:
        return {"code": -999, "msg": f"非JSON HTTP{r.status_code}", "raw": r.text[:200]}
    return j


def load_token():
    if not os.path.exists(CONFIG):
        raise SystemExit(
            "[!] 缺少 config.json —— 先执行: copy config.example.json config.json\n"
            "    然后把小程序登录态 JWT 填进 token 字段（见 README「怎么拿 token」）")
    with open(CONFIG, encoding="utf-8") as f:
        try:
            token = (json.load(f) or {}).get("token") or ""
        except ValueError:
            raise SystemExit("[!] config.json 不是合法 JSON")
    if not str(token).strip():
        raise SystemExit("[!] config.json 的 token 字段是空的")
    return str(token).strip()


if __name__ == "__main__":
    s = make_session(load_token())
    r = call(s, "/v1/thread/recommend", {"page": 1, "sort": 0})
    print("code =", r.get("code"), "msg =", r.get("msg"))
    d = r.get("data")
    if isinstance(d, dict):
        keys = list(d.keys())
        print("data keys:", keys[:10])
        lst = d.get("list") or d.get("data") or []
    elif isinstance(d, list):
        lst = d
    else:
        lst = []
    print("条数:", len(lst))
    for it in lst[:8]:
        if isinstance(it, dict):
            print("  id=", it.get("id"), "| title=", str(it.get("title") or it.get("subject"))[:50])
    if not lst:
        print(json.dumps(d, ensure_ascii=False)[:900])