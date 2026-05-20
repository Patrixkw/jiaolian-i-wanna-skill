# CRAWL + COMPILE 阶段 — 知识获取与 Wiki 编译

---

## CRAWL 阶段

### 目标

采集覆盖 `dependency_chain` 所有节点的高质量教学素材，存入 `raw/` 目录。

### 素材类型与获取策略

```python
def acquire_resource(resource_url, resource_type, resource_title):
    if resource_type == "webpage":
        content = web_fetch(resource_url)
        save_to_raw(content, title=resource_title, type="webpage")

    elif resource_type == "video":
        if has_capability("video_download"):
            video_path = video_download(resource_url)
            if has_capability("video_transcribe") or has_capability("audio_transcribe"):
                transcript = transcribe(video_path)
                save_to_raw(transcript, title=resource_title, type="video_transcript")
                return
        # 降级处理
        notify_user(
            message=f"我找到了一个很好的视频资料「{resource_title}」，"
                    f"但我目前没有视频下载和转写能力。\n"
                    f"你可以：\n"
                    f"1. 帮我安装 video-download / whisper-transcribe skill，"
                    f"我就能把视频转成文字纳入教学\n"
                    f"2. 先跳过，我用文字资料教这部分"
        )
        save_to_raw(
            {"url": resource_url, "title": resource_title},
            type="video_link",
            status="link_only",
            missing_skill="video_download"
        )

    elif resource_type == "book_pdf":
        if has_capability("ocr") or has_capability("pdf_extract"):
            text = extract_pdf(resource_url)
            save_to_raw(text, title=resource_title, type="book_text")
            return
        notify_user(
            message=f"我找到了书本资料「{resource_title}」，"
                    f"但我目前没有 PDF 提取能力。\n"
                    f"建议安装 pdf-reading skill 后我能全文纳入教学。"
        )
        save_to_raw(
            {"url": resource_url, "title": resource_title},
            type="book_link",
            status="link_only",
            missing_skill="pdf_extract"
        )

    elif resource_type == "github_repo":
        content = web_fetch(resource_url)  # README + 关键文件
        save_to_raw(content, title=resource_title, type="code_example")
```

### 第一轮：广度扫描

搜索策略（覆盖 dependency_chain 每个节点）：

```python
search_queries = [
    f"{topic} 教程 入门",                    # 体系资源
    f"{topic} {key_gap} 详解",              # 重点资源（针对 key_gaps）
    f"{topic} 实战项目 示例",               # 实践资源
    f"{topic} 官方文档 getting started",    # 官方资源
    f"{topic} {dependency_chain[0]} 概念",  # 依赖链第一节点
]
```

对每个搜索结果：
1. 识别资源类型（webpage / video / book_pdf / github_repo）
2. 调用 `acquire_resource()`
3. 记录到 `manifest.json`

### manifest.json 结构

```json
{
  "topic": "Rust 编程",
  "crawled_at": "2026-05-20T15:00:00+08:00",
  "resources": [
    {
      "id": "001",
      "title": "The Rust Programming Language - Ownership",
      "url": "https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html",
      "type": "webpage",
      "acquired_via": "web_fetch",
      "status": "full_text",
      "raw_file": "001_rust_ownership.md",
      "covers_concepts": ["所有权", "移动语义", "克隆"]
    },
    {
      "id": "004",
      "title": "Rust 所有权讲解视频",
      "url": "https://...",
      "type": "video_link",
      "acquired_via": "fallback_metadata_only",
      "status": "link_only",
      "missing_skill": "video_download",
      "covers_concepts": ["所有权"]
    }
  ]
}
```

### 第二轮：针对性补采

编译 B 级 wiki 后，检查覆盖度：

```python
uncovered = [
    concept for concept in dependency_chain_nodes
    if not any(concept in r["covers_concepts"] for r in manifest["resources"] if r["status"] == "full_text")
]

for concept in uncovered:
    web_search(f"{topic} {concept} 教程 详解")
    # 补采并添加到 raw/
```

