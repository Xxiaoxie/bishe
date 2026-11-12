# -*- coding: utf-8 -*-
"""
signal_analysis.py —— 信号分析核心模块
=====================================
负责整条数据处理流水线：
    读取文件 → 自动选列 → 数据清洗 → 采样率估计 → FFT 频谱分析 → 巴特沃斯低通滤波

对应的 PRD 需求：
    * 支持 .xlsx / .csv 上传
    * 自动识别数值列，多列时默认取前两列（时间 / 幅值）
    * 根据时间列推算采样率 Fs，推算不出时默认 Fs = 1000 Hz
    * scipy.fft 单边谱 + 主频识别
    * 4 阶巴特沃斯低通滤波（截止频率 = 1.5 × 主频）
"""

import io

import numpy as np
import pandas as pd
from scipy.fft import rfft, rfftfreq          # 快速傅里叶变换
from scipy.signal import butter, filtfilt     # 巴特沃斯滤波器 / 零相位滤波

# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------
DEFAULT_FS = 1000.0        # 无法识别时间列时使用的默认采样率（PRD 规定）
MIN_POINTS = 32            # 做 FFT 至少需要的数据点数
FILTER_ORDER = 4           # 巴特沃斯滤波器阶数（PRD 规定 4 阶）
CUTOFF_RATIO = 1.5         # 截止频率 = 主频 × 1.5（PRD 规定）


# ------------------------------------------------------------------
# 1. 文件读取
# ------------------------------------------------------------------
def load_dataframe(raw_file):
    """根据文件后缀名读取上传的 Excel / CSV 文件，返回 pandas.DataFrame。

    自动兼容常见编码：中文 Windows 的 Excel 导出的 CSV 常为 GBK 编码，
    因此依次尝试 utf-8-sig / gbk / latin-1。
    """
    name = str(getattr(raw_file, 'name', '')).lower()
    if name.endswith('.csv'):
        raw_file.seek(0)
        raw_bytes = raw_file.read()                  # 先读出全部字节，手动尝试解码
        last_error = None
        for encoding in ('utf-8-sig', 'gbk', 'latin-1'):
            try:
                text = raw_bytes.decode(encoding)
                return pd.read_csv(io.StringIO(text))
            except UnicodeDecodeError as exc:         # 编码不对就换下一个
                last_error = exc
        raise ValueError(f'CSV 解码失败（{last_error}），请用 Excel 另存为 UTF-8 后重试')
    if name.endswith(('.xlsx', '.xls')):
        raw_file.seek(0)
        return pd.read_excel(raw_file)
    raise ValueError('仅支持 .xlsx / .xls / .csv 格式的文件')


# ------------------------------------------------------------------
# 2. 自动选列
# ------------------------------------------------------------------
def pick_numeric_columns(df, min_valid_ratio=0.8):
    """自动识别数值列。

    判断标准：该列至少 min_valid_ratio（80%）的值能转成数字。
    有两列及以上时，默认取前两个数值列作为（时间, 幅值）（PRD 规定）；
    只有一列时，时间列返回 None（后续用默认采样率重建时间轴）。

    返回: (时间列名 or None, 时间序列 or None, 幅值列名, 幅值序列)
    """
    candidates = []                                   # [(列名, 转成数值后的 Series), ...]
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors='coerce')   # 非数值会变成 NaN
        if converted.notna().mean() >= min_valid_ratio:
            candidates.append((str(col), converted))

    if not candidates:
        raise ValueError('未找到数值列：请确认文件中至少有一列纯数字数据（时间或幅值）')

    if len(candidates) == 1:                          # 只有一列 → 视为幅值列
        name, values = candidates[0]
        return None, None, name, values

    (t_name, t_vals), (y_name, y_vals) = candidates[0], candidates[1]
    return t_name, t_vals, y_name, y_vals


# ------------------------------------------------------------------
# 3. 数据清洗
# ------------------------------------------------------------------
def clean_signal(t, y):
    """数据清洗（PRD：处理缺失值）。

    * 删除含缺失值 / 非数值的行；
    * 带时间轴时按时间排序，并删除重复时间点；
    * 有效点数不足时报错。

    参数 t / y 可以是 pandas.Series（来自 pick_numeric_columns），
    返回 (numpy数组 or None, numpy数组)。
    """
    t_arr = None if t is None else pd.to_numeric(t, errors='coerce').to_numpy(dtype=float)
    y_arr = pd.to_numeric(y, errors='coerce').to_numpy(dtype=float)

    if t_arr is not None:
        ok = np.isfinite(t_arr) & np.isfinite(y_arr)  # 两列都有效的行才保留
        t_arr, y_arr = t_arr[ok], y_arr[ok]
        order = np.argsort(t_arr, kind='stable')      # 按时间升序排列
        t_arr, y_arr = t_arr[order], y_arr[order]
        keep = np.concatenate(([True], np.diff(t_arr) > 1e-12))   # 去重（保留首个）
        t_arr, y_arr = t_arr[keep], y_arr[keep]
    else:
        y_arr = y_arr[np.isfinite(y_arr)]

    if y_arr.size < MIN_POINTS:
        raise ValueError(f'有效数据点仅 {y_arr.size} 个（至少 {MIN_POINTS} 个），无法做频谱分析')
    return t_arr, y_arr


