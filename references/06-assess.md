# ASSESS + REVIEW 阶段 — 检验与补课

---

## ASSESS：检验式评估

### 出题规则

每课结束后出 2~3 题，顺序固定：

| 题型 | 是否必出 | 目的 |
|---|---|---|
| 核心概念验证题 | 必出 | 检验对核心概念的理解，不允许死记硬背通过 |
| 应用题 | 必出 | 根据课型：project→写代码、case_study→场景分析、socratic→开放推理 |
| 迁移题 | 关键课时可选 | 探查深层理解，看用户能否把概念用到新场景 |

### 题型设计原则

**核心概念验证题**（不出定义题）：
- ❌ "什么是所有权？"（背定义没用）
- ✅ "这段代码编译会成功吗？为什么？"（检验理解）
- ✅ "下面两种写法，哪个更符合 Rust 的惯用法？为什么？"

**应用题**（贴近 motivation）：
- 尽量结合用户的动机场景（如"在你的爬虫里，这个函数签名应该怎么写？"）
- 对 project 型课时必须有代码题

**迁移题**（关键课时启用）：
- 在 dependency_chain 上的关键节点课时使用
- 例："所有权规则在函数参数传递中是怎么体现的？"（接上一课所有权，迁移到函数）

### 出题格式

```
--- 课时检验 ---

题 1（核心概念）
{题目内容}

题 2（应用）
{题目内容}

[题 3（迁移）—— 可选]
{题目内容}

——
不用一次答完，逐题回答也行。
```

---

## 评判标准

LLM 根据用户回答综合判定：

### pass

满足以下全部条件：
- 题 1（核心概念题）答对且能解释
- 题 2（应用题）答对，代码题可以小错（能自行修正算通过）
- 整体回答显示对概念有真实理解，非死记

**后续动作**：
```python
lesson["status"] = "passed"
lesson["assess_history"].append({
    "attempt": attempt_num,
    "verdict": "pass",
    "timestamp": now_iso8601()
})
state["current_lesson"] += 1

# 注册下一课 schedule
register_next_session(state)

# 告知用户
if state["current_lesson"] <= state["plan"]["total_lessons"]:
    reply("✅ 过了！第 N 课的内容你掌握了。\n下一课「{title}」已安排到 {next_time}。")
else:
    state["state"] = "GRADUATE"
```

### partial

满足以下条件：
- 核心概念题答对（或接近正确）
- 应用题有明显盲点（能写出大致结构但有概念性错误）

**后续动作**：
```python
lesson["assess_history"].append({
    "attempt": attempt_num,
    "verdict": "partial",
    "weak_points": ["具体盲点描述"],
    "timestamp": now_iso8601()
})

# 补讲 1~2 轮，针对盲点
reply("有个地方需要加强一下——{weak_point}。我们来看一看：{补讲内容}")
# 补题再评（只出盲点相关的 1 题）
```

### fail

满足任一条件：
- 核心概念题答错
- 应用题完全无从下手
- 答案显示存在根本性误解

**后续动作**：进入 REVIEW

---

## REVIEW：补课机制

### 诊断

fail 后先诊断原因：

```python
def diagnose_fail(lesson, answers):
    # 检查是否是前置知识问题
    for prereq in lesson["prerequisites"]:
        if not is_mastered(prereq, state):
            return "missing_prereq", prereq
    
    # 检查是否是教法问题（用户对这种课型响应不好）
    if lesson["type"] == "textbook" and user_prefers_hands_on(state):
        return "wrong_method", lesson["type"]
    
    # 默认：需要换角度重讲
    return "needs_reexplain", None
```

### 策略 A：换教法重讲

同一内容换课型（最多换一次）：

| 原课型 | 换成 |
|---|---|
| textbook | project（用代码让概念具体化）|
| project | textbook（先把概念讲清楚再动手）|
| socratic | textbook（有些人需要先给结论）|

```python
lesson["review_type"] = new_type
reply("我换个方式教这部分——{new_type_description}")
# 重新进入 TEACH，使用新课型
```

### 策略 B：补前置知识

```python
prereq_lesson = {
    "id": f"R{lesson['id']}",
    "title": f"补课：{missing_prereq}",
    "type": "textbook",
    "wiki_refs": get_wiki_for(missing_prereq),
    "estimated_duration": 15,
    "status": "pending",
    "is_remedial": True
}

# 插入到 plan.lessons 当前位置之前
plan["lessons"].insert(current_index, prereq_lesson)
state["current_lesson"] = prereq_lesson["id"]

reply("我发现有个前置知识需要先补一下：{missing_prereq}。
      先用 15 分钟把这个搞定，原来的内容就能顺利理解了。")
```

### REVIEW 后流程

补课完成后：
1. 重新执行 ASSESS（`attempt` 加 1）
2. 如果依然 fail（第 3 次 attempt），暂停并向用户说明：
   > "这个概念我们连续卡了 3 次——我觉得可能需要你先去看一些外部资料打底。我给你推荐几个资源，等你看完我们再继续？"
   将课时 status 设为 `"paused"`，跳过此课继续后面的课时。

---

## 评估历史记录

assess_history 完整结构：

```json
[
  {
    "attempt": 1,
    "verdict": "fail",
    "weak_points": ["借用规则理解有误"],
    "timestamp": "2026-05-21T09:30:00+08:00"
  },
  {
    "attempt": 2,
    "verdict": "partial",
    "weak_points": ["可变借用场景不熟"],
    "review_type": "project",
    "timestamp": "2026-05-22T09:15:00+08:00"
  },
  {
    "attempt": 3,
    "verdict": "pass",
    "timestamp": "2026-05-22T09:45:00+08:00"
  }
]
```
