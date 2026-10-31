# -*- coding: utf-8 -*-
"""
桃园社区 快速领奖（配合「社区发言」等需要人工完成的任务）

扫一遍任务列表，把所有 is_done=true 且本地没领过的任务领掉。
本地用 claimed.json 记录已领过的 task_id，避免反复请求。

用法：
    python taoyuan_claim.py          # 领一轮
    python taoyuan_claim.py --force  # 无视本地记录，全部再领一遍
"""
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tyapi import make_session, call, load_token

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "claim.log")
STATE = os.path.join(HERE, "claimed.json")


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(d: dict) -> None:
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def main() -> int:
    force = "--force" in sys.argv
    s = make_session(load_token())
    rt = call(s, "/v1/user/task")
    if rt.get("code") != 0:
        log(f"[!] 任务列表失败: {rt.get('msg')}")
        return 1
    d = rt.get("data") or {}
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")

    todo = []
    for t in (d.get("once_task") or []):
        if not t.get("is_done"):
            continue
        tid = str(t.get("id"))
        if not force and state.get(tid) == today:
            continue
        todo.append(t)

    if not todo:
        log(f"[=] 没有待领任务（粮草 {d.get('grain')}）")
        return 0

    log(f"[*] 待领 {len(todo)} 个: " + ", ".join(t["name"] for t in todo))
    got = 0
    for t in todo:
        tid = t.get("id")
        res = call(s, "/v1/task/once/finish", {"task_id": tid}, method="POST")
        if res.get("code") == 0:
            got += 1
            log(f"[+] 领取 {tid} {t.get('name')}")
            state[str(tid)] = today
        else:
            log(f"[!] {tid} {t.get('name')} -> {res.get('msg')}")
        time.sleep(1)

    save_state(state)
    time.sleep(1)
    rt2 = call(s, "/v1/user/task")
    g = (rt2.get("data") or {}).get("grain")
    log(f"[*] 本轮领取 {got} 个，当前粮草 {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())