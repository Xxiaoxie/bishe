# -*- coding: utf-8 -*-
"""
code_generator.py —— 源码生成模块（本产品的“杀手锏”）
==================================================
根据用户上传的数据文件与分析结果，用模板自动生成：

    * 一份 Matlab 源码（.m，逐行中文注释，一键复现全部三张图）
    * 一份 Python 源码（.py，逐行中文注释，一键复现全部三张图）
    * 一份交付说明（说明.txt）

并把这些文件连同 3 张无水印 300dpi 高清图打包成 ZIP，
付款后直接把 ZIP 发给用户即可完成交付（PRD 的商业闭环）。

模板使用 string.Template：代码里 $xxx 是占位符，
不会被 Python 的 f-string/format 语法干扰。
"""

import zipfile
from datetime import datetime
from io import BytesIO
from string import Template

FILTER_ORDER = 4          # 与 signal_analysis.py 保持一致
CUTOFF_RATIO = 1.5        # 截止频率 = 1.5 × 主频


# ------------------------------------------------------------------
# 数据读取段（按“有无时间列”生成不同的代码片段）
# ------------------------------------------------------------------
def _matlab_read_block(meta):
    if meta['has_time_axis']:
        return (
            f"data = readtable('{meta['data_file']}');            % 读取数据文件（需与本 .m 文件同目录）\n"
            f"t = data{{:, 1}};                                   % 第 1 列「{meta['t_col']}」= 时间 (s)\n"
            f"y = data{{:, 2}};                                   % 第 2 列「{meta['y_col']}」= 信号幅值\n"
            f"ok = ~isnan(t) & ~isnan(y);                         % 数据清洗：找出缺失值所在行\n"
            f"t = t(ok); y = y(ok);                               % 剔除缺失值行\n"
            f"Fs = {meta['fs']:g};                                % 采样率 (Hz)（由时间列间隔推算）"
        )
    return (
        f"data = readtable('{meta['data_file']}');            % 读取数据文件（需与本 .m 文件同目录）\n"
        f"y = data{{:, 1}};                                   % 第 1 列「{meta['y_col']}」= 信号幅值（文件无时间列）\n"
        f"y = y(~isnan(y));                                   % 数据清洗：剔除缺失值\n"
        f"Fs = {meta['fs']:g};                                % 采样率 (Hz)（未检测到时间列，取默认值）\n"
        f"t = (0:length(y)-1) / Fs;                           % 按采样率重建时间轴 (s)"
    )


def _python_read_block(meta):
    # 按上传文件后缀选择读取函数，保证生成的代码开箱即跑
    name = meta['data_file'].lower()
    read_call = (f"pd.read_csv('{meta['data_file']}', encoding='utf-8-sig')"
                 if name.endswith('.csv') else
                 f"pd.read_excel('{meta['data_file']}')")
    if meta['has_time_axis']:
        return (
            f"df = {read_call:<58}# 读取数据文件（与本 .py 同目录）\n"
            f"t = df.iloc[:, 0].astype(float).to_numpy()     # 第 1 列「{meta['t_col']}」= 时间 (s)\n"
            f"y = df.iloc[:, 1].astype(float).to_numpy()     # 第 2 列「{meta['y_col']}」= 信号幅值\n"
            f"ok = np.isfinite(t) & np.isfinite(y)           # 数据清洗：找出缺失/非数值行\n"
            f"t, y = t[ok], y[ok]                            # 剔除缺失值行\n"
            f"Fs = {meta['fs']:g}                            # 采样率 (Hz)（由时间列间隔推算）"
        )
    return (
        f"df = {read_call:<58}# 读取数据文件（与本 .py 同目录）\n"
        f"y = df.iloc[:, 0].astype(float).to_numpy()     # 第 1 列「{meta['y_col']}」= 信号幅值（文件无时间列）\n"
        f"y = y[np.isfinite(y)]                         # 数据清洗：剔除缺失值\n"
        f"Fs = {meta['fs']:g}                            # 采样率 (Hz)（未检测到时间列，取默认值）\n"
        f"t = np.arange(len(y)) / Fs                     # 按采样率重建时间轴 (s)"
    )