同时检查 `status: "link_only"` 的高价值资源——如果用户中途安装了缺失 skill，重新获取全文。

---

## COMPILE_B 阶段

### 目标

将 `raw/` 中的素材编译为课时级（B 级）wiki 页面，每页覆盖一个可独立教学的知识单元。

### 编译原则

- **综合多源**：不复制粘贴，用教学语言重写
- **教学优先**：以用户 profile 为基础，选择合适的解释深度
- **immutable raw**：raw/ 目录只读，wiki/ 可反复重写
- **溯源标注**：每个 wiki 页脚注明来源（manifest 中的 id 列表）
- **视频素材**：有转写内容时与网页素材同等对待；仅有链接时作为补充资源标注

### 课时页结构

文件名格式：`L{序号}_{概念英文}_wiki.md`（序号两位，如 L01、L10）

```markdown
# L{N}：{课时标题}

## 元信息
- **前置知识**：{必须先掌握的概念列表}
- **课型**：{project | textbook | case_study | socratic | drill}
- **预计时长**：{N} 分钟
- **来源**：raw/{id 列表}

---

## 核心概念

{教学内容——用用户能理解的语言，结合 profile.level 调整深度}

## 关键示例

```{language}
{代码示例 / 案例 / 场景}
```

{示例解析}

## 常见误区

{1~3 个典型错误或陷阱}

## 课后检验题

1. **核心题**：{必出，检验核心概念理解}
2. **应用题**：{检验动手能力或场景应用}
3. **迁移题**（可选）：{检验深层理解，在关键课时使用}
```

### index.md 结构

```markdown
# {topic} 学习 Wiki 索引

生成时间：{时间}
学习者：{level} 级别，{key_gaps 摘要}

## 课时列表

| 课时 | 标题 | 课型 | 前置 | 状态 |
|---|---|---|---|---|
| L01 | {title} | {type} | — | pending |
| L02 | {title} | {type} | L01 | pending |

## 概念依赖图（文字版）

{dependency_chain}

## C级概念页（按需生成）

| 概念 | 文件 | 触发原因 |
|---|---|---|
```

index.md 控制在 **单次 context window 可读**范围（约 200 行以内）。

---

## COMPILE_C：按需拆解到概念粒度

### 触发条件

任意一项满足即触发：
- 用户对某个概念连续追问 2 次以上
- TEACH 阶段检测到前置概念未打牢（用户代码暴露误解）
- 用户主动说"我还是不太懂 X"

### 执行流程

```python
def trigger_compile_c(concept, lesson_wiki_ref):
    # 1. 从课时页提取该概念的内容
    # 2. 结合 raw/ 中覆盖该概念的素材
    # 3. 生成独立概念页到 wiki/concepts/
    # 4. 更新 index.md 的 C级概念页表格
    # 5. 记录到 state["compile_c_triggered"]
    
    output_file = f"wiki/concepts/{concept_slug}.md"
    state["compile_c_triggered"].append({
        "concept": concept,
        "file": output_file,
        "triggered_at": now_iso8601(),
        "triggered_by": "user_confusion"
    })
```

概念页结构比课时页更细粒度：专注单一概念，多角度解释（定义→类比→示例→反例→边界条件）。

---

## 课时文件夹脚手架（SCAFFOLD_LESSON_DIR）

### 时机与触发

| 触发时机 | 为哪一课准备 |
|---|---|
| COMPILE_B 完成、state → PLAN 时 | 第 1 课（立刻就要上） |
| PLAN 用户确认后 | 第 1 课（如已存在则跳过） |
| ASSESS pass、注册下一课 schedule 时 | 下一课（提前备好） |
| TEACH 开始前检查 | 当前课（兜底：如果上面两步漏了） |

### 文件夹结构

```
lessons/L{N:02d}_{slug}/
├── sources/
│   ├── {raw_id}_{filename}.md    # 从 raw/ 筛选复制的相关素材
│   └── sources.json              # 本课素材清单
├── wiki.md                       # 本课编译后的教学内容（从 wiki/L{N}.md 复制）
└── session.json                  # 本课会话记录（初始为空）
```

