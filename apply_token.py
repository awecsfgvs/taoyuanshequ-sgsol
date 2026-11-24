# -*- coding: utf-8 -*-
"""从 clock.jsonl 取最新 login token 写进 config.json，并校验有效期。

用法: python apply_token.py [--min-hours 1]
退出码: 0 写入成功 / 2 没找到 token / 3 token 即将过期
"""
import argparse
import base64
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "clock.jsonl")
CFG = os.path.join(HERE, "config.json")


def newest_token(skip_lines=0):
    token = ""
    seen = 0
    try:
        fh = open(LOG, encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    with fh:
        for line in fh:
            seen += 1
            if seen <= skip_lines:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if "wx/login" not in (rec.get("url") or ""):
                continue
            body = rec.get("resp_body") or ""
            idx = body.find('"token":"eyJ')
            if idx < 0:
                continue
            tail = body[idx + 9:]
            cand = tail[: tail.find('"')]
            if cand.startswith("eyJ"):
                token = cand
    return token


def claims(token):
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-hours", type=float, default=1.0)
    ap.add_argument("--skip-lines", type=int, default=0)
    args = ap.parse_args()

    token = newest_token(args.skip_lines)
    if not token:
        print("没在 clock.jsonl 里找到有效 login token")
        return 2

    data = claims(token)
    left = (data["exp"] - time.time()) / 3600
    if left < args.min_hours:
        print("token 只剩 %.1f 小时，太短，不写入（需要重新抓包）" % left)
        return 3

    old = {}
    try:
        with open(CFG, encoding="utf-8") as fh:
            old = json.load(fh)
    except Exception:
        pass

    cfg = {
        "token": token,
        "uid": data.get("sub") or old.get("uid"),
        "exp": data["exp"],
        "captured_at": datetime.datetime.fromtimestamp(
            data.get("iat", time.time())
        ).astimezone().isoformat(timespec="seconds"),
    }
    with open(CFG, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)

    print(
        "已写入 config.json：exp = %s（剩 %.1f 小时）"
        % (datetime.datetime.fromtimestamp(cfg["exp"]).strftime("%Y-%m-%d %H:%M"), left)
    )
    return 0


raise SystemExit(main())