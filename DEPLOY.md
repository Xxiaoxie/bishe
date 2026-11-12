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

**1.2** 建 Public 仓库（一步步来）：
1. 登录后，浏览器直接打开 <https://github.com/new>（或点右上角头像旁的 **「+」→ New repository**）
2. **Repository name** 框填 `bishe`（只能用英文/数字/横线，不能用中文）
3. 往下找到可见性，选 **Public**（公开）。原因：Streamlit Cloud 免费版只支持公开仓库
   的应用（私有应用已并入 Snowflake 收费路线）。放心：管理员密码走云端 Secrets
   配置，绝不在代码仓库里，公开无泄密风险；代价是别人能看到源码。
4. 下方的 **Add a README file / .gitignore / license 全部不要勾**（本地已有这些，
   勾了会导致推送冲突）
5. 点最下方绿色按钮 **Create repository**

> 已建成 Private 仓库？转换：仓库页面 → **Settings** → 拉到最底 **Danger Zone** →
> **Change repository visibility** → Make public → 按提示输入仓库名确认。

**1.3** 把本地代码推上去：

打开命令行（两种方式任选）：
- 打开本项目文件夹（`D:\bishe`），点一下顶部的**地址栏**，输入 `cmd` 后回车；
- 或在文件夹空白处右键 → **Open Git Bash Here** / **在终端中打开**。

执行（**把 `你的用户名` 换成你 GitHub 的用户名**）：

```bash
git remote add origin https://github.com/你的用户名/bishe.git
git push -u origin main
```

> * 首次 push 会弹出 **Git Credential Manager** 小窗：点 **Sign in with your browser** →
>   浏览器里登录 GitHub → 点绿色 **Authorize** 按钮 → 回到命令行看到
>   `main -> main` 即成功。以后 push 免登录。
> * 用户名在哪看：GitHub 页面右上角点头像，第一行就是你的用户名。
> * 万一之前勾了 Add a README 导致 push 报错 `rejected`：把 GitHub 上这个仓库
>   删掉（仓库页面 Settings → 最底部 Danger Zone → Delete this repository），
>   按 1.2 重新建一个**什么都不勾**的，再重新执行上面两条命令。
> * 本地仓库已 init + commit 好，所以只需要这两条命令；GitHub 建完仓库页面
>   显示的三条命令，复制全部执行也可以（多出的那条是无害的）。

---

## 第 2 步：部署到 Streamlit Cloud（约 5 分钟）

**2.1** 浏览器打开 <https://share.streamlit.io> → 点 **Continue with GitHub** →
跳转到 GitHub 授权页 → 点绿色 **Install & Authorize**（或 Authorize Streamlit）按钮。

> * 若让你选仓库访问范围（Repository access）：选 **All repositories** 最省事；
>   选了 Only select repositories 就必须勾上 `bishe`，否则下一步找不到仓库。
> * 首次进入可能问你姓名 / 职业之类，随便填，继续。

**2.2** 进入控制台（My apps）后，点右上角 **Create app**。弹出的对话框有三个选项，
**选第一个 `Deploy a public app from GitHub`**（模板部署用不上；Snowflake 私有
应用是企业收费路线，别选）。然后在表单里填：

| 项 | 填什么 |
| --- | --- |
| Repository | 点开下拉框，选 `你的用户名/bishe` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL | 起个英文名（如 `bishe-rescue`），以后访问地址就是 `https://bishe-rescue.streamlit.app`；被占用就换一个 |

Advanced settings 里 Python version 选 **3.11** 即可（默认也行）。

**2.3** 点右下角 **Deploy!**，等 2~5 分钟：右下角滚动安装日志
（Installing dependencies…），装完页面出现「毕设数据一键分析神器」即成功。

**2.4** **把应用设为「公开」（必做！否则访客打开是空白页）**：
share.streamlit.io → 点进你的应用 → 右下角 **Settings** → **Sharing** 区块 →
**Who can view this app** 改为**公开（Public）** → Save。

