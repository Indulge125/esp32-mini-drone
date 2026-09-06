#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flix 飞行日志分析器。

输入: `log dump` 输出的 CSV（列: t,rates.x,rates.y,rates.z,ratesTarget.x,ratesTarget.y,
ratesTarget.z,attitude.x,attitude.y,attitude.z,attitudeTarget.x,attitudeTarget.y,
attitudeTarget.z,thrustTarget，姿态为弧度）。

输出: 每轴角速率跟踪误差 RMS/峰值、振荡主频与幅值、稳态偏差、姿态角跟踪 RMS、
油门统计，并给出初步判定（OSC/LAZY/OK）与参数调整建议。

用法:
    python log_analyzer.py <csv文件> [--flight-thrust 0.15] [--json 输出.json]
"""
import argparse
import csv
import json
import math
import sys

import numpy as np

AXES = {'x': 'roll', 'y': 'pitch', 'z': 'yaw'}
DEG = 180.0 / math.pi


def load_csv(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        rows = [r for r in csv.reader(f) if r]
    header = rows[0]
    if header[0] != 't':
        raise SystemExit('文件不是 flix log dump 格式（第一列应为 t）: %s' % path)
    data = np.array([[float(v) for v in r] for r in rows[1:] if len(r) == len(header)])
    # 环形缓冲回绕后 dump 顺序会乱，按 t 排序
    order = np.argsort(data[:, 0])
    data = data[order]
    idx = {name: i for i, name in enumerate(header)}
    return header, idx, data


def dominant_freq(t, sig, fmin=1.5, fmax=40.0):
    """返回显著振荡主频(Hz)与该频段峰值功率占比。"""
    n = len(sig)
    if n < 32:
        return None, 0.0
    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt
    sig = sig - sig.mean()
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(sig * win)) ** 2
    freqs = np.fft.rfftfreq(n, dt)
    band = (freqs >= fmin) & (freqs <= fmax)
    if not band.any() or spec.sum() <= 0:
        return None, 0.0
    peak = int(np.argmax(spec * band))
    return float(freqs[peak]), float(spec[band].sum() / spec.sum())


def axis_report(t, rate, rate_t, att, att_t, thrust, fthrust):
    """单轴指标。rate 单位 rad/s，att 单位 rad。"""
    fly = thrust > fthrust          # 真正离地飞行段（怠速 0.1 不算）
    out = {'fly_samples': int(fly.sum())}
    if fly.sum() < 20:
        out['note'] = '有效飞行样本不足（油门未超过阈值），跳过该轮分析'
        return out

    tf, rf, rtf = t[fly], rate[fly], rate_t[fly]
    err = (rf - rtf) * DEG          # 实际 - 目标, deg/s
    out['rate_err_rms'] = round(float(np.sqrt(np.mean(err ** 2))), 2)
    out['rate_err_p2p'] = round(float(err.max() - err.min()), 2)
    out['rate_err_mean'] = round(float(err.mean()), 2)   # 持续为负=跟不上目标
    f, share = dominant_freq(tf, err)
    out['osc_freq_hz'] = round(f, 2) if f else None
    out['osc_band_power'] = round(share, 3)
    # 主频处的近似幅值
    if f:
        lo, hi = f * 0.8, f * 1.25
        m = (tf >= tf[0])  # 占位
        sig = err - err.mean()
        n = len(sig)
        dt = float(np.median(np.diff(tf)))
        spec = np.abs(np.fft.rfft(sig * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, dt)
        bandm = (freqs >= lo) & (freqs <= hi)
        out['osc_amp_degs'] = round(float(2 * spec[bandm].max() / n * math.sqrt(2)), 2) if bandm.any() else None

    # 姿态跟踪（角度环，deg）
    af = att[fly] * DEG
    atf = att_t[fly] * DEG
    aerr = af - atf
    out['att_err_rms'] = round(float(np.sqrt(np.mean(aerr ** 2))), 2)
    out['att_mean'] = round(float(af.mean()), 2)     # 悬停时的平均角（漂移方向参考）
    out['att_p2p'] = round(float(af.max() - af.min()), 2)

    out['thrust_mean'] = round(float(thrust[fly].mean()), 3)
    out['thrust_max'] = round(float(thrust[fly].max()), 3)
    out['duration_s'] = round(float(tf[-1] - tf[0]), 1)

    # 判定
    notes = []
    osc = (out.get('osc_amp_degs') or 0) > 8 and out.get('osc_band_power', 0) > 0.4 \
        and out['rate_err_p2p'] > 25 and (out['osc_freq_hz'] or 0) <= 30
    if osc:
        notes.append('OSC(角速率振荡 f=%sHz amp=%s°/s 峰峰=%.0f°/s) → 降rate P 或升 rate D' %
                     (out['osc_freq_hz'], out['osc_amp_degs'], out['rate_err_p2p']))
    elif out['rate_err_rms'] > 20:
        notes.append('WEAK(角速率跟踪差 rms=%s°/s) → 升 rate P' % out['rate_err_rms'])
    if abs(out['rate_err_mean']) > 8:
        notes.append('BIAS(稳态偏差 %s°/s) → 升 rate I 或 P' % out['rate_err_mean'])
    if out['att_err_rms'] > 8:
        notes.append('ATT(姿态跟踪差 rms=%s°) → 降角度环 P' % out['att_err_rms'])
    if not notes:
        notes.append('OK')
    out['verdict'] = '; '.join(notes)
    return out


def analyze(path, flight_thrust=0.15, json_out=None):
    header, idx, data = load_csv(path)
    t = data[:, idx['t']]
    report = {
        'file': path,
        'samples': int(len(data)),
        't_range_s': [round(float(t[0]), 2), round(float(t[-1]), 2)],
        'dt_median_ms': round(float(np.median(np.diff(t)) * 1000), 2),
    }
    # t 大间隔 = 记录断点（解锁前后的旧数据/重启）
    gaps = np.diff(t)
    big = gaps[gaps > 0.5]
    if len(big):
        report['t_gaps_over_0.5s'] = [round(float(g), 2) for g in big[:5]]

    axes = {}
    for ax, name in AXES.items():
        axes[name] = axis_report(
            t,
            data[:, idx['rates.%s' % ax]], data[:, idx['ratesTarget.%s' % ax]],
            data[:, idx['attitude.%s' % ax]], data[:, idx['attitudeTarget.%s' % ax]],
            data[:, idx['thrustTarget']], flight_thrust)
    report['axes'] = axes

    print('=' * 72)
    print('flix 飞行日志分析: %s' % path)
    print('样本 %d, 时间 %.2f~%.2fs, 中位 dt %.2fms' %
          (report['samples'], t[0], t[-1], report['dt_median_ms']))
    if 't_gaps_over_0.5s' in report:
        print('!! 时间轴存在大间隔 %s —— 可能混入解锁前旧数据或发生重启' % report['t_gaps_over_0.5s'])
    for name, r in axes.items():
        print('-' * 72)
        print('[%s]' % name)
        if 'note' in r:
            print('  %s' % r['note'])
            continue
        print('  飞行段 %.1fs, 油门 mean %.3f max %.3f' %
              (r['duration_s'], r['thrust_mean'], r['thrust_max']))
        print('  角速率误差: RMS %.1f°/s, 峰峰 %.1f°/s, 均值 %+.1f°/s' %
              (r['rate_err_rms'], r['rate_err_p2p'], r['rate_err_mean']))
        print('  振荡估计: 主频 %s Hz, 频段功率占比 %.2f, 幅值 %s °/s' %
              (r['osc_freq_hz'], r['osc_band_power'], r.get('osc_amp_degs')))
        print('  姿态: 跟踪RMS %.2f°, 平均角 %+.2f°, 峰峰 %.2f°' %
              (r['att_err_rms'], r['att_mean'], r['att_p2p']))
        print('  判定: %s' % r['verdict'])
    print('=' * 72)
    if json_out:
        with open(json_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print('JSON 已存: %s' % json_out)
    return report


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--flight-thrust', type=float, default=0.15)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    analyze(a.csv, a.flight_thrust, a.json)
