# -*- coding: utf-8 -*-
"""
test_app.py —— app.py 启动冒烟测试
================================
运行方式：
    python test_app.py

用 Streamlit 官方 AppTest 框架无浏览器执行 app.py，验证：
    * 应用能正常启动（无异常）；
    * 未上传文件时出现正确的引导提示；
    * 管理员密码已配置（交付区不会处于「未启用」状态）。
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

# ---- 1. 页面启动无异常 ----
at = AppTest.from_file('app.py', default_timeout=60)
at.run()
assert not at.exception, f'app 启动即报错：{at.exception}'

# ---- 2. 标题 + 上传引导正常渲染 ----
assert at.title[0].value.startswith('🎓'), '主标题未渲染'
assert any('请先上传数据文件' in m.value for m in at.info), '未出现上传引导提示'

# ---- 3. 管理员密码已配置（secrets.toml 由 .gitignore 忽略，不入库） ----
secrets_file = Path('.streamlit') / 'secrets.toml'
assert secrets_file.exists(), '缺少 .streamlit/secrets.toml（从 secrets.toml.example 复制一份）'
assert 'admin_password' in secrets_file.read_text(encoding='utf-8'), \
    'secrets.toml 中未配置 admin_password，交付区将保持锁定'

print('✅ test_app 冒烟测试通过：应用可正常启动，交付区密码配置有效。')