> 📌 部署成功 ≠ 能用交付区 —— 还要做第 3 步配密码。
> 这个网址（`https://你起的名字.streamlit.app`）就是发给用户的正式地址。

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
- [ ] 侧边栏客服QQ号正确（改 `app.py` 顶部 `CONTACT_QQ`；本地营业重启 bat 生效，push 后云端也自动更新）

---

## ⚠️ 常见坑速查表

| 现象 | 原因 / 解决 |
| --- | --- |
| 部署页下拉框找不到 `bishe` 仓库 | 授权时没给权限：打开 <https://github.com/settings/installations> → 点 **Streamlit** 的 Configure → Repository access 改成 **All repositories**（或勾上 bishe）→ Save，回来刷新重选 |
| 提示仓库不是 public / 只能选 Snowflake | 免费版只支持公开仓库：按第 1 步末尾的说明把 GitHub 仓库转成 Public，回来刷新重选 |
| 打开 App 是空白页（全白无内容） | 多为大陆访问境外服务器不稳：页面壳能到、JS 加载被卡。先确认 2.4 已设公开（首次访问会自动经 share.streamlit.io 建立会话再弹回，属正常流程）；然后换网络 / 手机流量 / 找外地朋友试。全部打不开则说明该网络环境下无法营业 |
| 图表中文变方框 | 已内置字体一般不会发生；若发生，检查 `fonts/` 文件夹是否已提交到 GitHub |
| 交付区提示「未启用」 | 第 3 步的 Secrets 没配 / 格式写错。注意是 TOML 格式：`admin_password = "xxx"`，值要双引号 |
| 打开很慢、显示 Zzz 图标 | 免费版应用 **7 天没人访问会休眠**，唤醒需 1~2 分钟。自己每周点开一次即可保持活跃 |
| 上传大文件失败 / 应用重启 | 免费容器只有 1GB 内存，上传上限已调为 20MB（`.streamlit/config.toml`），毕设数据绰绰有余 |
| 大陆访问偏慢几秒 | 服务器在境外，属正常；先零成本验证需求，后续有收入再考虑迁移 |
| 大陆打开**全白屏**（手机流量也一样） | 大陆到谷歌云的网络不通，**非平台故障**（2026-11 实测：平台状态页绿色，健康检查/静态资源/websocket 从境外全部正常）。改用下方「🏠 营业模式」 |
| 改了代码没生效 | 每次 `git push` 云端自动重新部署，等 1~2 分钟后刷新页面 |
| push 时弹浏览器要登录 | 正常，首次登录授权一次，之后免登录 |

---

## 🏠 营业模式：自己的电脑当服务器（免费，大陆可访问）

> 实测结论（2026-11）：大陆访问 Streamlit Cloud（谷歌云）经常全白屏。
> 云端网址保留当备用入口，**正式营业用本模式**：本地跑应用 + Cloudflare 免费
> 隧道生成公网网址（走 Cloudflare 网络，大陆一般能打开）。

**一次性准备（约 3 分钟）**：

1. 浏览器打开官方链接，下载 cloudflared（约 50MB 的 exe）：
   <https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe>
   （电脑浏览器下不动就用手机下载后传到电脑）
2. 把下载的 `cloudflared-windows-amd64.exe` 放进本项目文件夹（`D:\bishe`）

**每天营业**：

双击 **`start_business.bat`** → 黑窗口里出现
`https://xxxx.trycloudflare.com` → **这就是当天的营业网址**，手机、别人都能打开。

**规则**：

- 电脑开机 + 窗口开着 = 营业中；关窗口 / 关机 = 打烊
- 网址每次重启都会变，把当天的新网址发微信给客户即可
- 同一台电脑别同时双击两次（端口会冲突）
- 云端网址 `https://bishe-rescue.streamlit.app` 一直免费挂着当备用

---

## 以后怎么更新代码？

改完代码后，在本项目文件夹执行：

```bash
git add -A
git commit -m "一句话说明改了什么"
git push
```

推上去后云端 1~2 分钟内自动更新，无需任何手动操作。
