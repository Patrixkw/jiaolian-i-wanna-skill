# PLAN 阶段 — 教学计划生成

## 目标

根据 profile + wiki/index.md + time_commitment，生成完整教学计划，用户确认后注册 schedule。

---

## 课型选择器

### 五种课型

| 课型 | 适用场景 | 核心结构 |
|---|---|---|
| `project` | 编程、工具使用、动手技能 | 目标→脚手架→动手→讲卡点→检验 |
| `textbook` | 理论、数学、框架原理、纯概念 | 概念→类比→正例反例→练习→检验 |
| `case_study` | 管理、商业、设计决策、架构权衡 | 案例→提问→知识提炼→迁移→检验 |
| `socratic` | 哲学、思维方法、高阶抽象概念 | 核心问题→追问→矛盾暴露→自行修正→检验 |
| `drill` | 语言语法、算法模式、乐器指法 | 规则速讲→密集练习→即时纠错→变式→检验 |

### 选择逻辑

```python
def select_lesson_type(concept, topic_domain, profile_level, user_preference=None):
    if user_preference:
        return user_preference
    
    # 领域 + 内容类型判断
    if topic_domain in ["编程", "工具", "框架"] and concept_is_hands_on(concept):
        return "project"
    
    if concept_is_abstract_theory(concept):
        if profile_level in ["absolute-beginner", "beginner"]:
            return "textbook"  # 初学者需要系统建构
        else:
            return "socratic"  # 有基础的人用苏格拉底更高效
    
    if topic_domain in ["管理", "商业", "设计", "产品"]:
        return "case_study"
    
    if concept_requires_repetition(concept):  # 如语法、公式
        return "drill"
    
    return "textbook"  # 默认
```

---

## 排课逻辑

### 步骤

1. **拓扑排序**：按 dependency_chain 排列课时顺序，保证前置知识先教
2. **跳过已验证**：`verified_known` 中的概念跳过（但在计划中标注为"已掌握"）
3. **优先级排列**：
   - 第 1~3 课：`key_gaps` 中的最大障碍点
   - 中间课时：`known_unknown`（用户有锚点，建立连接）
   - 后期课时：`unknown_unknown`（需要前置铺垫）
4. **分配课型**：每个概念用课型选择器决定课型
5. **生成 cron**：根据 time_commitment 生成 cron 表达式

### Cron 生成规则

```python
def generate_cron(time_commitment):
    time = time_commitment["preferred_time"]  # "09:00"
    slots = time_commitment["preferred_slots"]
    hour, minute = time.split(":")
    
    if "workday_morning" in slots or "workday" in slots:
        return f"{minute} {hour} * * 1-5"  # 工作日
    elif "weekend" in slots:
        return f"{minute} {hour} * * 0,6"  # 周末
    elif "daily" in slots:
        return f"{minute} {hour} * * *"    # 每天
    else:
        return f"{minute} {hour} * * 1-5"  # 默认工作日
```

---

## 教学计划展示格式

```
好，我给你排了一个 10 课的 Rust 学习计划，每次 30 分钟，工作日早上 9 点：

课时 1  所有权与移动语义    [项目练习]  30 min  ← 从这里开始（key gap）
课时 2  借用与引用          [项目练习]  30 min
课时 3  生命周期基础         [教科书式]  30 min
课时 4  Trait 入门          [教科书式]  30 min
课时 5  错误处理（Result）   [项目练习]  30 min
课时 6  迭代器与闭包         [项目练习]  30 min
课时 7  模块与 crate 系统   [教科书式]  30 min
课时 8  并发基础             [案例分析]  30 min
课时 9  async/await         [项目练习]  30 min
课时 10 综合项目：并发爬虫   [项目练习]  30 min  ← 你的目标

已跳过：变量与类型、控制流、函数（你已掌握 ✅）

你可以：
A. 直接开始
B. 调整课时顺序或合并（如"把 3、4 合并"）
C. 换某课的教法（如"第 3 课改用项目练习"）
D. 改时间安排
```

---

## 用户调整处理

| 用户请求 | 处理方式 |
|---|---|
| "合并第 3、4 课" | 合并为一节，增加 estimated_duration，更新 wiki_refs |
| "第 5 课改用项目练习" | 修改 type 字段，不需要重新采集 |
| "从第 3 课开始" | current_lesson 设为 3，前 2 课标记为 skipped |
| "改成晚上 8 点" | 更新 preferred_time 和 cron |
| "加快节奏，每天 2 课" | 拆分 cron 为多次/天，或减少总课时数 |

---

## 确认后执行

用户说"好"/"开始"/"没问题"后：

1. 将 `plan` 写入 `learning_state.json`
2. 调用 `references/07-schedule.md` 中的调度接口注册 schedule
3. 将 state 更新为 `"TEACH"`，`current_lesson` 设为 1
4. 立刻开始第一课，不等下次 schedule 触发：
   > "计划定好了，schedule 也注册完成——明天早上 9 点你会收到提醒。不过现在我们就开始第一课吧？"