# ------------------------------------------------------------------
# Matlab 源码模板
# ------------------------------------------------------------------
MATLAB_TEMPLATE = Template(r'''%% ============================================================
%  毕设数据一键分析 —— Matlab 源码（自动生成，含逐行中文注释）
%  ------------------------------------------------------------
%  数据文件  : $data_file
%  数据列    : $t_desc / $y_desc
%  关键参数  : Fs = $fs Hz | 主频 fp = $fp Hz | 低通截止 fc = $fc Hz
%  使用方法  : 把本文件与数据文件放在同一文件夹，直接点击“运行”
%  依赖      : Signal Processing Toolbox（butter / filtfilt 函数）
%  生成时间  : $timestamp
%% ============================================================
clear; clc; close all;                                 % 清空工作区、命令行，关闭旧图窗

%% 1. 读取数据
$read_block

%% 2. 绘制原始信号时域波形
figure('Color', 'w', 'Position', [100 100 900 470]);   % 新建白底图窗
plot(t, y, '-', 'Color', [0.12 0.31 0.61], 'LineWidth', 1.8);   % 经典学术蓝粗线
xlabel('时间 (s)', 'FontSize', 12);                    % X 轴标签（12 号字）
ylabel('幅值', 'FontSize', 12);                        % Y 轴标签（12 号字）
title('原始信号时域波形', 'FontSize', 13);             % 图标题（13 号字）
grid off;                                              % 关闭网格（论文风格）
set(gca, 'FontSize', 12);                              % 坐标刻度统一 12 号字
print('-dpng', '-r300', 'fig1_时域波形.png');          % 导出 300dpi 高清图

%% 3. FFT 频谱分析（单边谱 + 标出主频）
N  = length(y);                                        % 信号总点数
Yf = fft(y - mean(y));                                 % 先减均值（去直流）再 FFT，避免 0Hz 假峰
half = floor(N / 2) + 1;                               % 单边谱的频点个数
P  = abs(Yf(1:half)) * 2 / N;                          % 单边幅值谱（量纲与原信号一致）
P(1) = P(1) / 2;                                       % 直流分量不需要乘 2
f  = (0:half-1) * Fs / N;                              % 每个频点对应的频率 (Hz)
[~, k] = max(P(2:end));                                % 跳过 0Hz 直流分量，找最大峰
k = k + 1;                                             % 把索引还原成从 1 开始
fp = f(k);                                             % 主频 (Hz)

figure('Color', 'w', 'Position', [100 100 900 470]);
plot(f, P, '-', 'Color', [0.12 0.31 0.61], 'LineWidth', 1.6);   % 幅值谱曲线
xlabel('频率 (Hz)', 'FontSize', 12);
ylabel('幅值', 'FontSize', 12);
title(sprintf('幅值谱（单边谱），主频 %.2f Hz', fp), 'FontSize', 13);
hold on;                                               % 在同一张图上继续叠加标注
plot(fp, P(k), 'ro', 'MarkerSize', 9, 'LineWidth', 1.8);        % 红圈圈出主频峰
text(fp, P(k), sprintf('  主频 %.2f Hz', fp), 'Color', 'r', 'FontSize', 12);  % 峰值旁文字
grid off;
set(gca, 'FontSize', 12);
print('-dpng', '-r300', 'fig2_频谱图.png');

%% 4. 4 阶巴特沃斯低通滤波去噪
fc = $fc;                                              % 低通截止频率 = 1.5 × 主频 (Hz)
[b, a] = butter($order, fc / (Fs / 2), 'low');         % 设计 4 阶低通 Butterworth 滤波器
y2 = filtfilt(b, a, y);                                % 零相位滤波：不引入相位延迟

figure('Color', 'w', 'Position', [100 100 900 470]);
plot(t, y2, '-', 'Color', [0.12 0.31 0.61], 'LineWidth', 1.8);  % 滤波后的平滑波形
xlabel('时间 (s)', 'FontSize', 12);
ylabel('幅值', 'FontSize', 12);
title(sprintf('4 阶巴特沃斯低通滤波后波形（fc = %.1f Hz）', fc), 'FontSize', 13);
grid off;
set(gca, 'FontSize', 12);
print('-dpng', '-r300', 'fig3_滤波后波形.png');

%% 5. 输出分析结论
fprintf('分析完成：主频 fp = %.2f Hz，截止频率 fc = %.2f Hz。\n', fp, fc);
fprintf('三张 300dpi 图片已保存到当前文件夹。\n');
''')


