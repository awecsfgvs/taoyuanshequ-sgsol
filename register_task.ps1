# 注册桃园日常的 Windows 兜底计划任务
# 作用：DSH 没开着 / DSH cron 没触发时，每天 22:10 补跑一次
# 去重：taoyuan_daily.py 自己会读 daily_done.json，DSH 已跑过就直接跳过，不会重复点赞
$ErrorActionPreference = 'Stop'

$name = 'TaoyuanCheckin'
$bat  = 'D:\ty_scan\run_daily.bat'

# 已有同名任务先删掉，保证参数是新的
$old = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($old) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }

$action  = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$bat`"" -WorkingDirectory 'D:\ty_scan'
$trigger = New-ScheduledTaskTrigger -Daily -At '22:10'
$sett    = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
             -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
             -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $sett `
  -Description '桃园社区每日任务兜底（DSH cron 主跑，22:10 补跑，脚本自带当日去重）' `
  -User $env:USERNAME | Out-Null

$t = Get-ScheduledTask -TaskName $name
$i = Get-ScheduledTaskInfo -TaskName $name
"registered : {0}" -f $t.TaskName
"state      : {0}" -f $t.State
"next run   : {0}" -f $i.NextRunTime
"last run   : {0} (result {1})" -f $i.LastRunTime, $i.LastTaskResult