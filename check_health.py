# -*- coding: utf-8 -*-
"""桃园社区日常任务 健康自检

每项检查给出 OK / WARN / FAIL，任何 WARN/FAIL 都会让退出码非 0，
方便 DSH cron 的运行记录里一眼看出问题。

检查项：
  1. token 是否还在有效期（config.json exp），剩余天数
  2. 今天是否已经跑过（daily_done.json）
  3. daily.log 最后一条运行结果
  4. --probe：真调一次 /v1/user/clock/info 验证 token 服务端仍有效
"""
import json
import os
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
DONE = os.path.join(HERE, "daily_done.json")
LOG = os.path.join(HERE, "daily.log")
HEALTH = os.path.join(HERE, "health.log")

WARN_DAYS = 2          # 剩余天数 <= 这个值就告警
problems = []


def say(tag, msg):
    line = f"[{tag}] {msg}"
    print(line)
    return line


def check_token():
    try:
        c = json.load(open(CONFIG, encoding="utf-8"))
    except Exception as e:
        problems.append("config.json 读取失败")
        return say("FAIL", f"config.json 读取失败: {e}")
    exp = c.get("exp")
    if not exp:
        problems.append("config.json 缺 exp")
        return say("FAIL", "config.json 缺 exp 字段")
    left = (exp - time.time()) / 86400
    when = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
    if left <= 0:
        problems.append("token 已过期")
        return say("FAIL", f"token 已于 {when} 过期，签到会全部失败 -> 双击 续期token.bat")
    if left <= WARN_DAYS:
        problems.append(f"token 仅剩 {left:.1f} 天")
        return say("WARN", f"token 仅剩 {left:.1f} 天（{when} 到期）-> 找时间双击 续期token.bat")
    return say("OK", f"token 有效，剩 {left:.1f} 天（{when} 到期）")


def check_today():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        d = json.load(open(DONE, encoding="utf-8")).get("date")
    except Exception:
        d = None
    if d == today:
        return say("OK", f"今天（{today}）已执行完毕")
    problems.append(f"今天({today})还没跑，上次完成 {d}")
    return say("WARN", f"今天（{today}）还没跑，daily_done.json = {d}")


def check_log():
    if not os.path.exists(LOG):
        return say("WARN", "daily.log 不存在，脚本还没跑过")
    lines = open(LOG, encoding="utf-8", errors="replace").read().splitlines()
    tail = [x for x in lines if x.strip()][-6:]
    if not tail:
        return say("WARN", "daily.log 是空的")
    print("    最近日志:")
    for x in tail:
        print("      " + x)
    bad = [x for x in tail
           if "[!]" in x and "token 已于" not in x]   # 过期预检不算真报错，上面已单独 FAIL
    if bad:
        problems.append("最近日志里有 [!] 报错")
        return say("WARN", f"最近日志出现 {len(bad)} 条 [!] 报错")
    return say("OK", "最近日志没有报错")


def probe():
    try:
        sys.path.insert(0, HERE)
        from tyapi import make_session, call, load_token
        s = make_session(load_token())
        last = None
        for attempt in range(3):
            try:
                ci = call(s, "/v1/user/clock/info")
                break
            except Exception as e:      # SSL/连接抖动：重试，别误报
                last = e
                time.sleep(5)
        else:
            problems.append(f"接口探测异常: {last}")
            return say("FAIL", f"接口探测异常（重试 3 次）: {last}")
        if ci.get("code") != 0:
            problems.append(f"接口探测失败 code={ci.get('code')}")
            return say("FAIL", f"接口探测失败 code={ci.get('code')} msg={ci.get('msg')}")
        d = ci.get("data") or {}
        return say("OK", f"接口正常：is_clock={d.get('is_clock')} 连续={d.get('clock_days')}天 粮草={d.get('grain')}")
    except Exception as e:
        problems.append(f"接口探测异常: {e}")
        return say("FAIL", f"接口探测异常: {e}")


def main():
    print(f"===== 桃园日常自检 {datetime.now():%Y-%m-%d %H:%M:%S} =====")
    check_token()
    check_today()
    check_log()
    if "--no-probe" not in sys.argv:
        probe()
    if problems:
        print("结论: 需要处理 -> " + "；".join(problems))
        code = 1
    else:
        print("结论: 一切正常")
        code = 0
    try:
        with open(HEALTH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} problems={problems or 'none'}\n")
    except Exception:
        pass
    return code


if __name__ == "__main__":
    sys.exit(main())