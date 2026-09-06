#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flix 调参自动化工具（经 WiFi MAVLink 与无人机通信）。

用法:
    python flix_tuning.py cmd <CLI命令>       执行任意串口命令并打印输出
    python flix_tuning.py status              连接 + 基本遥测 + time/imu 摘要
    python flix_tuning.py params [输出文件]    导出全量参数（默认 analysis/params_baseline.txt）
    python flix_tuning.py set <名> <值>        设置参数并回读验证
    python flix_tuning.py log [输出.csv]      抓取 log dump（默认 analysis/logs/log_<时间>.csv）
    python flix_tuning.py analyze <csv>       分析日志（调 log_analyzer）
    python flix_tuning.py monitor <秒>        监听遥测 N 秒（观察 armed/姿态/油门）
"""
import os
import re
import sys
import time
import datetime

sys.path.insert(0, r'd:\develop\quadcopter\source\flix-v1.2-20260325\tools')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyflix import Flix  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(BASE, 'logs')


def connect(timeout=30):
    print('等待无人机连接（需 PC 已连 Drone_WiFi 且无人机已上电）...')
    flix = Flix(wait_connection=False)
    if not flix.wait('mavlink.HEARTBEAT', timeout=timeout):
        raise SystemExit('超时：未收到心跳。检查无人机是否上电、PC 是否连上 Drone_WiFi。')
    time.sleep(0.5)
    print('已连接: mode=%s armed=%s landed=%s' % (flix.mode, flix.armed, flix.landed))
    return flix


def raw_listen(flix, prefix, timeout):
    """绕过 cli() 的短超时，自己收集 SERIAL_CONTROL 分片，返回完整文本或 None。"""
    chunks = []
    done = {'text': None}
    def on_full(text):
        if text.startswith(prefix):
            done['text'] = text[len(prefix):].strip()
    flix.on('print_full', on_full)
    deadline = time.time() + timeout
    while time.time() < deadline and done['text'] is None:
        time.sleep(0.05)
    flix.off('print_full')
    return done['text']


def cli(flix, cmd, timeout=3):
    out = raw_listen(flix, '> %s\n' % cmd, timeout)
    if out is None:  # 兜底走 pyflix 自带
        out = flix.cli(cmd)
    return out


def cmd_cmd(flix, args):
    print(cli(flix, ' '.join(args), timeout=8))


def cmd_status(flix, args):
    out = []
    for c in ('time', 'ps', 'mot'):
        out.append('=== %s ===\n%s' % (c, cli(flix, c)))
    e = flix.attitude_euler
    out.append('遥测: roll=%+.1f° pitch=%+.1f° yaw=%+.1f° rates=%s motor=%s' %
               (e[0], e[1], e[2],
                ['%.1f' % (r * 57.3) for r in flix.rates],
                ['%.2f' % m for m in (flix.motors or [])]))
    print('\n'.join(out))


def cmd_params(flix, args):
    text = cli(flix, 'p', timeout=8)
    path = args[0] if args else os.path.join(BASE, 'params_baseline.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# 导出时间 %s\n' % datetime.datetime.now().isoformat())
        f.write(text + '\n')
    n = len([l for l in text.splitlines() if '=' in l])
    print('已导出 %d 个参数 -> %s' % (n, path))


def cmd_set(flix, args):
    if len(args) != 2:
        raise SystemExit('用法: set <参数名> <值>')
    name, value = args[0], float(args[1])
    cli(flix, 'p %s %g' % (name, value))
    back = float(cli(flix, 'p %s' % name).split('=')[1])
    ok = abs(back - value) < 1e-6 * max(1, abs(value))
    print('%s = %g %s(回读 %g)' % (name, value, 'OK ' if ok else 'MISMATCH! ', back))
    if not ok:
        raise SystemExit(1)


def cmd_log(flix, args):
    os.makedirs(LOGDIR, exist_ok=True)
    path = args[0] if args else os.path.join(
        LOGDIR, 'log_%s.csv' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    text = raw_listen(flix, '> log dump\n', timeout=15)
    if text is None:
        raise SystemExit('log dump 未在 15s 内完成（WiFi 分片可能丢包），重试一次...')
    lines = [l for l in text.splitlines() if re.match(r'^[-\d.eE+,]+$', l)]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('已保存 %d 行 -> %s' % (len(lines), path))
    if len(lines) < 900:
        print('!! 行数偏少（满缓冲应为约 1000 行），可能存在 UDP 丢包，建议检查时间连续性')


def cmd_analyze(flix, args):
    from log_analyzer import analyze
    analyze(args[0])


def cmd_monitor(flix, args):
    secs = float(args[0]) if args else 5
    end = time.time() + secs
    while time.time() < end:
        e = flix.attitude_euler
        print('%s armed=%s mode=%s landed=%s roll=%+6.1f pitch=%+6.1f yaw=%+6.1f thr_mot=%s' %
              (time.strftime('%H:%M:%S'), flix.armed, flix.mode, flix.landed,
               e[0], e[1], e[2], ['%.2f' % m for m in (flix.motors or [])]))
        time.sleep(1)


COMMANDS = {'cmd': cmd_cmd, 'status': cmd_status, 'params': cmd_params,
            'set': cmd_set, 'log': cmd_log, 'analyze': cmd_analyze,
            'monitor': cmd_monitor}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(__doc__)
    action, args = sys.argv[1], sys.argv[2:]
    if action == 'analyze':  # 离线分析不需要连接
        from log_analyzer import analyze
        analyze(args[0])
        return
    flix = connect()
    COMMANDS[action](flix, args)


if __name__ == '__main__':
    main()
