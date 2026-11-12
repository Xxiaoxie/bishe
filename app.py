# -*- coding: utf-8 -*-
"""
app.py —— 「毕设急救包」Signal-Easy 主程序（Streamlit Web 应用）
==========================================================
运行方式：
    streamlit run app.py

业务流程（PRD 核心闭环）：
    上传 Excel/CSV → 清洗数据 → 时域图 / FFT 频谱图 / 低通滤波图
    →（免费预览：带水印 + 分析结论）
    →（付费 9.9 元：交付区下载无水印高清图 + Matlab/Python 源码包）
"""

import glob
import os

import numpy as np
import streamlit as st

from code_generator import build_delivery_zip, generate_matlab_code, generate_python_code
from plotting import (
    add_watermark,
    filtered_figure,
    figure_to_png_bytes,
    spectrum_figure,
    time_domain_figure,
)
from signal_analysis import (
    CUTOFF_RATIO,
    FILTER_ORDER,
    build_conclusion,
    butterworth_lowpass,
    clean_signal,
    estimate_fs,
    fft_spectrum,
    load_dataframe,
    pick_numeric_columns,
)

# ------------------------------------------------------------------
# 上线配置区（部署前改成你自己的，共三处：这里 2 处 + secrets.toml 1 处）
# ------------------------------------------------------------------
CONTACT_QQ = '你的QQ号'                            # 客服QQ号（侧边栏 + 付款引导处显示，上线前改成自己的小号）
QR_CODE_GLOB = os.path.join('static', '收款码.*')  # 收款码图片，如 static/收款码.png（jpg 也行）


def get_admin_password():
    """读取管理员密码（配置在 .streamlit/secrets.toml 的 admin_password）。

    未配置 secrets.toml 或未写该项时返回空串（交付区保持锁定，宁可不用也不泄密）。
    """
    try:
        return str(st.secrets['admin_password'])
    except (KeyError, FileNotFoundError):
        return ''


# ------------------------------------------------------------------
# 页面配置（必须是第一个 Streamlit 调用）
# ------------------------------------------------------------------
st.set_page_config(page_title='毕设数据一键分析神器', page_icon='📈', layout='wide')

# ------------------------------------------------------------------
# 侧边栏：产品介绍
# ------------------------------------------------------------------
with st.sidebar:
    st.title('📈 毕设急救包')
    st.caption('理工科毕设数据 · 一键分析 · 论文级图表')

    st.markdown(
        '**三步出结果**\n\n'
        '1️⃣ 上传 Excel / CSV 数据\n'
        '2️⃣ 自动生成 3 张论文级图表\n'
        '3️⃣ 支付 9.9 元解锁高清图 + 源码包'
    )
    st.divider()
    st.markdown(
        '**自动完成的分析**\n\n'
        '• 时域波形绘制\n'
        '• FFT 频谱分析（标出主频）\n'
        f'• {FILTER_ORDER} 阶巴特沃斯低通滤波去噪\n'
        '• 100 字学术分析结论\n'
        '• Matlab / Python 源码一键生成'
    )
    st.divider()
    st.caption('🔒 数据仅在本次会话内存中分析，不做任何保存。')
    st.caption(f'🛠 由独立开发者出品 · 唯一客服QQ：`{CONTACT_QQ}`')

# ------------------------------------------------------------------
# 主页面：标题 + 上传
# ------------------------------------------------------------------
st.title('🎓 毕设数据一键分析神器')
st.caption(
    '上传含「时间 + 幅值」两列数据的 Excel / CSV 文件，自动生成论文级图表、'
    '分析结论，以及可直接交差的 Matlab / Python 源码包。'
)

uploaded = st.file_uploader(
    '拖拽或点击上传数据文件',
    type=['xlsx', 'csv'],
    help='支持 .xlsx 和 .csv。第一列建议为时间（秒），第二列为信号幅值；'
         '没有时间列也可以，会按默认采样率 1000 Hz 处理。',
)

if uploaded is None:
    st.info('👆 请先上传数据文件（可先用本项目自带的「示例数据」文件夹里的 CSV 试一试）')
    st.stop()

