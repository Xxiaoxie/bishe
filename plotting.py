# -*- coding: utf-8 -*-
"""
plotting.py —— 学术论文级绘图 + 预览水印
=====================================
* matplotlib 全部按 PRD 要求配置：无网格、线条加粗、字号 12、300dpi、学术风；
* 所有图表导出为 PNG 字节流，方便打包 / 下载；
* 用 Pillow 在图片正中央叠加半透明斜体水印：“预览版 - 支付9.9元解锁高清源码”。
"""

import io
import os

import matplotlib
matplotlib.use('Agg')                       # 无界面后端：只出文件不弹窗，服务器上也能跑
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------
# 项目自带的开源中文字体（思源黑体 Noto Sans CJK SC，OFL 协议可自由分发）
# 优先使用自带字体：任何服务器（包括 Streamlit Cloud 的 Linux 容器）上
# 中文都不会变方框，且各平台渲染效果一致。
# ------------------------------------------------------------------
BUNDLED_FONT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'fonts', 'NotoSansCJKsc-Regular.otf',
)
if os.path.exists(BUNDLED_FONT_PATH):
    font_manager.fontManager.addfont(BUNDLED_FONT_PATH)   # 注册到 matplotlib 字体库

# ------------------------------------------------------------------
# 学术风全局样式（PRD：无网格、粗线条、字号 12、300dpi）
# ------------------------------------------------------------------
plt.rcParams['font.sans-serif'] = [         # 中文字体（自带思源黑体优先，其余为系统回退）
    'Noto Sans CJK SC', 'Microsoft YaHei', 'SimHei', 'PingFang SC',
    'WenQuanYi Micro Hei', 'DejaVu Sans',
]
plt.rcParams['axes.unicode_minus'] = False  # 让负号 “-” 正常显示
plt.rcParams['axes.grid'] = False           # 不显示网格（论文风格）

ACADEMIC_BLUE = '#1f4e9c'                   # 经典学术蓝
MARKER_RED = '#d62728'                      # 主频标记红
WATERMARK_TEXT = '预览版 - 支付9.9元解锁高清源码'
EXPORT_DPI = 300                            # 论文级分辨率


# ------------------------------------------------------------------
# 画图
# ------------------------------------------------------------------
def _new_axes(figsize=(8.0, 4.2)):
    """新建一张白底学术图画布，返回 (fig, ax)。"""
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    return fig, ax


def _decorate(ax, xlabel, ylabel, title):
    """统一设置坐标轴标签 / 标题 / 刻度字号（全部 12 号，标题 13 号）。"""
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.tick_params(labelsize=12)
    for spine in ax.spines.values():        # 边框稍微加粗，更接近期刊排版
        spine.set_linewidth(1.1)
    ax.grid(False)                          # 再次确保无网格


def time_domain_figure(x, y, xlabel='时间 (s)', ylabel='幅值', title='原始信号时域波形'):
    """图 1：原始信号时域波形。"""
    fig, ax = _new_axes()
    ax.plot(x, y, color=ACADEMIC_BLUE, linewidth=1.8)   # 粗线条学术蓝
    _decorate(ax, xlabel, ylabel, title)
    fig.tight_layout()
    return fig


def spectrum_figure(freqs, amplitude, fp, fp_amp, title='幅值谱（单边谱）'):
    """图 2：FFT 单边幅值谱，并用红圈 + 文字标出主频峰。"""
    fig, ax = _new_axes()
    ax.plot(freqs, amplitude, color=ACADEMIC_BLUE, linewidth=1.6)
    ax.plot(fp, fp_amp, 'o', color=MARKER_RED, markersize=9,
            markerfacecolor='none', markeredgewidth=1.8)          # 红圈圈出主频
    ax.annotate(f'主频 {fp:.2f} Hz',                              # 峰值旁的文字标注
                xy=(fp, fp_amp), xytext=(12, 8),
                textcoords='offset points',
                color=MARKER_RED, fontsize=12)
    _decorate(ax, '频率 (Hz)', '幅值', f'{title}，主频 {fp:.2f} Hz')
    fig.tight_layout()
    return fig


def filtered_figure(x, y_filt, fc, xlabel='时间 (s)', ylabel='幅值'):
    """图 3：低通滤波去噪后的时域波形。"""
    fig, ax = _new_axes()
    ax.plot(x, y_filt, color=ACADEMIC_BLUE, linewidth=1.8)
    _decorate(ax, xlabel, ylabel, f'4 阶巴特沃斯低通滤波后波形（fc = {fc:.1f} Hz）')
    fig.tight_layout()
    return fig


def figure_to_png_bytes(fig):
    """把 matplotlib 图导出为 300dpi PNG 的字节流（并顺手关闭图，防内存泄漏）。"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=EXPORT_DPI)
    plt.close(fig)
    return buf.getvalue()


# ------------------------------------------------------------------
# 预览水印（Pillow 实现）
# ------------------------------------------------------------------
def _load_cjk_font(size):
    """加载一个能显示中文的字体（项目自带字体优先），都找不到就用 Pillow 默认字体。"""
    candidates = [
        BUNDLED_FONT_PATH,                   # 项目自带的思源黑体（优先，跨平台一致）
        r'C:\Windows\Fonts\msyh.ttc',        # Windows 微软雅黑
        r'C:\Windows\Fonts\msyh.ttf',
        r'C:\Windows\Fonts\simhei.ttf',      # Windows 黑体
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',   # Linux 思源黑体
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',           # Linux 文泉驿
        '/System/Library/Fonts/PingFang.ttc',                        # macOS 苹方
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def add_watermark(png_bytes, text=WATERMARK_TEXT):
    """在图片正中央叠加半透明斜排水印，返回带水印的 PIL 图像。

    实现：把文字画在一层透明画布上 → 整体旋转 18° 得到“斜体”效果 →
    与原图合成。灰色 + 约 43% 不透明度，既醒目又不完全挡住图形。
    """
    base = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    width, height = base.size

    font = _load_cjk_font(max(30, width // 22))       # 字号随图片宽度自适应
    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    bbox = draw.textbbox((0, 0), text, font=font)      # 计算文字实际占的框
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - text_w) / 2 - bbox[0],
               (height - text_h) / 2 - bbox[1]),
              text, font=font, fill=(90, 90, 90, 110))  # 半透明灰

    layer = layer.rotate(18, resample=Image.BICUBIC, center=(width / 2, height / 2))
    return Image.alpha_composite(base, layer)
