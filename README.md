# taoyuanshequ-sgsol

三国杀OL 「桃园社区」小程序每日任务自动化 —— 签到、点赞、浏览、领奖、复核，一条命令跑完。

纯 HTTP 实现，不需要模拟器、不需要 hook 客户端。签名算法从 `api/base.js` 逆出，认证只需要一个小程序登录态 JWT。

> 自用脚本，接口随官方版本可能变动。详见文末「说明」。

## 它做什么

一次运行完成 5 件事：

1. **签到** —— `GET /v1/user/clock/info` 查状态，未签则 `POST /v1/user/clock {"type":1}`
2. **点赞 5 条** —— 从推荐流里挑没点过的帖子 `POST /v1/thread/like {"tid":N}`
3. **浏览 5 条** —— `GET /v1/thread/detail?tid=N`，触发浏览任务计数
4. **领一次性任务奖励** —— 扫 `/v1/user/task`，把 `is_done` 且本地没领过的 `POST /v1/task/once/finish`
5. **复核 + 记流水** —— 打印粮草余额、连续签到天数、五项每日任务进度、当日粮草收支明细

脚本自带**当日去重**（`daily_done.json`），同一天重复触发只会写一行「已经跑过了，跳过」，不会重复点赞或重复领奖。

## 目录

| 文件 | 作用 |
|---|---|
| `tyapi.py` | API 客户端：签名、会话、`call()` |
| `taoyuan_daily.py` | 每日全套（签到+点赞+浏览+领奖+复核） |
| `taoyuan_checkin.py` | 只签到，单独跑（查状态 / 签 / 复核） |
| `taoyuan_claim.py` | 只领奖，给「社区发言」这类要人工先做的任务用 |
| `check_health.py` | 健康自检：token 剩余天数、今天跑没跑、日志报错、真调一次接口 |
| `run_daily.bat` / `run_claim.bat` / `run_check.bat` | Windows 双击入口 |
| `续期token.bat` + `refresh_token.ps1` + `sni.py` | token 续期（hosts 劫持 + mitmproxy 反代抓登录响应） |
| `config.example.json` | 配置模板，复制成 `config.json` 填自己的 |

## 签名算法

```
sign = md5( "".join(f"{k}={v}" for k in sorted(params ∪ {timestamp})) + SALT )
SALT = EXWcjIzThnRLbLXguxzkxnToYcDlPTQp
```

参数按 key 升序拼 `k=v`，无分隔符，末尾接盐，取 md5 小写。`timestamp` 为秒级。注意：**签到、点赞、浏览这几个接口实测不校验 sign**，带上也不会错；有些接口会校验。

## 快速开始

```bash
pip install -r requirements.txt
cp config.example.json config.json
# 把 config.json 里的 token 换成自己的
python taoyuan_daily.py
```

`config.json`：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...（小程序登录态 JWT）",
  "uid": 123456,
  "exp": 1793717305,
  "captured_at": "2026-10-27T22:48:25+08:00"
}
```

只有 `token` 是必需的，`uid`/`exp` 仅用于展示和自检。JWT 里的 `sub` 就是 uid，`exp` 是签发后 7 天。

### 怎么拿 token

**方式一：手动抓包（推荐，最省事）**

用 Stream（iOS）/ Reqable、HTTP Canary（Android）抓微信小程序请求，打开桃园社区任意页面，找 `olwxbbs.sanguosha.com` 的请求，复制请求头 `authorization` 的值。也可以 PC 端用微信开发者工具打开小程序，在 Network 面板里找。

**方式二：本仓库自带的自动抓取**

`续期token.bat` → UAC 提权 → `refresh_token.ps1`：

1. 先解析 `olwxbbs.sanguosha.com` 真实 IP（必须在改 hosts 之前）
2. 往 hosts 写 `127.0.0.1 olwxbbs.sanguosha.com`
3. 起 `mitmdump --mode reverse:https://<ip>:443@443`，用 `sni.py` 修 SNI/Host 并落 `clock.jsonl`
4. 杀掉 `WeChatAppEx`，强制小程序重连（**这步之后要手动把小程序重新打开**）
5. 从捕获响应里正则提 `"token":"eyJ..."`，解 JWT payload 拿 `sub`/`exp`，写回 `config.json`
6. 无论成败都还原 hosts、关掉 443 监听

需要 `pip install mitmproxy`，并且真的要有管理员权限（改 hosts、占 443）。

⚠️ JWT 由 `wx.login` 的 code 一次性换取，**没法自己造**，所以每 7 天得续一次。续期这件事绕不开人工打开小程序。

## 定时跑

**Windows 计划任务**（最简单）：

```bat
schtasks /Create /TN TaoyuanCheckin /TR "cmd /c \"D:\path\to\run_daily.bat\"" /SC DAILY /ST 00:05
```

**Linux cron**：

```cron
5 0 * * * cd /path/to/taoyuanshequ-sgsol && /usr/bin/python3 taoyuan_daily.py >> daily.log 2>&1
```

**DSH / 青龙**等面板：把 `taoyuan_daily.py` 挂成 python 任务，时间每天 00:05。

时间很关键的一点：**服务端按自然日（00:00）重置，所以哪天跑就覆盖哪天的任务**，一天跑一次就够。选一个你的机器确定开着的时段，比如 **22:00**——比 00:05 靠谱得多，因为大多数人 00:05 前已经关机，任务只能等第二天开机才补跑。0 点整跑只在机器 24 小时开机时才有意义。

配一个自检更稳：`python check_health.py` 每天上午跑一次，token 快过期、当天没跑、日志有 `[!]` 报错都会让它返回非 0。

## 说明

- 仅用于自己账号的日常打卡，请自行评估风控与账号风险。
- 接口、签名盐、UA、referer 都来自小程序自身，官方更新版本后可能需要重新对一遍。
- 仓库里不含任何登录态：`config.json`、`*.log`、`daily_done.json`、`claimed.json`、`clock.jsonl` 全部在 `.gitignore` 里。
- 续期脚本会临时改 hosts、占用 443，脚本结束会还原；介意的话用方式一手动抓。