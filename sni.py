# -*- coding: utf-8 -*-
"""劫持 olwxbbs.sanguosha.com：修 SNI + 修 Host + 落 jsonl。"""
import json, os, time

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clock.jsonl")
HOST = "olwxbbs.sanguosha.com"


class Cap:
    def tls_start_server(self, data):
        try:
            data.conn.sni = HOST
        except Exception:
            pass

    def requestheaders(self, flow):
        try:
            flow.request.headers["Host"] = HOST
            flow.request.headers["Referer"] = f"https://servicewechat.com/wx88a45073e0660980/193/page-frame.html"
        except Exception:
            pass

    def response(self, flow):
        try:
            rec = {
                "t": time.strftime("%H:%M:%S"),
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "req_headers": dict(flow.request.headers),
                "req_body": (flow.request.get_text(strict=False) or "")[:5000],
                "status": flow.response.status_code,
                "resp_headers": dict(flow.response.headers),
                "resp_body": (flow.response.get_text(strict=False) or "")[:8000],
            }
        except Exception as e:
            rec = {"t": time.strftime("%H:%M:%S"), "error": str(e)}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


addons = [Cap()]