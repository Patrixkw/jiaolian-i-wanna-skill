# PROFILING 阶段 — 认知诊断

## 目标

通过 4~6 轮对话，构建完整的用户知识画像。结束时 `profile` 对象必须包含：
- `known`：用户确实掌握的概念（经过验证）
- `known_unknown`：知道但不确定的概念
- `unknown_unknown`：用户不知道自己不知道的概念
- `verified_known`：通过检验题验证的概念子集
- `downgraded`：自评熟悉但检验未通过的概念
- `level`：整体水平标签
- `key_gaps`：最大障碍点描述
- `dependency_chain`：概念依赖链

---

## 第一轮：快速知识地图扫描（1~2 轮）

### 步骤

1. **用 `web_search` 获取该领域知识地图**
   - 搜索词模板：`"{topic} 知识体系 概念地图"` 或 `"{topic} roadmap core concepts"`
   - 从结果中提炼 8~12 个核心概念，按层次排列（基础→进阶）

2. **分层呈现，让用户自评**
   
   呈现格式：
   ```
   我整理了 Rust 的核心概念，你评估一下自己的掌握程度：
   
   基础层
   - 变量与类型（let、mut、基本类型）
   - 控制流（if、loop、match）
   - 函数与闭包
   
   核心层
   - 所有权（ownership）
   - 借用与引用（borrowing、&）
   - 生命周期（lifetime、'a）
   
   高级层
   - Trait 与泛型
   - 错误处理（Result、？）
   - 并发与 async/await
   
   每个概念标一下：✅ 熟悉 / ⚠️ 听过 / ❌ 没概念
   ```

3. **解析用户回答，构建初始画像**
   - ✅ → `self_assessed.familiar`
   - ⚠️ → `self_assessed.heard_of`
   - ❌ → `self_assessed.no_idea`

---

## 第二轮：鉴别性深挖（2~4 轮）

### 策略 A：对"熟悉"的概念——验真

挑选 1~2 个标了 ✅ 的核心概念，问鉴别性问题：

**提问原则**：
- 不问定义（"什么是所有权"）
- 问行为（"这段代码会报什么错"）
- 或场景（"你要把一个字符串传给两个函数，你会怎么做"）

**Rust 所有权示例题**：
```rust
fn main() {
    let s = String::from("hello");
    let s2 = s;
    println!("{}", s);  // 这行会发生什么？
}
```

**判定**：
- 答对且能解释原因 → 加入 `verified_known`，保留在 `known`
- 答对但说不清为什么 → 保留在 `known`，不加入 `verified_known`
- 答错 → 移入 `downgraded`，从 `known` 删除，加入 `known_unknown`

### 策略 B：对"听过"的概念——探边界

用场景题探理解深度：

**示例（借用）**：
> "你在 Rust 里想让一个函数读取一个字符串但不拥有它，你会怎么写函数签名？"

**判定**：
- 能写出或描述 `fn read(s: &str)` 的形式 → 升级到 `known`
- 说出了方向但不确定语法 → 保留在 `known_unknown`
- 完全不知道 → 降级到 `no_idea`，考虑加入前置内容

### 策略 C：暴露 unknown_unknown

根据领域依赖链，主动提示用户未提及但必然会遇到的概念：

> "你提到了所有权，但你没提到生命周期（lifetime）——这两个概念是绑在一起的，写稍微复杂一点的代码就会遇到。你有没有看到过 `'a` 这种写法？"

判定后加入 `unknown_unknown`（如果用户完全没概念）或 `known_unknown`（听说过但不懂）。

---

## 水平标签

| 标签 | 描述 |
|---|---|
| `absolute-beginner` | 没有任何相关领域经验 |
| `beginner` | 有少量相关知识，但核心概念不清楚 |
| `beginner-with-programming-background` | 有其他编程语言经验，但该语言零基础 |
| `intermediate` | 掌握核心概念，缺少高级特性和实践 |
| `intermediate-with-gaps` | 整体中级，但有明显的知识盲区 |
| `advanced` | 熟悉大部分概念，需要专项深化 |

---

## 依赖链构建

根据知识地图和用户 profile，生成概念依赖链（作为字符串存入 state）：

示例：
```
"所有权 → 借用 → 生命周期 → Trait → async/await"
```

规则：
- 每个箭头代表"必须先掌握左侧才能理解右侧"
- `key_gaps` 标注最大障碍点（通常是 `known_unknown` 中的核心依赖）

---

## 完成标准

profile 对象完整后：

1. 简要向用户描述诊断结果：
   > "好，我大概摸清了。你的 Rust 基础还不错——变量、控制流没问题。最大的挑战是所有权体系，这是 Rust 学习曲线最陡的地方，我们从这里开始重点突破。"

2. 将 state 更新为 `"CRAWL"`，保存 `learning_state.json`

3. **立刻在同一条回复中开始 CRAWL**——不等用户回复，直接调用 `web_search`。
   如需告知用户，用一句话内嵌在诊断结果后面，紧接着输出搜索结果：
   > "我去找一些好的学习资料，整理成课程——这需要一点时间，稍等。"

   ❌ 错误做法：说完这句话后换行等待用户回复再搜索。
   ✅ 正确做法：这句话之后立刻在**同一个 response** 里调用 `web_search` 工具。
