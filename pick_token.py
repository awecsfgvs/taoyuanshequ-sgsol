# -*- coding: utf-8 -*-
r"""从 clock.jsonl 里取最新的 wx/login token。

为什么不用「直接正则扫文件」：sni.py 用 json.dumps 写记录，响应体里的引号
会被转义成 \"，raw 文本里长这样： \"token\":\"eyJ...
所以把 '"token"\s*:' 当正则去扫永远匹配不到（这正是 11-06 那次抓包成功
却报「没抓到 token」的原因）。这里走 json.loads 解出 resp_body 再取。
"""
import json
import os
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clock.jsonl")


def main() -> int:
    try:
        fh = open(LOG, encoding="utf-8", errors="ignore")
    except OSError:
        return 1
    token = ""
    with fh:
        for line in fh:
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
            i = body.find('"token":"eyJ')
            if i < 0:
                continue
            tail = body[i + 9:]
            cand = tail[:tail.find('"')]
            if cand.startswith("eyJ"):
                token = cand
    if token:
        sys.stdout.write(token)
        return 0
    return 1


raise SystemExit(main())