# ------------------------------------------------------------------
# 1. 读取 → 选列 → 清洗 → 采样率 → FFT → 滤波
# ------------------------------------------------------------------
try:
    with st.spinner('正在读取并清洗数据…'):
        df = load_dataframe(uploaded)                         # 读取文件
        t_col, t_vals, y_col, y_vals = pick_numeric_columns(df)   # 自动识别数值列
        t_arr, y_arr = clean_signal(t_vals, y_vals)           # 清洗（缺失值/排序/去重）
        fs, has_time_axis = estimate_fs(t_arr, t_col)         # 采样率估计
except Exception as exc:                                      # 统一给出人话报错
    st.error(f'❌ 数据读取失败：{exc}')
    st.stop()

if float(np.std(y_arr)) == 0.0:                               # 常数信号无频谱可言
    st.error('❌ 该信号是常数（幅值没有任何变化），不需要频谱分析。请检查是否传错了列。')
    st.stop()

with st.spinner('正在进行 FFT 频谱分析与低通滤波…'):
    freqs, amplitude, fp, fp_amp = fft_spectrum(y_arr, fs)    # FFT + 主频
    fc_design = CUTOFF_RATIO * fp                             # 截止频率 = 1.5 × 主频
    y_filt, fc_used = butterworth_lowpass(y_arr, fs, fc_design)   # 4 阶低通滤波

    # 时间轴：识别出时间列就用它，否则按采样率重建
    if has_time_axis:
        x, xlabel = t_arr, '时间 (s)'
        duration = float(t_arr[-1] - t_arr[0])
    else:
        x, xlabel = np.arange(y_arr.size) / fs, '时间 (s)'
        duration = y_arr.size / fs

    noise_std = float(np.std(y_arr - y_filt))                 # 被滤掉的噪声幅值
    conclusion = build_conclusion(fs, fp, fc_used, y_arr.size, noise_std)

    # 生成三张图（干净版，300dpi，用于付费交付）
    fig1_bytes = figure_to_png_bytes(time_domain_figure(x, y_arr, xlabel))
    fig2_bytes = figure_to_png_bytes(spectrum_figure(freqs, amplitude, fp, fp_amp))
    fig3_bytes = figure_to_png_bytes(filtered_figure(x, y_filt, fc_used, xlabel))

# ------------------------------------------------------------------
# 2. 关键指标 + 数据预览
# ------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric('有效数据点', f'{y_arr.size:,}')
m2.metric('采样率 Fs', f'{fs:g} Hz', help='根据时间列推算；未识别到时间列时默认 1000 Hz')
m3.metric('主频 fp', f'{fp:.2f} Hz')
m4.metric('滤波截止 fc', f'{fc_used:.1f} Hz', help=f'截止频率 = {CUTOFF_RATIO:g} × 主频')

with st.expander('📋 数据预览（自动识别的列）', expanded=False):
    if has_time_axis:
        st.markdown(f"已选择：第 1 数值列「{t_col}」→ 时间，第 2 数值列「{y_col}」→ 幅值")
    else:
        st.markdown(f"仅识别到一个数值列「{y_col}」→ 幅值；未检测到时间列，按默认 Fs=1000 Hz 重建时间轴")
    st.dataframe(df.head(10))

st.divider()

# ------------------------------------------------------------------
# 3. 三张图（预览版：带半透明水印，PRD 商业闭环第一步）
# ------------------------------------------------------------------
st.subheader('分析结果（预览版）')

for png, caption in (
    (fig1_bytes, '图 1 · 原始信号时域波形'),
    (fig2_bytes, '图 2 · FFT 幅值谱（红圈为主频）'),
    (fig3_bytes, f'图 3 · {FILTER_ORDER} 阶巴特沃斯低通滤波后波形'),
):
    preview = add_watermark(png)              # 正中央半透明斜排水印
    preview.thumbnail((1000, 1000))           # 缩小用于网页展示（付费版才是全分辨率）
    st.image(preview, caption=f'{caption}（含水印预览）')

# ------------------------------------------------------------------
# 4. 自动生成的学术分析结论（约 100 字）
# ------------------------------------------------------------------
st.subheader('自动分析结论')
st.success(conclusion)
st.caption(
    f'补充：信号时长约 {duration:.2f} s；主频幅值 {fp_amp:.3g}；'
    f'被滤除的高频噪声幅值约 {noise_std:.3g}。'
)

