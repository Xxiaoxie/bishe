# -*- coding: utf-8 -*-
"""
test_core.py —— 核心功能自测（不上传文件也能整条流水线验证）
运行方式：python test_core.py
全部通过会打印「全部通过」。
"""

import io

import numpy as np

from code_generator import build_delivery_zip, generate_matlab_code, generate_python_code
from plotting import add_watermark, filtered_figure, figure_to_png_bytes, spectrum_figure, time_domain_figure
from signal_analysis import (
    DEFAULT_FS, build_conclusion, butterworth_lowpass, clean_signal,
    estimate_fs, fft_spectrum, load_dataframe, pick_numeric_columns,
)


class FakeUpload:
    """模拟 streamlit 上传的文件对象（有 .name，可 seek/read）。"""

    def __init__(self, data: bytes, name: str):
        self._buf = io.BytesIO(data)
        self.name = name

    def seek(self, *args):
        return self._buf.seek(*args)

    def read(self, *args):
        return self._buf.read(*args)

    def tell(self):
        return self._buf.tell()


def make_csv_bytes(t, y, header='时间(秒),幅值', encoding='utf-8-sig'):
    """把数组打包成 CSV 字节流。"""
    lines = [header]
    for ti, yi in zip(t, y):
        lines.append(f'{ti:.6f},{yi:.6f}')
    return ('\n'.join(lines) + '\n').encode(encoding)


def test_full_pipeline():
    """含时间列的标准场景：10 Hz 主频 + 250 Hz 高频噪声。"""
    fs_true = 1000.0
    t = np.arange(0, 2.0, 1 / fs_true)                       # 2 秒，1000 Hz
    rng = np.random.default_rng(42)
    clean = 1.0 * np.sin(2 * np.pi * 10 * t)                 # 10 Hz 主信号
    noise = 0.35 * np.sin(2 * np.pi * 250 * t)               # 250 Hz 高频噪声
    y = clean + noise + 0.05 * rng.standard_normal(t.size)

    # 在中间挖掉 5 个点，验证缺失值清洗
    y_corrupt = y.copy()
    y_corrupt[500:505] = np.nan

    f = FakeUpload(make_csv_bytes(t, y_corrupt), 'test_data.csv')
    df = load_dataframe(f)
    t_col, t_vals, y_col, y_vals = pick_numeric_columns(df)
    assert t_col is not None and y_col is not None, '应识别出两列'

    t_arr, y_arr = clean_signal(t_vals, y_vals)
    assert y_arr.size == t.size - 5, f'应删除 5 个缺失点，实际 {y_arr.size}'

    fs, has_time = estimate_fs(t_arr, t_col)
    assert has_time, '应识别出时间轴'
    assert abs(fs - fs_true) < 1.0, f'采样率应≈1000，实际 {fs}'

    freqs, amp, fp, fp_amp = fft_spectrum(y_arr, fs)
    assert abs(fp - 10.0) < 0.5, f'主频应≈10 Hz，实际 {fp:.2f}'
    assert fp_amp > 0.5, '主频幅值应显著'

    y_filt, fc_used = butterworth_lowpass(y_arr, fs, 1.5 * fp)
    assert abs(fc_used - 15.0) < 0.5, f'截止频率应≈15 Hz，实际 {fc_used}'
    assert np.std(y_arr - y_filt) > 0.1, '应有明显噪声被滤除'
    # 滤波后应接近干净信号（残余 < 噪声的一半）
    clean_kept = clean[np.isfinite(y_corrupt)]              # 与清洗后 survivor 对齐
    residual = np.std(y_filt[20:-20] - clean_kept[20:-20])
    assert residual < 0.5 * np.std(noise), f'滤波残差 {residual:.3f} 过大'

    # 绘图 + 水印
    f1 = figure_to_png_bytes(time_domain_figure(t_arr, y_arr))
    f2 = figure_to_png_bytes(spectrum_figure(freqs, amp, fp, fp_amp))
    f3 = figure_to_png_bytes(filtered_figure(t_arr, y_filt, fc_used))
    for name, b in [('f1', f1), ('f2', f2), ('f3', f3)]:
        assert len(b) > 20000, f'{name} 图片过小，导出可能失败'
    marked = add_watermark(f1)
    assert marked.size[0] > 0 and marked.mode == 'RGBA', '水印图生成失败'
    assert len(f1) != len(marked.tobytes()), '水印后图片应有变化'

    # 结论 + 源码生成 + 交付包
    conclusion = build_conclusion(fs, fp, fc_used, y_arr.size, np.std(y_arr - y_filt))
    assert 60 < len(conclusion) < 200, f'结论长度 {len(conclusion)} 不符合“约 100 字”'
    meta = {
        'data_file': 'test_data.csv', 't_col': t_col, 'y_col': y_col,
        'has_time_axis': has_time, 'fs': fs, 'fp': fp, 'fc': fc_used,
        'n_points': int(y_arr.size), 'conclusion': conclusion,
    }
    m_code = generate_matlab_code(meta)
    p_code = generate_python_code(meta)
    assert 'butter(4' in m_code and 'filtfilt' in m_code, 'Matlab 代码缺滤波'
    assert '主频' in m_code and '主频' in p_code, '源码应含主频标注逻辑'
    assert f'{fp:.2f}' in m_code and f'{fp:.2f}' in p_code, '源码应嵌入实测主频'
    assert 'rfft' in p_code and 'butter' in p_code, 'Python 代码缺分析步骤'
    zip_bytes = build_delivery_zip(
        {'time': f1, 'spectrum': f2, 'filtered': f3}, meta)
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(zip_bytes)).namelist()
    assert len(names) == 6 and '说明.txt' in names and '毕设分析_Matlab.m' in names
    print('  ✔ 含时间列完整流水线通过（主频 %.2f Hz，截止 %.1f Hz）' % (fp, fc_used))


