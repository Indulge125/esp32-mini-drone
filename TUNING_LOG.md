# 四轴调参记录（TUNING_LOG）

> 固件：flix v1.2 魔改快照 ｜ 控制方式：QGC 手机虚拟摇杆 ｜ 数据链路：WiFi MAVLink（pyflix）
> 每轮飞行后由 `analysis/log_analyzer.py` 产出指标，参数快照由 `python analysis/flix_tuning.py params` 导出。

## 基线（2026-08-31，调参前）

来源：上次 QGC 悬停首飞的观察记录 —— 明显振荡/抖动、漂移/自转、响应迟钝/过窜、大油门易断电。

| 参数 | 出厂/当前值 | 含义 |
|---|---|---|
| CTL_R_RATE_P / CTL_P_RATE_P | 0.05 | roll/pitch 角速率 P |
| CTL_R_RATE_I / CTL_P_RATE_I | 0.2 | roll/pitch 角速率 I |
| CTL_R_RATE_D / CTL_P_RATE_D | 0.001 | roll/pitch 角速率 D |
| CTL_R_RATE_WU / CTL_P_RATE_WU | 0.3 | 积分限幅 |
| CTL_Y_RATE_P | 0.3 | yaw 角速率 P（I 项因 windup=0 无效，勿调） |
| CTL_R_P / CTL_P_P | 6 | roll/pitch 角度环 P |
| CTL_Y_P | 3 | yaw 角度环 P |
| CTL_TILT_MAX | 0.5236 rad (30°) | 自稳最大倾角 |
| CTL_R_RATE_MAX / CTL_P_RATE_MAX | 6.2832 rad/s (360°/s) | 角速率上限 |
| CTL_Y_RATE_MAX | 5.2360 rad/s (300°/s) | yaw 角速率上限 |
| EST_ACC_WEIGHT | 0.003 | 加速度修正权重（仅地面生效） |
| EST_RATES_LPF_A | 0.2 | 陀螺低通系数（~40Hz） |

完整快照见 `analysis/params_baseline.txt`。

## 诊断与调参轮次

| # | 时间 | 目的/改动 | 关键指标（roll/pitch/yaw） | 结论 |
|---|---|---|---|---|
| CHK | 08-31 | USB 自检（time/imu/ps/p/wifi） | loop 1000Hz，gyro bias 已滤净，参数=出厂默认 | 4项通过 |
| CHK2 | 08-31 | 180°旋转鉴别试验（实际旋转~65°，yaw 65.17°） | 旋转前 roll -5.19/pitch +0.92，旋转后 roll **-4.23**/pitch +1.64（符号未翻转） | **机体系固定误差（~4-5°）**，非桌面歪斜 |
| CHK3 | 08-31 | 重跑 `ca` 六面校准（拆桨） | bias X 1.331→**1.363**、Z -1.424→**-1.462**（两次差<0.03，复现性极好）；scale 几乎不变 | 传感器偏移真实且测量可重复 → 残差非"校准没校好"，缩小为 **IMU 模块安装歪斜** 或 轴间耦合/模型残差，待物理检查与 IMU_ROT 微调 |
| D0 | 待填 | 电源专项：拆桨油门阶梯 0.3/0.5/0.7/0.9 | 各级电池端电压 | 待填 |
| F1 | 待填 | 基线悬停（不改参数） | 待填 | 待填 |

## 指标目标

- 角速率跟踪误差 RMS < 10°/s，无 2~30Hz 等幅振荡（峰峰值 < 30°/s）
- 悬停姿态 |roll|,|pitch| < 5°，姿态跟踪 RMS < 3°
- 无持续自转
