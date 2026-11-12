# 🚀 部署手册：Streamlit Community Cloud（免费托管，保姆级）

> 全程**不花一分钱、不用买服务器/域名**。
> 前置条件：一个 GitHub 账号 + 浏览器。全程约 20 分钟（大部分时间在等）。

---

## 第 0 步：确认文件已就绪（✅ 已备好）

| 文件 | 作用 |
| --- | --- |
| `app.py` | 主程序（部署时 Main file path 就填它） |
| `requirements.txt` | 依赖清单，云端自动安装 |
| `.streamlit/config.toml` | 主题 / 上传上限配置 |
| `fonts/NotoSansCJKsc-Regular.otf` | 内置中文字体，防止云端图表变方框 |
| `.gitignore` | 已排除密码文件 `secrets.toml`，**绝不会**传上 GitHub |

⚠️ 唯一不跟着代码上云的：**管理员密码**。部署完要在云端后台手动填一次（见第 3 步），
否则页面底部「交付区」会一直处于锁定状态。

---

## 第 1 步：把代码推上 GitHub（约 5 分钟）

**1.1** 打开 <https://github.com>，注册 / 登录。

**1.2** 点右上角 **「+」→ New repository**：
- Repository name 填 `bishe`（或其他英文名）
- 选 **Private**（私有仓库，别人看不到你的代码；免费账号可部署 1 个私有应用，够用）
- 其余都不勾 → 点 **Create repository**

**1.3** 在本项目文件夹打开命令行（Git Bash / PowerShell 都行），执行：

```bash
git remote add origin https://github.com/你的用户名/bishe.git
git push -u origin main
```

> 首次 push 会弹出浏览器让你登录 GitHub 并授权（Git Credential Manager），
> 点完授权即可，以后再 push 免登录。
> （本地仓库我已帮你 init + commit 好，所以只有这两条命令。）

---

## 第 2 步：部署到 Streamlit Cloud（约 5 分钟）

**2.1** 打开 <https://share.streamlit.io> → **Continue with GitHub** → 授权。

**2.2** 点 **Create app**，填写：

| 项 | 填什么 |
| --- | --- |
| Repository | `你的用户名/bishe` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL | 起个英文名（如 `bishe-rescue`），以后访问地址就是 `https://bishe-rescue.streamlit.app` |

Advanced settings 里 Python version 选 **3.11** 即可（默认也行）。

**2.3** 点 **Deploy!**，等 2~5 分钟（云端在自动 pip install）。

**2.4** 看到 **Your app is live 🎈**、页面出现「毕设数据一键分析神器」即部署成功。
把这个网址发给用户就能用了。

---

## 第 3 步：配置管理员密码（必做，约 1 分钟）

**3.1** 打开 <https://share.streamlit.io> → 进入你的 App → 右下角 **Settings**。

**3.2** 切到 **Secrets** 标签，粘贴以下内容（密码换成你自己的，别和代码库里的一致也没关系）：

```toml
admin_password = "你的管理员密码"
```

**3.3** 点 **Save**，App 自动重启，交付区密码即生效。

> 本地的 `.streamlit/secrets.toml` 被 .gitignore 挡住不会上传，所以云端要单独配这份。

---

## 第 4 步：上线自检清单（逐条点一遍）

- [ ] 打开 `https://你的应用名.streamlit.app`，页面正常显示
- [ ] 上传 `示例数据/示例数据_含时间列.csv` → 出三张图，**中文不是方框 □**
- [ ] 图上有半透明水印；分析结论正常显示
- [ ] 页面底部「📦 交付区」锁定：输错密码有提示，输对密码能下载 ZIP
- [ ] 付款区显示收款码（把收款码图片命名为 `收款码.png` 放进 `static/` 文件夹后 push）
- [ ] 侧边栏微信号正确（改 `app.py` 顶部 `CONTACT_WECHAT` 后 push 即自动更新）

---

## ⚠️ 常见坑速查表

| 现象 | 原因 / 解决 |
| --- | --- |
| 图表中文变方框 | 已内置字体一般不会发生；若发生，检查 `fonts/` 文件夹是否已提交到 GitHub |
| 交付区提示「未启用」 | 第 3 步的 Secrets 没配 / 格式写错。注意是 TOML 格式：`admin_password = "xxx"`，值要双引号 |
| 打开很慢、显示 Zzz 图标 | 免费版应用 **7 天没人访问会休眠**，唤醒需 1~2 分钟。自己每周点开一次即可保持活跃 |
| 上传大文件失败 / 应用重启 | 免费容器只有 1GB 内存，上传上限已调为 20MB（`.streamlit/config.toml`），毕设数据绰绰有余 |
| 大陆访问偏慢几秒 | 服务器在境外，属正常；先零成本验证需求，后续有收入再考虑迁移 |
| 改了代码没生效 | 每次 `git push` 云端自动重新部署，等 1~2 分钟后刷新页面 |
| push 时弹浏览器要登录 | 正常，首次登录授权一次，之后免登录 |

---

## 以后怎么更新代码？

改完代码后，在本项目文件夹执行：

```bash
git add -A
git commit -m "一句话说明改了什么"
git push
```

推上去后云端 1~2 分钟内自动更新，无需任何手动操作。