def test_single_column_default_fs():
    """只有一列幅值：应使用默认 Fs=1000。"""
    rng = np.random.default_rng(0)
    t = np.arange(0, 1.0, 1 / 1000)
    y = np.sin(2 * np.pi * 50 * t) + 0.2 * rng.standard_normal(t.size)
    csv = make_csv_bytes(np.arange(t.size), y, header='幅值')
    df = load_dataframe(FakeUpload(csv, 'only_y.csv'))
    t_col, t_vals, y_col, y_vals = pick_numeric_columns(df)
    assert t_col is None and t_vals is None, '单列时不应有时间列'
    _, y_arr = clean_signal(t_vals, y_vals)
    fs, has_time = estimate_fs(None, t_col)   # 无时间列时应回退默认采样率
    assert fs == DEFAULT_FS and not has_time, '应回退到默认 1000 Hz'
    freqs, amp, fp, _ = fft_spectrum(y_arr, DEFAULT_FS)
    assert abs(fp - 50.0) < 1.0, f'默认 Fs 下主频应≈50 Hz，实际 {fp:.2f}'
    print('  ✔ 单列数据（默认 Fs=1000）通过')


def test_gbk_csv_and_index_column():
    """GBK 编码 CSV + 序号列（疑似样本序号）→ 应默认 1000 Hz。"""
    fs_true = 1000.0
    t = np.arange(0, 0.5, 1 / fs_true)
    y = np.sin(2 * np.pi * 20 * t)
    gbk_bytes = make_csv_bytes(np.arange(t.size), y, header='序号,电压', encoding='gbk')
    df = load_dataframe(FakeUpload(gbk_bytes, 'gbk.csv'))
    assert list(df.columns) == ['序号', '电压'], 'GBK 列名解码失败'
    t_col, t_vals, y_col, y_vals = pick_numeric_columns(df)
    t_arr, y_arr = clean_signal(t_vals, y_vals)
    fs, has_time = estimate_fs(t_arr, t_col)
    assert not has_time and fs == DEFAULT_FS, '序号列不应被当作时间轴'
    print('  ✔ GBK 编码 + 序号列回退默认采样率通过')


if __name__ == '__main__':
    print('开始自测...')
    test_full_pipeline()
    test_single_column_default_fs()
    test_gbk_csv_and_index_column()
    print('全部通过 ✔')
