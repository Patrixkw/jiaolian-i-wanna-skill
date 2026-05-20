# 调度接口规范

## 何时注册 Schedule

| 事件 | 注册动作 |
|---|---|
| PLAN 确认后 | 注册第一课 schedule |
| ASSESS pass 后 | 注册下一课 schedule（覆盖上一条） |
| ASSESS partial 后 | 注册复习 schedule（30 分钟后或次日同时间）|
| REVIEW 完成后 | 注册重考 schedule（24 小时后）|

---

## Runtime 适配

skill 运行时按顺序检测可用能力，选择第一个可用的：

```python
def register_next_session(state, lesson_id=None, override_cron=None):
    lesson_id = lesson_id or state["current_lesson"]
    lesson = get_lesson(state, lesson_id)
    
    schedule_entry = {
        "task_id": f"coach_{state['topic_slug']}_L{lesson_id:02d}",
        "cron": override_cron or state["schedule"]["cron"],
        "prompt": build_resume_prompt(state, lesson_id),
        "state_file": f"{state['wiki_dir']}learning_state.json",
        "retry_policy": state["schedule"]["retry_policy"],
        "registered_at": now_iso8601()
    }
    
    if has_capability("cron_register"):          # Hermes / OpenClaw
        cron_register(schedule_entry)
        registered_via = "cron_register"
    elif has_capability("task_schedule"):         # Claude Code task
        task_schedule(schedule_entry)
        registered_via = "task_schedule"
    elif has_capability("heartbeat"):             # 心跳模式
        heartbeat_append(schedule_entry)
        registered_via = "heartbeat"
    else:
        # 无调度能力：提醒用户手动返回
        remind_user_manual_schedule(state, lesson_id)
        registered_via = "manual_reminder"
    
    state["schedule"]["registered_via"] = registered_via
    state["schedule"]["task_id"] = schedule_entry["task_id"]
    state["schedule"]["last_registered"] = now_iso8601()
    save_state(state)
```

### Claude Code 环境（本项目主环境）

使用 `CronCreate` 工具注册定时任务：

```python
# 注册时调用 CronCreate
cron_create(
    schedule=state["schedule"]["cron"],  # "0 9 * * 1-5"
    prompt=build_resume_prompt(state, lesson_id),
    description=f"教练课：{state['topic']} 第 {lesson_id} 课",
)
```

---

## Resume Prompt 生成

```python
def build_resume_prompt(state, lesson_id):
    lesson = get_lesson(state, lesson_id)
    state_file = f"{state['wiki_dir']}learning_state.json"
    
    return f"""
你是一个苏格拉底式学习教练。

请读取学习状态文件：{state_file}
当前课时：第 {lesson_id} 课「{lesson['title']}」
课型：{lesson['type']}

执行流程：
1. 读取 learning_state.json 确认当前状态
2. 读取 {state['wiki_dir']}wiki/{lesson['wiki_refs'][0]} 获取课时内容
3. 按照 references/05-teach.md 中 {lesson['type']} 课型模板执行教学
4. 教学结束后按 references/06-assess.md 执行检验

开场：用一句话打招呼，提醒用户今天学什么。
""".strip()
```

---

## 无调度能力时的手动提醒

```python
def remind_user_manual_schedule(state, next_lesson_id):
    lesson = get_lesson(state, next_lesson_id)
    next_time = calculate_next_slot(state["time_commitment"])
    
    reply(
        f"✅ 第 {state['current_lesson']} 课完成！\n\n"
        f"下一课「{lesson['title']}」安排在 {next_time}。\n"
        f"到时候回来找我说「继续学 {state['topic']}」就行。\n\n"
        f"（当前环境不支持自动提醒，需要你手动回来。）"
    )
```

---

## 动态调整策略

### 加快节奏

触发条件：连续 3 节课首次 ASSESS 直接 pass

```python
reply("你这 3 课都是一遍过——节奏要不要加快？"
      "我可以把每天的课时改成 2 节，或者跳过练习直接进检验。")
# 等用户确认后修改 cron 或 plan
```

### 放慢节奏

触发条件：连续 2 节课需要 REVIEW

```python
reply("这两课都卡了一下——要不要把节奏放慢一点？"
      "比如每节课后加 1 天消化时间？")
```

### 暂停调度

触发条件：用户在计划时间内 3 天无响应

```python
if days_since_last_response(state) >= 3:
    pause_schedule(state["schedule"]["task_id"])
    state["schedule"]["paused"] = True
    state["schedule"]["paused_at"] = now_iso8601()
    save_state(state)
    # 不主动发消息，等用户回来时检测 paused 状态
```

恢复时（用户主动开始对话）：

```python
if state["schedule"].get("paused"):
    days_paused = (now() - parse_iso(state["schedule"]["paused_at"])).days
    reply(f"欢迎回来！你离开了 {days_paused} 天。"
          f"我们从第 {state['current_lesson']} 课「{lesson_title}」继续？")
    # 用户确认后取消 paused，重新注册 schedule
```

---

## Next-slot 计算

```python
def calculate_next_slot(time_commitment):
    now = datetime.now(tz=ZoneInfo(time_commitment["timezone"]))
    preferred_time = time_commitment["preferred_time"]  # "09:00"
    slots = time_commitment["preferred_slots"]
    
    hour, minute = map(int, preferred_time.split(":"))
    
    # 找下一个满足 preferred_slots 条件的日期
    candidate = now.replace(hour=hour, minute=minute, second=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    
    while not matches_slot(candidate, slots):
        candidate += timedelta(days=1)
    
    return candidate.strftime("%m月%d日 %H:%M")
```