# ------------------------------------------------------------------
# 4. 采样率估计
# ------------------------------------------------------------------
def _column_name_looks_like_time(name):
    """根据列名判断是否为时间列（列名常被写成 时间/time/秒/t 等）。"""
    s = str(name).strip().lower()
    if s in {'t', 'time', 's', 'sec', 'second', 'seconds', '时间', '时刻',
             't/s', 't(s)', 't（s）', '时间(s)', '时间（s）'}:
        return True
    return any(key in s for key in ('时间', '时刻', 'time', '秒'))


def estimate_fs(t_arr, t_col_name=None):
    """根据时间列推算采样率 Fs（PRD：推算不出就默认 1000 Hz）。

    判定规则：
      * 间隔必须全为正（时间单调递增）且基本均匀（95% 的间隔落在
        中位间隔的 ±50% 以内），否则认为第一列不是时间轴；
      * “从 0/1 开始、步长恰为 1 的整数列”更像样本序号而非时间，
        此时按 PRD 用默认 Fs = 1000 Hz。

    返回: (fs, 是否识别出真实时间轴)
    """
    if t_arr is None or t_arr.size < 4:
        return DEFAULT_FS, False

    name_is_time = _column_name_looks_like_time(t_col_name or '')
    dt = np.diff(t_arr)                       # 相邻采样点的时间间隔
    med = float(np.median(dt))
    if med <= 0:
        return DEFAULT_FS, False

    mostly_uniform = (
        np.all(dt > 0)
        and np.mean(np.abs(dt - med) <= 0.5 * med + 1e-12) >= 0.95
    )

    if not mostly_uniform:
        if name_is_time and np.all(dt > 0):
            # 列名明示是时间，只是间隔不严格均匀：用中位间隔近似采样率
            return 1.0 / med, True
        return DEFAULT_FS, False

    looks_like_index = (
        float(t_arr[0]) in (0.0, 1.0)
        and np.allclose(dt, 1.0)
        and np.allclose(t_arr, np.round(t_arr))
    )
    if looks_like_index and not name_is_time:
        return DEFAULT_FS, False              # 疑似样本序号 → 按默认采样率处理

    return 1.0 / med, True


# ------------------------------------------------------------------
# 5. FFT 频谱分析
# ------------------------------------------------------------------
def fft_spectrum(y_arr, fs):
    """对信号做 FFT，返回单边幅值谱并找出主频。

    * 先减去均值（去直流），避免 0 Hz 处出现巨峰淹没真实主频；
    * 幅值谱乘 2/N 后与原信号同量纲（单边谱惯例）；
    * 从第 2 个频点开始找最大峰，即为主频。

    返回: (频率轴, 幅值谱, 主频 Hz, 主频幅值)
    """
    y_arr = np.asarray(y_arr, dtype=float)
    n = y_arr.size

    spectrum = rfft(y_arr - y_arr.mean())            # scipy.fft 实数 FFT
    freqs = rfftfreq(n, d=1.0 / fs)                  # 单边频率轴 (Hz)
    amplitude = np.abs(spectrum) * 2.0 / n           # 单边幅值谱
    amplitude[0] /= 2.0                              # 直流分量不翻倍

    idx = int(np.argmax(amplitude[1:]) + 1)          # 跳过 0 Hz 找主频
    return freqs, amplitude, float(freqs[idx]), float(amplitude[idx])


# ------------------------------------------------------------------
# 6. 巴特沃斯低通滤波
# ------------------------------------------------------------------
def butterworth_lowpass(y_arr, fs, cutoff):
    """4 阶巴特沃斯低通滤波去噪（filtfilt 零相位，不引入相位延迟）。

    归一化截止频率被限制在 (0.002, 0.99) 内，防止主频贴着奈奎斯特
    频率时滤波器无法设计。

    返回: (滤波后信号, 实际采用的截止频率 Hz)
    """
    nyquist = fs / 2.0
    wn = float(np.clip(cutoff / nyquist, 0.002, 0.99))   # 归一化截止频率 (0~1)
    b, a = butter(FILTER_ORDER, wn, btype='low')          # 4 阶低通滤波器系数
    y_filt = filtfilt(b, a, np.asarray(y_arr, dtype=float))
    return y_filt, float(wn * nyquist)


# ------------------------------------------------------------------
# 7. 自动生成“学术分析结论”（约 100 字，PRD 模板）
# ------------------------------------------------------------------
def build_conclusion(fs, fp, fc, n_points, noise_std):
    """按 PRD 给定的模板生成约 100 字的分析结论（Markdown 纯文本）。"""
    return (
        f'经分析，该信号共 {n_points} 个采样点，采样率约 {fs:g} Hz，'
        f'主频为 {fp:.2f} Hz。原始波形存在明显高频噪声'
        f'（噪声幅值约 {noise_std:.3g}），经 4 阶巴特沃斯低通滤波'
        f'（截止频率 {fc:.2f} Hz，即 1.5 倍主频）后，'
        f'波形平滑度显著提升，周期特征更加清晰，'
        f'可直接用于后续系统建模与参数辨识。'
    )
