# -*- coding: utf-8 -*-
"""普通代理模式下的抓包插件：只记录桃园域名，其它流量原样放行。

与 sni.py 的区别：不改 SNI、不改 Host——代理模式里客户端本来就连对了域名，
改反而会把微信其它请求搞坏。
"""
import json
import time

LOG = r"D:\ty_scan\clock.jsonl"
HOST = "olwxbbs.sanguosha.com"


class Cap:
    def response(self, flow):
        try:
            if HOST not in (flow.request.pretty_host or ""):
                return
            rec = {
                "t": time.strftime("%H:%M:%S"),
                "src": "proxy",
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "req_headers": dict(flow.request.headers),
                "req_body": (flow.request.get_text(strict=False) or "")[:5000],
                "status": flow.response.status_code,
                "resp_headers": dict(flow.response.headers),
                "resp_body": (flow.response.get_text(strict=False) or "")[:8000],
            }
        except Exception as exc:
            rec = {"t": time.strftime("%H:%M:%S"), "error": str(exc)}
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


addons = [Cap()]