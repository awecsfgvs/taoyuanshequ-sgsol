# -*- coding: utf-8 -*-
"""
桃园社区（三国杀OL）小程序 自动签到

接口（2026-10-27 抓包实测）：
    GET  /v1/user/clock/info   -> 签到状态  is_clock / clock_days
    POST /v1/user/clock        -> 签到  body {"type":1}
    GET  /v1/user/clock/gift?type=1 -> 签到奖励表
    GET  /v1/user/clock/subscribe   -> 订阅提醒

认证：仅需头部 authorization: <JWT>
       JWT 里 sub=uid, exp=签发后 7 天
       这些接口不校验 timestamp/sign，随便带不带都行
"""
import json
import os
import sys
import time
from datetime import datetime

import requests

BASE = "https://olwxbbs.sanguosha.com"
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
LOG = os.path.join(HERE, "checkin.log")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) "
      "NetType/WIFI MiniProgramEnv/Windows WindowsWechat")
REFERER = "https://servicewechat.com/wx88a45073e0660980/193/page-frame.html"


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "authorization": token,
        "content-type": "application/json",
        "user-agent": UA,
        "referer": REFERER,
        "xweb_xhr": "1",
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
    })
    return s


def call(s: requests.Session, path: str, method: str = "GET", body=None, timeout=20) -> dict:
    url = BASE + path
    if method == "GET":
        r = s.get(url, timeout=timeout)
    else:
        r = s.post(url, data=json.dumps(body or {}), timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"code": -999, "msg": "非 JSON 响应", "raw": r.text[:300]}


def jwt_exp(token: str):
    """不验签，只读 payload 里的 exp。"""
    try:
        import base64
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p)).get("exp")
    except Exception:
        return None


def main() -> int:
    cfg = load_config()
    token = (cfg.get("token") or "").strip()
    if not token:
        log("[!] config.json 里没有 token")
        return 2

    exp = jwt_exp(token)
    if exp:
        left = exp - int(time.time())
        days = left / 86400
        log(f"[*] token 剩余 {days:.1f} 天（exp={exp}）")
        if left < 86400:
            log("[!] token 不足 1 天，需要重新打开小程序抓一次")

    s = make_session(token)

    # 1) 查状态
    info = call(s, "/v1/user/clock/info")
    if info.get("code") != 0:
        log(f"[!] 查询签到状态失败: {info}")
        return 3
    d = info.get("data") or {}
    log(f"[*] uid={cfg.get('uid')} 昵称={d.get('nickname')} "
        f"已连续签到={d.get('clock_days')}天 今日已签={d.get('is_clock')} 粮草={d.get('grain')}")

    if d.get("is_clock"):
        log("[=] 今天已经签过，跳过")
        return 0

    # 2) 签到
    res = call(s, "/v1/user/clock", method="POST", body={"type": 1})
    if res.get("code") != 0:
        if "已签到" in str(res.get("msg") or ""):
            log("[=] 服务端回「今日已签到」，视为完成")
            return 0
        log(f"[!] 签到失败: {res}")
        return 4
    rd = res.get("data") or {}
    log(f"[+] 签到成功！今日奖励: {rd.get('today_gift_name')} x{rd.get('today_gift_num')}  "
        f"连续奖励: {rd.get('gift_name')} x{rd.get('gift_num')}")

    # 3) 复核
    time.sleep(1)
    info2 = call(s, "/v1/user/clock/info")
    d2 = info2.get("data") or {}
    if d2.get("is_clock"):
        log(f"[✓] 复核通过：已签={d2.get('is_clock')} 连续={d2.get('clock_days')}天 粮草={d2.get('grain')}")
        return 0
    log(f"[!] 复核未通过: {info2}")
    return 5


if __name__ == "__main__":
    sys.exit(main())