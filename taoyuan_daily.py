# -*- coding: utf-8 -*-
"""
桃园社区（三国杀OL）小程序 每日全套

流程：
  1. 签到            GET  /v1/user/clock/info  -> POST /v1/user/clock  {"type":1}
  2. 点赞 5 个帖子    POST /v1/thread/like     {"tid": N}
  3. 浏览 5 个帖子    GET  /v1/thread/detail   ?tid=N
  4. 领已完成的任务   POST /v1/task/once/finish {"task_id": N}
  5. 复核 + 记流水    GET  /v1/user/task, /v1/user/grain/log

签名算法（api/base.js 逆向所得）：
  sign = md5( "k1=v1k2=v2..." + SALT )   参数按 key 升序，含 timestamp
  SALT = EXWcjIzThnRLbLXguxzkxnToYcDlPTQp
"""
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tyapi import make_session, call, load_token

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "daily.log")
CLAIMED = os.path.join(HERE, "claimed.json")

LIKE_TARGET = 5
VIEW_TARGET = 5


def _load_claimed() -> dict:
    try:
        with open(CLAIMED, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_claimed(d: dict) -> None:
    try:
        with open(CLAIMED, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def do_clock(s) -> None:
    info = call(s, "/v1/user/clock/info")
    if info.get("code") != 0:
        log(f"[!] 签到状态查询失败: {info.get('msg')}")
        return
    d = info.get("data") or {}
    if d.get("is_clock"):
        log(f"[=] 今日已签到（连续 {d.get('clock_days')} 天，粮草 {d.get('grain')}）")
        return
    res = call(s, "/v1/user/clock", {"type": 1}, method="POST")
    if res.get("code") == 0:
        rd = res.get("data") or {}
        log(f"[+] 签到成功：{rd.get('today_gift_name')} x{rd.get('today_gift_num')}")
    elif "已签" in str(res.get("msg") or ""):
        log("[=] 服务端回今日已签到")
    else:
        log(f"[!] 签到失败: {res.get('msg')}")
    time.sleep(1)


def do_likes(s) -> int:
    r = call(s, "/v1/thread/recommend", {"page": 1, "sort": 0})
    lst = ((r.get("data") or {}).get("list")) or []
    if not lst:
        log("[!] 拿不到帖子列表")
        return 0
    n = 0
    for it in lst:
        if n >= LIKE_TARGET:
            break
        if it.get("isLike"):
            continue
        tid = it.get("tid")
        res = call(s, "/v1/thread/like", {"tid": tid}, method="POST")
        if res.get("code") == 0:
            n += 1
            log(f"[+] 点赞 tid={tid} {str(it.get('title'))[:24]}")
        else:
            log(f"[!] 点赞 tid={tid} 失败: {res.get('msg')}")
        time.sleep(1)
    return n


def do_views(s) -> int:
    r = call(s, "/v1/thread/recommend", {"page": 1, "sort": 0})
    lst = ((r.get("data") or {}).get("list")) or []
    n = 0
    for it in lst:
        if n >= VIEW_TARGET:
            break
        tid = it.get("tid")
        res = call(s, "/v1/thread/detail", {"tid": tid})
        if res.get("code") == 0:
            n += 1
            log(f"[+] 浏览 tid={tid} {str(it.get('title'))[:24]}")
        time.sleep(1)
    return n


def do_claims(s) -> int:
    rt = call(s, "/v1/user/task")
    if rt.get("code") != 0:
        log(f"[!] 任务列表失败: {rt.get('msg')}")
        return 0
    d = rt.get("data") or {}
    state = _load_claimed()
    today = datetime.now().strftime("%Y-%m-%d")
    got = 0
    for t in (d.get("once_task") or []):
        if not t.get("is_done"):
            continue
        tid = t.get("id")
        # once_task 是一次性任务：永久只领一次（服务端不幂等，重复领会白加粮草）
        if str(tid) in state:
            continue
        res = call(s, "/v1/task/once/finish", {"task_id": tid}, method="POST")
        if res.get("code") == 0:
            got += 1
            state[str(tid)] = today
            log(f"[+] 领取 task_id={tid} {t.get('name')}")
        else:
            log(f"[ ] task_id={tid} {t.get('name')} -> {res.get('msg')}")
        time.sleep(1)
    _save_claimed(state)
    return got


def summary(s) -> None:
    rt = call(s, "/v1/user/task")
    d = rt.get("data") or {}
    log(f"[*] 粮草={d.get('grain')} 连续签到={d.get('clock_days')}天")
    daily = d.get("daily_task") or []
    if daily:
        log("[*] 每日任务: " + "  ".join(
            f"{t['name']}={t['done']}/{t['target']}" for t in daily))
    time.sleep(1)
    rg = call(s, "/v1/user/grain/log", {"page": 1})
    lst = ((rg.get("data") or {}).get("list")) or []
    today = datetime.now().strftime("%Y-%m-%d")
    today_in = [x for x in lst if str(x.get("created_at", "")).startswith(today)]
    if today_in:
        total = sum(int(x.get("num") or 0) for x in today_in)
        log(f"[*] 今日粮草收支 {total:+d}: " + ", ".join(
            f"{x.get('desc')}{x.get('num'):+d}" for x in today_in[:8]))


DONE = os.path.join(HERE, "daily_done.json")


def _already_done(today: str) -> bool:
    try:
        with open(DONE, encoding="utf-8") as f:
            return json.load(f).get("date") == today
    except Exception:
        return False


def _mark_done(today: str) -> None:
    try:
        with open(DONE, "w", encoding="utf-8") as f:
            json.dump({"date": today}, f)
    except Exception:
        pass


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    if "--force" not in sys.argv and _already_done(today):
        log(f"[=] {today} 已经跑过了，跳过（要重跑加 --force）")
        return 0
    s = make_session(load_token())
    log("=" * 50)
    log("开始每日任务")
    do_clock(s)
    n_like = do_likes(s)
    n_view = do_views(s)
    log(f"[*] 本轮 点赞 {n_like} / 浏览 {n_view}")
    time.sleep(2)
    n_claim = do_claims(s)
    log(f"[*] 领取任务奖励 {n_claim} 个")
    time.sleep(1)
    summary(s)
    _mark_done(today)
    log("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())