# ------------------------------------------------------------------
# Python 源码模板
# ------------------------------------------------------------------
PYTHON_TEMPLATE = Template(r'''# -*- coding: utf-8 -*-
"""
毕设数据一键分析 —— Python 源码（自动生成，含逐行中文注释）
------------------------------------------------------
数据文件 : $data_file
数据列   : $t_desc / $y_desc
关键参数 : Fs = $fs Hz | 主频 fp = $fp Hz | 低通截止 fc = $fc Hz
运行前提 : pip install pandas numpy scipy matplotlib openpyxl
使用方法 : 把本文件与数据文件放在同一文件夹，运行 python 本文件
生成时间 : $timestamp
"""
import numpy as np                            # 数值计算库
import pandas as pd                           # 表格数据读取
from scipy.fft import rfft, rfftfreq          # 快速傅里叶变换
from scipy.signal import butter, filtfilt     # 巴特沃斯滤波器 / 零相位滤波
import matplotlib
matplotlib.use('Agg')                         # 无界面出图（不弹窗，直接存文件）
import matplotlib.pyplot as plt               # 绘图库

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']  # 中文字体
plt.rcParams['axes.unicode_minus'] = False    # 让负号正常显示
plt.rcParams['axes.grid'] = False             # 不画网格（论文风格）

# ---------- 1. 读取数据 ----------
$read_block

# ---------- 2. 原始信号时域波形 ----------
fig, ax = plt.subplots(figsize=(8, 4.2))      # 新建画布（8×4.2 英寸）
ax.plot(t, y, color='#1f4e9c', lw=1.8)        # 经典学术蓝粗线
ax.set_xlabel('时间 (s)', fontsize=12)        # X 轴标签（12 号字）
ax.set_ylabel('幅值', fontsize=12)            # Y 轴标签（12 号字）
ax.set_title('原始信号时域波形', fontsize=13)  # 图标题
ax.tick_params(labelsize=12)                  # 刻度字号 12
fig.tight_layout()                            # 自动收紧边距
fig.savefig('fig1_时域波形.png', dpi=300)     # 导出 300dpi 高清图
plt.close(fig)                                # 关闭图，释放内存

# ---------- 3. FFT 频谱分析（单边谱 + 标出主频） ----------
N = len(y)                                    # 信号总点数
spec = rfft(y - y.mean())                     # 去直流后做 FFT，避免 0Hz 假峰
f = rfftfreq(N, d=1.0 / Fs)                   # 单边频率轴 (Hz)
A = np.abs(spec) * 2.0 / N                    # 单边幅值谱（量纲与原信号一致）
A[0] /= 2.0                                   # 直流分量不乘 2
k = int(np.argmax(A[1:]) + 1)                 # 跳过 0Hz，找最大峰的索引
fp = f[k]                                     # 主频 (Hz)

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(f, A, color='#1f4e9c', lw=1.6)        # 幅值谱曲线
ax.plot(fp, A[k], 'o', color='#d62728', ms=9,  # 红圈圈出主频峰
        mfc='none', mew=1.8)
ax.annotate(f'主频 {fp:.2f} Hz',              # 峰值旁的文字标注
            xy=(fp, A[k]), xytext=(12, 8),
            textcoords='offset points', color='#d62728', fontsize=12)
ax.set_xlabel('频率 (Hz)', fontsize=12)
ax.set_ylabel('幅值', fontsize=12)
ax.set_title(f'幅值谱（单边谱），主频 {fp:.2f} Hz', fontsize=13)
ax.tick_params(labelsize=12)
fig.tight_layout()
fig.savefig('fig2_频谱图.png', dpi=300)
plt.close(fig)

# ---------- 4. 4 阶巴特沃斯低通滤波去噪 ----------
fc = $fc                                      # 低通截止频率 = 1.5 × 主频 (Hz)
b, a = butter($order, fc / (Fs / 2), btype='low')   # 4 阶低通 Butterworth
y2 = filtfilt(b, a, y)                        # 零相位滤波：不引入相位延迟

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(t, y2, color='#1f4e9c', lw=1.8)       # 滤波后的平滑波形
ax.set_xlabel('时间 (s)', fontsize=12)
ax.set_ylabel('幅值', fontsize=12)
ax.set_title(f'4 阶巴特沃斯低通滤波后波形（fc = {fc:.1f} Hz）', fontsize=13)
ax.tick_params(labelsize=12)
fig.tight_layout()
fig.savefig('fig3_滤波后波形.png', dpi=300)
plt.close(fig)

# ---------- 5. 输出分析结论 ----------
print(f'分析完成：主频 fp = {fp:.2f} Hz，截止频率 fc = {fc:.2f} Hz。')
print('三张 300dpi 图片已保存到当前文件夹。')
''')


