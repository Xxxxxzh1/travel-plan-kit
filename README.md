<div align="center">

<img src="docs/promo/01-cover.png" width="330" alt="出境游没信号，照样查票"/>

# travel-plan-kit · 自制离线路书

**一份 `trip.yaml`，生成可打印的行程单 + 没信号也能打开的手机路书。**
国外旅游超好用。

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Offline first](https://img.shields.io/badge/offline--first-yes-2ea44f)
![Made with](https://img.shields.io/badge/made%20with-Claude%20Code-7c3aed)

<br/>

<img src="docs/screenshots/roadbook-demo.gif" width="310" alt="路书交互演示：日程列表 → 票据抽屉 → 分类标签 → 全屏车票"/>

<sub><b>点任意一天 → 票据抽屉 → 全屏车票</b> · 真机录制，非效果图</sub>

</div>

---

## 📴 信号再差也能用

> 路书是**一个自包含的 HTML 文件**——行程、住宿地址、**每一张票据图片**全部嵌在文件内部，
> 运行时不发起任何网络请求。
>
> 地铁里、火车隧道里、阿尔卑斯山谷里、飞机上，**断网照常打开**。
>
> 出境游最怕的就是这个：瑞士山区的火车上、去卡普里的渡轮上、博物馆排队时想确认门票时间，
> 信号说没就没。把这一份文件 AirDrop 到手机里，用不着流量、用不着 Wi-Fi、也刷不出"页面无法打开"。

构建时会自动断言产物里**零外部引用**——这句承诺是构建脚本保证的，不是口头说的。

也正因为如此，下面的加密托管版才定位为「有信号时的备份」：它需要联网取文件，
不是没信号时靠得住的那个。

<p align="center">
  <img src="docs/promo/06-offline-print.png" width="380" alt="所有票据都在这一个文件里 · 附 A4 打印版行程单"/>
</p>

## 🧭 路书能做什么

一个 HTML 文件——不要服务器、不要装 App、不要网络。AirDrop 到手机，
飞机上、火车上、山谷里都能开。所有交互都为「单手、站着、赶时间」设计：

- **点任意一天** → 底部抽屉滑出，当天全部信息一屏：行程安排、带车次和座位号的交通段、
  当晚住宿、还有票据本身。下滑即可关闭。
- **票据自动分组计数** —— `全部 3 · 🚄 交通 2 · 🏨 住宿 1`。在闸机前你要的是火车票，
  不是在相册里翻。
- **点开票据** → 全屏。双指放大二维码、左右滑动换票、长按存入相册。
- **🎫 全部票据** → 整趟行程的票在一处，按类别排列并自动去重
  （连用三天的铁路通票只出现一次）。
- **按国家筛选**，把 14 天的行程折叠成其中一段。
- **实时倒计时** —— 出发前显示 `D-12`，旅途中显示 `Day 3`，当天的卡片标着「今天」。
- **跟随系统深浅色**。

<table>
  <tr>
    <td align="center" width="33%">
      <img src="docs/promo/03-timeline.png" width="100%" alt="按天排的时间轴"/><br/>
      <sub><b>按天时间轴</b> · 点任意一天，当天行程 / 交通 / 住宿 / 票据一起弹出</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/promo/04-ticket-tabs.png" width="100%" alt="票据分好类"/><br/>
      <sub><b>票据自动分类</b> · 标签带计数，闸机前直接翻到车票</sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/promo/05-all-tickets.png" width="100%" alt="全部票据一屏汇总"/><br/>
      <sub><b>全部票据汇总</b> · 自动去重，点开全屏、双指放大二维码</sub>
    </td>
  </tr>
</table>

### 🧭 住宿地址就是 Google 地图链接（配合离线地图是绝配）

路书里**每一间住宿的地址都是可点击的链接**：装了 Google Maps 的手机上点一下，
直接唤起 App 定位；当天抽屉里还有一个全宽的「🧭 在 Google 地图中打开」按钮——
**晚上十点站在陌生街角找民宿的时候，你要的就是这个按钮。**

配合 **Google 离线地图**才是完全体，出发前花三分钟：

1. 在 Google Maps 里把目的地城市**下载为离线区域**（设置 → 离线地图，每个城市几分钟）；
2. 到了没信号的地方——山区的火车上、地铁隧道里——打开 Google Maps，
   **搜索和导航照常工作**；
3. 万一当时点不动链接，**地址文字始终显示在路书里**，复制出来到 Maps 里手动搜也一样。

信号断断续续的地方，这比现开网页查地图省心得多。

## 😮‍💨 为什么做这个

它始于一次真实的意大利 → 瑞士十四天旅行：每个预订躺在不同的 App 里，
每张票都是相册里又一张截图，而信号一断，什么都够不着。于是整趟行程被编译成了
一个页面——那个页面在火车上、山谷里、博物馆闸机前被天天打开。这个仓库就是那套
工具的通用化版本。

<p align="center">
  <img src="docs/promo/02-why.png" width="380" alt="出境游的真实崩溃"/>
</p>

## 🖨 还会生成什么

| 产物 | 用途 |
|---|---|
| `itinerary.md` | 行程总表，纯 Markdown——哪都能看，能 diff |
| `itinerary.html` | 同一张表的排版版 |
| `itinerary.pdf` | 横向 A4——**打印出来过关用**；边检有时会分开问话，一人带一份 |
| `roadbook.html` | 上面的离线路书 |
| `roadbook.enc.html` | 可选的密码加密版路书，可安全公开托管 |

<p align="center">
  <img src="docs/screenshots/itinerary-pdf.png" width="620" alt="横向 A4 打印行程单"/>
</p>

> 出发前把 PDF 打印出来，路书存进手机。两者的失效方式不同：
> **纸张不怕没电，路书不怕弄丢。**

## 🚀 快速开始

```bash
git clone https://github.com/Xxxxxzh1/travel-plan-kit ~/.claude/skills/travel-plan-kit
cd ~/.claude/skills/travel-plan-kit

pip install pyyaml            # 唯一的必装依赖
python3 scripts/build.py examples/italy-switzerland/trip.yaml
open examples/italy-switzerland/out/roadbook.html
```

然后复制 `trip.example.yaml`，填入你自己的行程，再对它跑一遍 `build.py`。

<p align="center">
  <img src="docs/promo/07-get-started.png" width="380" alt="自己也能生成一份"/>
</p>

## 📱 在手机上打开路书（先看这段）

路书是一个本地 HTML 文件，**手机上怎么打开因系统而异**：

- **iPhone**：系统**不会**把 Safari 列为 HTML 文件的打开方式——在「文件」App 里点开
  只会走快速预览，抽屉、灯箱等交互可能受限。请用**带内置浏览器的 App** 打开：
  - **Documents by Readdle**（App Store 免费下载）：把 HTML 文件导入，点开即可，
    完整支持抽屉、灯箱、双指缩放；
  - **Alook 浏览器** 是同类选择。
- **Android**：文件管理器里点开，选择 Chrome 打开即可。
- **或者干脆托管**：把 `roadbook.enc.html` 传到 GitHub Pages，手机浏览器直接访问。
  内容是加密的，公开仓库也安全（见下文）。

> 收到别人发来的路书文件？它就是一个网页文件——存下来，按上面的方式打开就行。

## 🧬 为什么各格式不会互相打架

所有产物都从同一份数据渲染，因此**不可能**彼此矛盾。两条规则保证这一点：

**住宿只声明一次。** `lodging` 是顶层列表，每天通过 `id` 引用。住三晚的住宿
只存一份、被查三次——改地址是一处修改，而不是三处。

```yaml
lodging:
  - id: rome
    city: 罗马
    address: Via dei Fiori, 12, Rome, Italy
    checkin:  {date: 2027-09-24, time: "16:00"}
    checkout: {date: 2027-09-27, time: "10:00"}
    nights: 3

days:
  - {n: 1, date: 2027-09-24, city: 罗马, lodging: rome}
```

**Markdown 和 HTML 由同一个行构建器渲染。** 只传一个格式参数，改变的是内联标记
如何变成文本，结构永远一致。两份手工维护的表格迟早漂移；同一个构建器不会和自己漂移。

**构建先生成校验、后生成产物。** `nights` 会和日期核对；指向不存在住宿的 `id`、
找不到文件的票据、顺序错乱的日期，全都是错误——而且**一次性列出所有问题**，并指明位置：

```
trip file has problems:
  - days[3]: lodging 'nowhere' is not defined in the lodging list
  - lodging[0]: nights=4 but 2027-09-24..2027-09-27 is 3 night(s)
  - tickets[6]: file not found: tickets/shinkansen.pdf
```

## 📦 环境要求

- **Python 3** + `pyyaml` —— 必需
- **Chrome / Chromium / Edge / Brave** —— 渲染 PDF 和票据图。不需要 wkhtmltopdf、
  weasyprint 或 pandoc（而且它们对这个用到的 CSS 支持更差）。
  可用 `CHROME=/path/to/chrome` 指定。
- **`pdftoppm`**（poppler）—— 仅当票据是 PDF 时需要。
  `brew install poppler` / `apt install poppler-utils`
- **Pillow** —— 可选；用于压缩票据图片、控制路书体积
- **Node.js** —— 仅 `--encrypt` 需要

`build.py` 启动时会先自检环境，缺什么直接告诉你，不会跑到一半才失败。

## 🔐 托管加密版路书

路书里是**可用的票据二维码**，往线上放之前要想清楚。

**GitHub Pages 免费版和专业版的站点一律公开。** 私有 Pages 需要 GitHub
Enterprise Cloud——**私有仓库并不会给你一个私有的站点**。

所以 `--encrypt` 会把整个载荷（行程、住宿、每一张票据图）用 **AES-256-GCM**
加密，密钥由 PBKDF2 从你的密码派生；先 gzip 压缩再加密，避免 base64 膨胀付两次：

```bash
python3 scripts/build.py my-trip.yaml --encrypt 'correct horse battery staple'
```

结果文件没有密码就是一堆惰性密文，放进公开仓库也安全。而在明文数据外面套一层
"请输入密码"的 JS 弹窗不是加密——查看源代码，票据还在那儿。

⚠️ **加密强度等于密码强度。** 40 万轮 PBKDF2 让每次猜测都有成本，
但 `holiday` 仍然是字典词。请用长口令。

⚠️ **它牺牲了离线可用。** 加密版需要联网取文件才能解锁。AirDrop 的明文版
在飞机上也能开。大多数时候，两个都要。

## 🤖 作为 Claude Code 技能使用

按上面的方式 clone 到 `~/.claude/skills/`，Claude 会自动识别。之后只要说
"做一份行程单""生成路书""帮我整理这次旅行的票据"，它就会收集行程信息、
写好 `trip.yaml`、校验并构建全部文档。工作流写在 `SKILL.md`，细节在 `references/`。

## 🗂 仓库结构

```
SKILL.md                      Claude Code 技能入口
trip.example.yaml             带注释的最小模板
schema/trip.schema.json       供编辑器自动补全的 schema
scripts/
  model.py                    解析 + 校验 + 解析 id 引用
  build.py                    构建编排器
  gen_itinerary.py            → md, html
  gen_roadbook.py             → 移动路书
  ingest_tickets.py           规整票据图片
  make_sample_tickets.py      为示例生成合成票据
  encrypt_roadbook.mjs        AES-256-GCM 密码门
  browser.py                  定位并驱动 headless Chrome
  record_demo.mjs             录制 README 的演示 GIF 帧
  make_demo_gif.py            把帧合成 GIF
templates/                    tokens.css, itinerary.html, roadbook.html
references/                   数据模型、构建管线、票据处理
examples/italy-switzerland/   完整示例
docs/promo/                   上方的宣传卡片
docs/screenshots/             演示 GIF + 打印版 PDF 截图
```

演示 GIF 由录制的帧合成，可一键复现：

```bash
cd examples/italy-switzerland/out && python3 -m http.server 8770 --bind 127.0.0.1 &
node scripts/record_demo.mjs http://localhost:8770/roadbook.html /tmp/frames
python3 scripts/make_demo_gif.py /tmp/frames docs/screenshots/roadbook-demo.gif
```

录制器通过 CDP 设备模拟设定精确的 390×844 手机视口——headless Chrome 会钳制
`--window-size` 导致画面被裁——并拉长抽屉的 CSS 过渡，因为 360 毫秒的滑出动画
比一次 CDP 截图往返还短，不拉长就永远拍不到滑动中间态。

## 🎭 关于示例数据

示例行程是**完全合成的**：人名、房东、街道地址、电话、预订号均为虚构；票据图由
`scripts/make_sample_tickets.py` 生成，并盖有 `SAMPLE DATA — NOT A REAL TICKET`
水印。路线是真实地理，其余皆非真实。

这是刻意的。真实票据图包含姓名、出生日期、预订号，以及本身就是凭证的二维码——
它们不该出现在公开仓库里。自己生成的真实产物请留在版本控制之外。

## 许可证

MIT
