# 教练，我要学… · Coach, I Wanna Learn

> 一个苏格拉底式教练 + 自适应课程引擎 Skill，适用于 Claude Code / Hermes / OpenClaw 等支持 Skill 系统的 Agent 运行时。
>
> A Socratic coaching + adaptive curriculum engine Skill for Claude Code, Hermes, OpenClaw, and any Agent runtime that supports the Skill system.

---

## 为什么做这个 · Why This Exists

Vibe-coding 让写代码变得容易，但让**学会一件事**变得更难——AI 会直接给答案，你不需要真的理解。

这个 Skill 反其道而行：它不给答案，它提问。它会在你真正掌握之前拒绝进入下一课。它记得你上次学到哪里，明天傍晚六点准时来敲门。

*Vibe-coding makes writing code easy, but makes **actually learning** harder — AI hands you answers without requiring understanding.*

*This Skill does the opposite: it asks questions, refuses to move on until you've proven mastery, remembers where you left off, and shows up at 6pm tomorrow to continue.*

---

## 核心设计 · Core Design

### 状态机 · State Machine

```
INTAKE → PROFILING → CRAWL → COMPILE_B → PLAN → TEACH → ASSESS
                                                   ↑        ↓
                                                   ←── REVIEW ──→ GRADUATE
```

每个阶段都有独立的 reference 文件驱动，状态持久化到本地 `learning_state.json`。

*Each phase is driven by a dedicated reference file. State persists locally in `learning_state.json`.*

### LLM Wiki 范式 · LLM Wiki Paradigm

不用 RAG，不依赖向量库。Skill 用 `web_search` + `web_fetch` 采集原始素材，再用 LLM 自身将其编译为**教学级 wiki 页面**（Karpathy LLM Wiki 范式）。Wiki 分两级：

- **B 级（课时粒度）**：备课阶段生成，覆盖整个教学计划
- **C 级（概念粒度）**：教学中按需拆解，用户卡住时触发

*No RAG, no vector DB. The Skill collects raw materials via web_search/web_fetch, then uses the LLM itself to compile them into teaching-grade wiki pages. Two levels:*
- *B-level (lesson granularity): generated during prep, covers the full curriculum*
- *C-level (concept granularity): generated on-demand when the user gets stuck*

### 每课独立文件夹 · Per-Lesson Isolation

每节课开始前，Skill 自动在本地创建独立文件夹，包含该课所有原始素材、编译后的教学内容和会话记录：

```
~/.claude/coach-sessions/{topic}_wiki/
└── lessons/
    ├── L01_service_boundary/
    │   ├── sources/          # 本课原始素材
    │   ├── wiki.md           # 编译后教学内容
    │   └── session.json      # 教学交互 + 评估历史
    └── L02_api_design/
        └── ...
```

*Before each lesson, the Skill scaffolds an isolated local folder with all relevant sources, compiled content, and session logs.*

### 混合式认知探测 · Hybrid Profiling

快速扫描（1~2 轮）+ 鉴别性深挖（2~4 轮）= 4~6 轮对话摸清真实认知水平，区分 `known` / `known_unknown` / `unknown_unknown` 三层，主动暴露用户不知道自己不知道的盲区。

*Quick scan + discriminative deep-probe = 4–6 turns to map true knowledge level across known / known_unknown / unknown_unknown, actively surfacing blind spots the user didn't know they had.*

### 主动调度 · Active Scheduling

计划确认后，Skill 主动注册下一节课的 cron / heartbeat / task_schedule，适配三种运行时。用户不需要记得回来——教练会来找用户。

*After the plan is confirmed, the Skill registers the next session automatically via cron / heartbeat / task_schedule — the coach comes to the user, not the other way around.*

---

## 优势 · Advantages

| 特性 | 说明 |
|---|---|
| **苏格拉底式** | 不灌输，用提问引导理解 |
| **检验驱动** | 每课必须通过检验才能进入下一课，不允许跳过 |
| **状态持久化** | 跨 session 记忆，随时中断随时恢复 |
| **主动调度** | 自动注册下次提醒，适配多种运行时 |
| **渐进编译** | wiki 从课时级到概念级按需拆解，不浪费 context |
| **产品可见** | 每课的完整素材和会话记录落在本地文件夹，人类可读 |
| **补课机制** | fail 时自动换教法或补前置知识，不卡死 |
| **vibe-coding 友好** | 专门有一课讲 AI 辅助编码时的架构决策原则和常见坑 |

---

## 文件结构 · File Structure

```
coach-skill/
├── SKILL.md                   # 主控：状态机 + 阶段路由
├── references/
│   ├── 01-intake.md           # 需求探测话术
│   ├── 02-profiling.md        # 混合式认知诊断
│   ├── 03-crawl-compile.md    # 素材采集 + Wiki 编译
│   ├── 04-plan.md             # 排课 + 课型选择器
│   ├── 05-teach.md            # 五种课型教学模板
│   ├── 06-assess.md           # 检验评估 + 补课策略
│   └── 07-schedule.md         # 调度接口（多运行时适配）
└── scripts/
    └── wiki_compiler.py       # Wiki 编译脚本（B/C 级）
```

学习数据存储在 `~/.claude/coach-sessions/`，与 skill 源码分离。

*Learning data is stored in `~/.claude/coach-sessions/`, separate from skill source files.*

---

## 安装 · Installation

### 给 Agent 看的安装方法 · For Agents

**Claude Code（推荐）**

```powershell
# Windows
robocopy "path\to\jiaolian-i-wanna-skill" "$env:USERPROFILE\.claude\skills\coach" /E /XO
```

```bash
# macOS / Linux
rsync -av --update path/to/jiaolian-i-wanna-skill/ ~/.claude/skills/coach/
```

安装后重启 Claude Code，即可在 skill 列表中看到 `coach`。

*Restart Claude Code after installation — `coach` will appear in the skill list.*

**验证安装 · Verify**

在 Claude Code 中输入：
```
教练我要学 Python
```

Skill 应自动激活并进入 INTAKE 阶段。

### 数据目录 · Data Directory

学习数据默认存储在：

```
~/.claude/coach-sessions/{topic-slug}_wiki/
```

如需修改，在调用 `wiki_compiler.py` 时传入 `--base-dir`：

```bash
python scripts/wiki_compiler.py rust --base-dir /your/custom/path
```

---

## 运行时兼容性 · Runtime Compatibility

| 运行时 | 调度方式 | 状态 |
|---|---|---|
| Claude Code | `CronCreate` tool | ✅ 支持 |
| Hermes / OpenClaw | `cron_register` capability | ✅ 支持 |
| 心跳模式 | `heartbeat_append` | ✅ 支持 |
| 无调度能力 | 手动提醒用户 | ✅ 降级支持 |

---

## License

MIT