# ------------------------------------------------------------------
# 对外接口
# ------------------------------------------------------------------
def generate_matlab_code(meta):
    """生成 Matlab 源码（.m）。meta 为包含分析结果的字典。"""
    t_desc = (f"第 1 列「{meta['t_col']}」= 时间"
              if meta['has_time_axis'] else '无时间列（按默认采样率重建时间轴）')
    return MATLAB_TEMPLATE.substitute(
        data_file=meta['data_file'],
        t_desc=t_desc,
        y_desc=f"第 2 列「{meta['y_col']}」= 幅值" if meta['has_time_axis']
               else f"第 1 列「{meta['y_col']}」= 幅值",
        fs=f"{meta['fs']:g}",
        fp=f"{meta['fp']:.2f}",
        fc=f"{meta['fc']:.2f}",
        order=FILTER_ORDER,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        read_block=_matlab_read_block(meta),
    )


def generate_python_code(meta):
    """生成 Python 源码（.py）。meta 为包含分析结果的字典。"""
    t_desc = (f"第 1 列「{meta['t_col']}」= 时间"
              if meta['has_time_axis'] else '无时间列（按默认采样率重建时间轴）')
    return PYTHON_TEMPLATE.substitute(
        data_file=meta['data_file'],
        t_desc=t_desc,
        y_desc=f"第 2 列「{meta['y_col']}」= 幅值" if meta['has_time_axis']
               else f"第 1 列「{meta['y_col']}」= 幅值",
        fs=f"{meta['fs']:g}",
        fp=f"{meta['fp']:.2f}",
        fc=f"{meta['fc']:.2f}",
        order=FILTER_ORDER,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        read_block=_python_read_block(meta),
    )


def generate_readme_text(meta):
    """生成交付包里的 说明.txt（可直接用于论文 / 答辩）。"""
    lines = [
        '═' * 56,
        ' 毕设数据分析 · 交付说明',
        '═' * 56,
        '',
        '一、分析对象',
        f"  数据文件　: {meta['data_file']}",
        (f"  数据列　　: 「{meta['t_col']}」(时间) + 「{meta['y_col']}」(幅值)"
         if meta['has_time_axis'] else
         f"  数据列　　: 「{meta['y_col']}」(幅值；文件无时间列，按默认采样率重建时间轴)"),
        f"  有效点数　: {meta['n_points']}",
        '',
        '二、关键结果',
        f"  采样率 Fs　　　: {meta['fs']:g} Hz",
        f"  主频 fp　　　　: {meta['fp']:.2f} Hz",
        f"  滤波器　　　　: {FILTER_ORDER} 阶巴特沃斯低通（零相位 filtfilt）",
        f"  截止频率 fc　　: {meta['fc']:.2f} Hz（= {CUTOFF_RATIO} × 主频）",
        '',
        '三、文件清单',
        '  fig1_时域波形.png　　原始信号时域波形（300dpi 无水印）',
        '  fig2_频谱图.png　　　FFT 单边幅值谱，红圈标出主频（300dpi 无水印）',
        '  fig3_滤波后波形.png　4 阶低通滤波去噪后的波形（300dpi 无水印）',
        '  毕设分析_Matlab.m　　一键复现全部图表的 Matlab 脚本（逐行中文注释）',
        '  毕设分析_Python.py　 一键复现全部图表的 Python 脚本（逐行中文注释）',
        '',
        '四、如何使用',
        '  Matlab：需要 Signal Processing Toolbox；把 .m 与数据文件放同一目录运行',
        '  Python：先 pip install pandas numpy scipy matplotlib openpyxl，',
        '　　　　　再把 .py 与数据文件放同一目录，运行 python 毕设分析_Python.py',
        '  图片　：300dpi 高清，可直接插入论文（Word / LaTeX 均可）',
        '',
        '五、自动分析结论（可直接引用到论文中）',
        f"  {meta['conclusion']}",
        '',
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        '由「毕设急救包」自动生成',
    ]
    return '\n'.join(lines)


def build_delivery_zip(figs, meta):
    """把无水印高清图 + 双语言源码 + 说明打包为 ZIP（字节流）。

    figs: {'time': png字节, 'spectrum': png字节, 'filtered': png字节}
    meta: 见 generate_matlab_code 的说明
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('fig1_时域波形.png', figs['time'])
        zf.writestr('fig2_频谱图.png', figs['spectrum'])
        zf.writestr('fig3_滤波后波形.png', figs['filtered'])
        zf.writestr('毕设分析_Matlab.m', generate_matlab_code(meta))
        zf.writestr('毕设分析_Python.py', generate_python_code(meta))
        zf.writestr('说明.txt', generate_readme_text(meta))
    return buf.getvalue()
