# MHGU 高帧率贯通弹丢段修复

适用于 Monster Hunter Generations Ultimate **1.4.0**（Title ID `0100770008DD8000`，main 的 Build ID `FB08F1D20FD1204FE7070672777F869B`）。其他版本的代码地址不同，不能使用。

## 问题

用 60 帧 / 120 帧 cheat 运行游戏时，弩的贯通弹会丢段，伤害比 30 帧低，120 帧比 60 帧更严重。属性贯通弹和会反弹的通常弹 Lv3 也有同样的问题。

## 原因

- 游戏引擎（MT Framework）以 60 帧为时间单位。原版 30 帧时每个逻辑帧的步长 dt = 2.0，60 帧时 dt = 1.0，120 帧时 dt = 0.5。
- 弩弹命中后，处理命中的那一个逻辑帧里子弹不移动；之后等待固定时间（贯通 4.0 帧，跳弹 8.0 帧）再重新开启攻击判定。新判定有 2 帧启动延迟，贯通弹每次重新开启时速度乘 0.7。
- 子弹冻结的时长正好是一个逻辑帧，也就是 dt。30 帧时冻结 2.0 帧，60 帧时只有 1.0 帧，120 帧时 0.5 帧。于是高帧率下两次命中之间子弹多飞了一段：

| 帧率 | 两段之间子弹飞行距离（v 为当前弹速） |
|---|---|
| 30 | 3.4v |
| 60 | 4.4v（+29%） |
| 120 | 4.9v（+44%） |

步幅变长，子弹穿过同样厚度的怪物时能打出的段数就少了。

## 修复方法

把命中后的等待时间改为 `原值 − (2.0 − dt)`，只在 dt < 2.0 时生效：

- 贯通类：4.0 → 2.0 + dt
- 通常弹 Lv3 跳弹：8.0 → 6.0 + dt

30 帧时行为与原版完全相同。60 / 120 帧时，两段之间的飞行距离和子弹寿命（暴击距离按寿命计算）都与 30 帧一致。

补丁共修改 41 字节：`0x46D410` 处写入等待时间的指令改为跳转，计算代码放在 `.text` 段末尾的对齐填充区 `0x13F1E00`。

## 覆盖范围

- **已修复**：贯通弹 Lv1~3、各属性贯通弹等多段贯通类弹种，通常弹 Lv3（跳弹）。
- **不受影响**：弓的贯通箭，命中时不会冻结，按代码推算没有这个问题。
- **未处理**：近战等其他招式。

## 安装

先把 `mod/HighFPS_Pierce_Fix` 准备好，再按你用的平台放到对应位置：

- **Eden 及其他 yuzu 系模拟器**：放进 `load/0100770008DD8000/` 目录。可以在游戏上右键选“打开 Mod 数据位置”找到它。
- **Ryujinx**：放进 `mods/contents/0100770008dd8000/` 目录。
- **大气层实机**：把 `.ips` 文件放到 `/atmosphere/exefs_patches/HighFPS_Pierce_Fix/` 目录。

配合 60 / 120 帧 cheat 使用即可。不开高帧率时补丁没有任何作用。

目前只在 Eden 上做过加载验证，Ryujinx 和实机还没有测试。

## 验证

`tools/simulate_pierce.py` 按反编译出的逻辑逐帧模拟贯通弹（弹速 75，判定启动延迟 2 帧），统计穿过不同厚度目标时的平均段数：

| 等级 | 目标厚度 | 30 帧 | 60 帧 | 60 帧 + 修复 | 120 帧 | 120 帧 + 修复 |
|---|---|---|---|---|---|---|
| Lv1 | 600 | 3.00 | 2.50 | 3.00 | 2.00 | 3.00 |
| Lv2 | 600 | 3.27 | 2.50 | 3.53 | 2.00 | 4.00 |
| Lv3 | 600 | 3.27 | 2.50 | 3.53 | 2.00 | 4.00 |
| Lv3 | 800 | 5.00 | 4.00 | 5.00 | 3.00 | 5.00 |

修复后高帧率的段数回到 30 帧水平。个别情况下会略多一段，因为高帧率的碰撞检测更密，第一段能更早打中，不是新的偏差。

## 文件说明

- `mod/HighFPS_Pierce_Fix/exefs/FB08F1D20FD1204FE7070672777F869B.ips`：补丁本体（IPS32 格式）。
- `tools/make_patch.py`：从汇编源码生成补丁。`--verify` 可以用 Eden “导出 NSO”得到的 main 校验原始字节，`--pchtxt` 可以额外生成 IPSwitch 格式。依赖 `keystone-engine`。
- `tools/simulate_pierce.py`：贯通弹命中时序模拟。

本仓库不包含任何游戏文件。

## English summary

At 60/120fps (via cheats), bowgun pierce ammo in MHGU 1.4.0 loses hits. After processing a hit, the shell stays still for exactly one logic tick, then waits a fixed 4.0 frames (8.0 for Normal S Lv3 ricochet) before re-arming. Game time is in 60fps frames, so one tick is 2.0 frames at 30fps but only 1.0 at 60fps and 0.5 at 120fps. At higher frame rates the shell therefore travels further between hits (3.4v → 4.4v → 4.9v) and drops hits while passing through a monster.

This patch shortens the re-arm wait by `2.0 − dt` when `dt < 2.0`. That restores the 30fps hit spacing and shell lifetime at any frame rate, and leaves 30fps unchanged. Install `mod/HighFPS_Pierce_Fix` as an exefs mod for the game.