# ------------------------------------------------------------------
# 5. 付费引导（PRD 文案）
# ------------------------------------------------------------------
st.divider()
st.success('🎉 图表已生成！扫码支付 **9.9 元** 获取无水印高清图 + 可直接交差的 Matlab/Python 源码包')

pay_left, pay_right = st.columns([1, 2])
with pay_left:
    qr_files = sorted(glob.glob(QR_CODE_GLOB))       # 找 static/收款码.png（jpg 等格式均可）
    if qr_files:
        st.image(qr_files[0], caption='扫码支付 9.9 元', width=240)
    else:
        st.markdown(
            '<div style="border:2px dashed #bbb;border-radius:8px;height:150px;'
            'display:flex;align-items:center;justify-content:center;text-align:center;'
            'color:#888;font-size:14px;padding:8px;">'
            '💳 收款码占位<br/>把收款码图片命名为「收款码.png」放到 '
            'static/ 文件夹即可显示</div>',
            unsafe_allow_html=True,
        )
with pay_right:
    st.markdown(
        '**付款后你将获得（ZIP 交付包）：**\n\n'
        '• 3 张 300dpi 无水印高清图，可直接插入论文\n'
        '• `毕设分析_Matlab.m`：逐行中文注释，Matlab 里一键复现全部图表\n'
        '• `毕设分析_Python.py`：逐行中文注释，免 Matlab 也能复现\n'
        '• `说明.txt`：参数、结论、使用方法全写好，答辩照着讲就行\n\n'
        f'付款后截图发给唯一客服QQ `{CONTACT_QQ}`，秒发交付包（谨防仿冒，只认此号）。'
    )

# ------------------------------------------------------------------
# 6. 交付区（管理员专用：密码解锁后才能下载，普通用户无法白嫖）
# ------------------------------------------------------------------
with st.expander('📦 交付区（管理员专用 · 密码解锁）', expanded=False):
    admin_pw = get_admin_password()
    if not admin_pw:                               # 没配置密码 → 交付区整体锁死（fail-closed）
        st.info('🔒 交付区未启用：管理员请在 .streamlit/secrets.toml 中配置 '
                'admin_password（模板见 secrets.toml.example）。')
        st.stop()

    pwd = st.text_input('管理员密码', type='password', key='admin_pwd')
    if pwd != admin_pw:
        if pwd:
            st.warning('❌ 密码不正确。')
        st.caption('🛡 管理员输入密码后即可下载交付包；普通用户付款后请联系唯一客服QQ获取。')
        st.stop()

    st.caption(f'交付对象：{uploaded.name} | Fs = {fs:g} Hz | 主频 {fp:.2f} Hz | 截止 {fc_used:.2f} Hz')

    zip_bytes = build_delivery_zip(
        {'time': fig1_bytes, 'spectrum': fig2_bytes, 'filtered': fig3_bytes},
        {
            'data_file': uploaded.name,
            't_col': t_col or '',
            'y_col': y_col,
            'has_time_axis': has_time_axis,
            'fs': fs,
            'fp': fp,
            'fc': fc_used,
            'n_points': int(y_arr.size),
            'conclusion': conclusion,
        },
    )
    st.download_button(
        '⬇️ 下载完整交付包（无水印图 + 源码 + 说明）',
        data=zip_bytes,
        file_name=f'毕设交付包_{uploaded.name}.zip',
        mime='application/zip',
        key='dl_zip',
    )
    c1, c2, c3 = st.columns(3)
    c1.download_button('⬇️ 图1 无水印', fig1_bytes, 'fig1_时域波形.png', 'image/png', key='dl_f1')
    c2.download_button('⬇️ 图2 无水印', fig2_bytes, 'fig2_频谱图.png', 'image/png', key='dl_f2')
    c3.download_button('⬇️ 图3 无水印', fig3_bytes, 'fig3_滤波后波形.png', 'image/png', key='dl_f3')

    tab_m, tab_p = st.tabs(['Matlab 源码预览', 'Python 源码预览'])
    meta = {
        'data_file': uploaded.name,
        't_col': t_col or '',
        'y_col': y_col,
        'has_time_axis': has_time_axis,
        'fs': fs,
        'fp': fp,
        'fc': fc_used,
        'n_points': int(y_arr.size),
        'conclusion': conclusion,
    }
    with tab_m:
        st.code(generate_matlab_code(meta), language='matlab')
    with tab_p:
        st.code(generate_python_code(meta), language='python')
