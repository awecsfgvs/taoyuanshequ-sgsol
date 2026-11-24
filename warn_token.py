# -*- coding: utf-8 -*-
"""token 临期/过期时的桌面弹窗提醒。每次登录跑一次，同一次到期只弹一次。"""
import ctypes
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")
FLAG = os.path.join(HERE, ".token_warned")
LIMIT = 1.2 * 86400


def popup(text, title="桃园签到"):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)


def main():
    try:
        with open(CFG, encoding="utf-8") as fh:
            cfg = json.load(fh)
        left = cfg["exp"] - time.time()
    except Exception as exc:
        popup("读不到 config.json：%s\n\n双击 D:\\ty_scan\\续期token.bat" % exc)
        return 1

    if left >= LIMIT:
        return 0

    key = "expired" if left <= 0 else "soon"
    stamp = key + str(cfg["exp"])
    try:
        with open(FLAG, encoding="utf-8") as fh:
            if fh.read().strip() == stamp:
                return 0
    except OSError:
        pass

    if left <= 0:
        msg = (
            "桃园 token 已过期 {:.1f} 天，签到与任务全部失败。\n\n"
            "1) 双击 D:\\ty_scan\\续期token.bat，UAC 点「是」\n"
            "2) 微信里重新打开三国杀OL/桃园小程序任意页面\n"
            "3) 抓完跑 python D:\\ty_scan\\taoyuan_daily.py 补当天"
        ).format(-left / 86400)
    else:
        msg = (
            "桃园 token 只剩 {:.1f} 天（{} 到期）。\n\n"
            "双击 D:\\ty_scan\\续期token.bat 续掉，别等过期。"
        ).format(left / 86400, time.strftime("%m-%d %H:%M", time.localtime(cfg["exp"])))

    popup(msg)
    with open(FLAG, "w", encoding="utf-8") as fh:
        fh.write(stamp)
    return 0


raise SystemExit(main())