### sources.json 结构

```json
{
  "lesson_id": 1,
  "lesson_title": "所有权与借用",
  "prepared_at": "2026-05-20T15:00:00+08:00",
  "covers_concepts": ["所有权", "移动语义", "借用"],
  "sources": [
    {
      "id": "001",
      "title": "The Rust Book - Ownership",
      "url": "https://...",
      "type": "webpage",
      "local_file": "001_rust_ownership.md"
    }
  ],
  "link_only_resources": [
    {
      "id": "004",
      "title": "Rust 所有权讲解视频",
      "url": "https://...",
      "missing_skill": "video_download",
      "note": "有转写能力时可补充全文"
    }
  ]
}
```

### session.json 初始结构

```json
{
  "lesson_id": 1,
  "lesson_title": "所有权与借用",
  "lesson_type": "project",
  "started_at": null,
  "completed_at": null,
  "interactions": [],
  "assess_history": [],
  "compile_c_triggered": []
}
```

### 脚手架执行逻辑

```python
def scaffold_lesson_dir(lesson, wiki_dir, manifest):
    lesson_slug = f"L{lesson['id']:02d}_{slugify(lesson['title'])}"
    lesson_dir = wiki_dir / "lessons" / lesson_slug
    
    if lesson_dir.exists():
        return  # 已存在，幂等跳过
    
    sources_dir = lesson_dir / "sources"
    sources_dir.mkdir(parents=True)
    
    # 1. 筛选本课相关素材（从 manifest 中匹配 covers_concepts）
    lesson_concepts = lesson.get("covers_concepts", [lesson["title"]])
    relevant = [
        r for r in manifest["resources"]
        if any(c in r.get("covers_concepts", []) for c in lesson_concepts)
    ]
    full_text = [r for r in relevant if r.get("status") == "full_text"]
    link_only = [r for r in relevant if r.get("status") == "link_only"]
    
    # 2. 复制 raw 文件到 sources/
    for resource in full_text:
        raw_file = wiki_dir / "raw" / resource["raw_file"]
        if raw_file.exists():
            dest = sources_dir / f"{resource['id']}_{resource['raw_file']}"
            shutil.copy2(raw_file, dest)
            resource["local_file"] = dest.name
    
    # 3. 写 sources.json
    sources_json = {
        "lesson_id": lesson["id"],
        "lesson_title": lesson["title"],
        "prepared_at": now_iso8601(),
        "covers_concepts": lesson_concepts,
        "sources": [
            {"id": r["id"], "title": r["title"], "url": r.get("url",""),
             "type": r["type"], "local_file": r.get("local_file","")}
            for r in full_text
        ],
        "link_only_resources": [
            {"id": r["id"], "title": r["title"], "url": r.get("url",""),
             "missing_skill": r.get("missing_skill","")}
            for r in link_only
        ],
    }
    (sources_dir / "sources.json").write_text(
        json.dumps(sources_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 4. 复制 wiki.md
    wiki_src = wiki_dir / "wiki" / lesson.get("wiki_refs", [""])[0]
    if wiki_src.exists():
        shutil.copy2(wiki_src, lesson_dir / "wiki.md")
    
    # 5. 初始化 session.json
    session = {
        "lesson_id": lesson["id"],
        "lesson_title": lesson["title"],
        "lesson_type": lesson["type"],
        "started_at": None,
        "completed_at": None,
        "interactions": [],
        "assess_history": [],
        "compile_c_triggered": [],
    }
    (lesson_dir / "session.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 6. 更新 lesson 对象中的 lesson_dir 字段
    lesson["lesson_dir"] = f"lessons/{lesson_slug}/"
```

---

### 完成标准

- `wiki/index.md` 存在且可读
- `dependency_chain` 上每个核心概念至少有一个课时页覆盖
- `manifest.json` 中 `full_text` 资源 ≥ 3 个
- `lessons/L01_xxx/` 文件夹已创建并包含 `wiki.md` + `sources/sources.json` + `session.json`

将 state 更新为 `"PLAN"`。
