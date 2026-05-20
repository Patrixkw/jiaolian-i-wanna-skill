#!/usr/bin/env python3
"""
wiki_compiler.py — LLM Wiki 编译脚本

用途：将 raw/ 目录中的原始素材编译为教学级 wiki 页面。
运行：python scripts/wiki_compiler.py <topic_slug> [--level B|C] [--concept <concept>]

B 级：课时粒度，覆盖整个教学计划
C 级：概念粒度，针对单一概念深挖（需要 --concept 参数）
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_state(wiki_dir: Path) -> dict:
    state_file = wiki_dir / "learning_state.json"
    if not state_file.exists():
        raise FileNotFoundError(f"learning_state.json not found in {wiki_dir}")
    with open(state_file, encoding="utf-8") as f:
        return json.load(f)


def save_state(wiki_dir: Path, state: dict) -> None:
    state["_updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file = wiki_dir / "learning_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_manifest(wiki_dir: Path) -> dict:
    manifest_file = wiki_dir / "raw" / "manifest.json"
    if not manifest_file.exists():
        return {"resources": []}
    with open(manifest_file, encoding="utf-8") as f:
        return json.load(f)


def load_raw_files(wiki_dir: Path, resource_ids: list[str]) -> list[dict]:
    """加载指定 resource id 对应的 raw 文件内容"""
    manifest = load_manifest(wiki_dir)
    raw_dir = wiki_dir / "raw"
    results = []

    id_set = set(resource_ids) if resource_ids else None

    for resource in manifest.get("resources", []):
        if id_set and resource["id"] not in id_set:
            continue
        if resource.get("status") != "full_text":
            continue
        raw_file = raw_dir / resource.get("raw_file", "")
        if raw_file.exists():
            content = raw_file.read_text(encoding="utf-8")
            results.append({
                "id": resource["id"],
                "title": resource["title"],
                "url": resource.get("url", ""),
                "type": resource["type"],
                "content": content,
                "covers_concepts": resource.get("covers_concepts", []),
            })
    return results


def build_lesson_wiki_b(
    lesson: dict,
    raw_contents: list[dict],
    profile: dict,
    topic: str,
) -> str:
    """
    生成 B 级课时页。

    实际项目中这里会调用 LLM API 进行智能编译。
    这里提供骨架结构，LLM 在执行时会填充具体内容。
    """
    prereqs = ", ".join(lesson.get("prerequisites", ["—"])) or "—"
    sources = ", ".join(r["id"] for r in raw_contents) or "（无外部素材，使用 LLM 内部知识）"
    lesson_type = lesson.get("type", "textbook")
    duration = lesson.get("estimated_duration", 30)

    # 根据 level 选择解释深度提示
    level = profile.get("level", "beginner")
    depth_hint = {
        "absolute-beginner": "假设读者零基础，用日常类比，避免专业术语",
        "beginner": "假设读者有基础编程经验，可以用编程概念类比",
        "beginner-with-programming-background": "假设读者熟悉其他语言，用对比方式解释",
        "intermediate": "可以使用专业术语，重点在实践和边界条件",
        "advanced": "聚焦高级特性和细节，可以省略基础解释",
    }.get(level, "使用清晰直白的语言")

    source_titles = "\n".join(f"  - [{r['id']}] {r['title']}" for r in raw_contents)
    raw_summary = "\n\n".join(
        f"### 来源 [{r['id']}]：{r['title']}\n\n{r['content'][:2000]}{'...(截断)' if len(r['content']) > 2000 else ''}"
        for r in raw_contents
    )

    template = f"""# L{lesson['id']:02d}：{lesson['title']}

## 元信息
- **前置知识**：{prereqs}
- **课型**：{lesson_type}
- **预计时长**：{duration} 分钟
- **来源**：{sources}

---

## [LLM 编译指令 — 执行时替换此区块]

请根据以下原始素材，为 **{level}** 水平的学习者编写「{lesson['title']}」的教学内容。

编写要求：
- {depth_hint}
- 课型为 {lesson_type}，内容结构需符合该课型模板
- 核心概念部分：300~500 字
- 关键示例：1~2 个，附解析
- 常见误区：1~3 个
- 课后检验题：2~3 题（核心题 + 应用题 + 可选迁移题）

原始素材：
{source_titles if source_titles else "（无外部素材）"}

---

{raw_summary}

---

## 核心概念

（由 LLM 编译填充）

## 关键示例

（由 LLM 编译填充）

## 常见误区

（由 LLM 编译填充）

## 课后检验题

1. **核心题**：（由 LLM 编译填充）
2. **应用题**：（由 LLM 编译填充）
"""
    return template


def build_concept_wiki_c(
    concept: str,
    related_lesson_file: str,
    raw_contents: list[dict],
    profile: dict,
    trigger_reason: str,
) -> str:
    """生成 C 级概念页（按需拆解）"""
    level = profile.get("level", "beginner")

    return f"""# 概念深挖：{concept}

> 触发原因：{trigger_reason}
> 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}
> 关联课时：{related_lesson_file}

---

## [LLM 编译指令 — 执行时替换此区块]

为 **{level}** 水平的学习者，对「{concept}」进行深度概念解析。

结构（按顺序）：
1. **定义**：用一句话给出精确定义
2. **类比**：用生活或其他领域的类比解释
3. **正例**：1~2 个正确使用的示例（代码或场景）
4. **反例**：1 个典型错误用法及原因
5. **边界条件**：这个概念在什么情况下失效或需要特殊处理
6. **与相邻概念的区别**：和容易混淆的 1~2 个概念做对比

---

## 定义

（由 LLM 填充）

## 类比

（由 LLM 填充）

## 正例

（由 LLM 填充）

## 反例

（由 LLM 填充）

## 边界条件

（由 LLM 填充）

## 与相邻概念的区别

（由 LLM 填充）
"""


def build_index(state: dict, lessons: list[dict]) -> str:
    """生成 wiki/index.md"""
    topic = state["topic"]
    profile = state["profile"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = []
    for lesson in lessons:
        prereqs = ", ".join(lesson.get("prerequisites", [])) or "—"
        status = lesson.get("status", "pending")
        status_icon = {"passed": "✅", "pending": "⏳", "paused": "⏸", "skipped": "⏭"}.get(status, "⏳")
        rows.append(
            f"| L{lesson['id']:02d} | {lesson['title']} | {lesson['type']} "
            f"| {prereqs} | {status_icon} {status} |"
        )

    table = "\n".join(rows)

    compile_c = state.get("compile_c_triggered", [])
    c_rows = "\n".join(
        f"| {c['concept']} | concepts/{Path(c['file']).name} | {c['triggered_by']} |"
        for c in compile_c
    ) or "（尚未触发）"

    return f"""# {topic} 学习 Wiki 索引

生成时间：{now_str}
学习者级别：{profile.get('level', '未知')}
核心障碍：{', '.join(profile.get('key_gaps', ['未知']))}
依赖链：{profile.get('dependency_chain', '未知')}

---

## 课时列表

| 课时 | 标题 | 课型 | 前置 | 状态 |
|---|---|---|---|---|
{table}

---

## 概念依赖图

{profile.get('dependency_chain', '（编译后填充）')}

---

## C 级概念页（按需生成）

| 概念 | 文件 | 触发原因 |
|---|---|---|
{c_rows}
"""


def slugify(text: str) -> str:
    """将中英文标题转为 slug（小写、下划线分隔）"""
    text = re.sub(r"[^\w一-鿿]+", "_", text.lower())
    return text.strip("_")[:40]


def scaffold_lesson_dir(lesson: dict, wiki_dir: Path, manifest: dict) -> Path:
    """
    为单个课时创建独立文件夹，填充 sources/、wiki.md、session.json。
    幂等：文件夹已存在且完整时直接返回路径。
    """
    lesson_slug = f"L{lesson['id']:02d}_{slugify(lesson['title'])}"
    lesson_dir = wiki_dir / "lessons" / lesson_slug
    sources_dir = lesson_dir / "sources"

    if lesson_dir.exists() and (lesson_dir / "wiki.md").exists():
        return lesson_dir  # 已就绪，幂等跳过

    sources_dir.mkdir(parents=True, exist_ok=True)

    # 1. 筛选本课相关素材
    lesson_concepts = lesson.get("covers_concepts", [lesson["title"]])
    relevant = [
        r for r in manifest.get("resources", [])
        if any(c in r.get("covers_concepts", []) for c in lesson_concepts)
    ]
    full_text = [r for r in relevant if r.get("status") == "full_text"]
    link_only = [r for r in relevant if r.get("status") == "link_only"]

    # 2. 复制 raw 文件到 sources/
    for resource in full_text:
        raw_file = wiki_dir / "raw" / resource.get("raw_file", "")
        if raw_file.exists():
            local_name = f"{resource['id']}_{raw_file.name}"
            shutil.copy2(raw_file, sources_dir / local_name)
            resource["_local_file"] = local_name  # 临时字段，不写回 manifest

    # 3. 写 sources.json
    sources_data = {
        "lesson_id": lesson["id"],
        "lesson_title": lesson["title"],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "covers_concepts": lesson_concepts,
        "sources": [
            {
                "id": r["id"],
                "title": r["title"],
                "url": r.get("url", ""),
                "type": r["type"],
                "local_file": r.get("_local_file", ""),
            }
            for r in full_text
        ],
        "link_only_resources": [
            {
                "id": r["id"],
                "title": r["title"],
                "url": r.get("url", ""),
                "missing_skill": r.get("missing_skill", ""),
                "note": "有对应 skill 时可补充全文",
            }
            for r in link_only
        ],
    }
    (sources_dir / "sources.json").write_text(
        json.dumps(sources_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4. 复制 wiki.md（从全局 wiki/ 目录）
    wiki_refs = lesson.get("wiki_refs", [])
    wiki_src = wiki_dir / "wiki" / wiki_refs[0] if wiki_refs else None
    if wiki_src and wiki_src.exists():
        shutil.copy2(wiki_src, lesson_dir / "wiki.md")
    else:
        # wiki 页还没生成时写占位符
        (lesson_dir / "wiki.md").write_text(
            f"# L{lesson['id']:02d}：{lesson['title']}\n\n（教学内容待编译）\n",
            encoding="utf-8",
        )

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

    # 6. 将 lesson_dir 写回 lesson 对象（调用方负责保存 state）
    lesson["lesson_dir"] = f"lessons/{lesson_slug}/"

    print(f"  📁 课时文件夹就绪：{lesson_dir.relative_to(wiki_dir)}")
    return lesson_dir


def compile_b(wiki_dir: Path, state: dict) -> None:
    """执行 B 级编译：为所有课时生成 wiki 页"""
    wiki_out_dir = wiki_dir / "wiki"
    wiki_out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(wiki_dir)
    profile = state["profile"]
    topic = state["topic"]
    lessons = state["plan"]["lessons"]

    print(f"开始 B 级编译，共 {len(lessons)} 个课时...")

    for lesson in lessons:
        lesson_id = lesson["id"]
        out_file = wiki_out_dir / (lesson["wiki_refs"][0] if lesson.get("wiki_refs") else f"L{lesson_id:02d}_{lesson['title']}.md")

        if out_file.exists():
            print(f"  跳过 L{lesson_id:02d}（已存在）：{out_file.name}")
            continue

        # 找覆盖该课时概念的 raw 文件
        lesson_concepts = lesson.get("covers_concepts", [lesson["title"]])
        relevant_ids = [
            r["id"] for r in manifest.get("resources", [])
            if r.get("status") == "full_text"
            and any(c in r.get("covers_concepts", []) for c in lesson_concepts)
        ]
        raw_contents = load_raw_files(wiki_dir, relevant_ids)

        content = build_lesson_wiki_b(lesson, raw_contents, profile, topic)
        out_file.write_text(content, encoding="utf-8")
        print(f"  ✅ L{lesson_id:02d}：{out_file.name}")

    # 更新 index.md
    index_content = build_index(state, lessons)
    index_file = wiki_out_dir / "index.md"
    index_file.write_text(index_content, encoding="utf-8")
    print(f"  ✅ index.md 已更新")

    # 为第一课（即将开始的课时）预先创建课时文件夹
    first_pending = next(
        (l for l in lessons if l.get("status", "pending") == "pending"), None
    )
    if first_pending:
        print(f"\n为第一课预创建课时文件夹...")
        scaffold_lesson_dir(first_pending, wiki_dir, manifest)

    state["wiki_version"] = "B"
    state["state"] = "PLAN"
    save_state(wiki_dir, state)
    print("B 级编译完成，state → PLAN")


def compile_c(wiki_dir: Path, state: dict, concept: str, trigger_reason: str = "user_confusion") -> None:
    """执行 C 级编译：为单一概念生成深挖页"""
    concepts_dir = wiki_dir / "wiki" / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    concept_slug = concept.lower().replace(" ", "_").replace("/", "_")
    out_file = concepts_dir / f"{concept_slug}.md"

    # 找相关 raw 素材
    manifest = load_manifest(wiki_dir)
    relevant_ids = [
        r["id"] for r in manifest.get("resources", [])
        if r.get("status") == "full_text" and concept in r.get("covers_concepts", [])
    ]
    raw_contents = load_raw_files(wiki_dir, relevant_ids)

    # 找关联课时
    related_lesson = next(
        (
            l["wiki_refs"][0] if l.get("wiki_refs") else f"L{l['id']:02d}"
            for l in state["plan"]["lessons"]
            if concept in l.get("title", "")
            or concept in " ".join(l.get("wiki_refs", []))
        ),
        "unknown",
    )

    content = build_concept_wiki_c(
        concept=concept,
        related_lesson_file=related_lesson,
        raw_contents=raw_contents,
        profile=state["profile"],
        trigger_reason=trigger_reason,
    )
    out_file.write_text(content, encoding="utf-8")

    # 更新 state
    compile_c_entry = {
        "concept": concept,
        "file": str(out_file.relative_to(wiki_dir)),
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "triggered_by": trigger_reason,
    }
    state.setdefault("compile_c_triggered", []).append(compile_c_entry)

    # 更新 index.md
    index_file = wiki_dir / "wiki" / "index.md"
    if index_file.exists():
        index_content = build_index(state, state["plan"]["lessons"])
        index_file.write_text(index_content, encoding="utf-8")

    save_state(wiki_dir, state)
    print(f"✅ C 级概念页生成：{out_file}")


def init_wiki_dir(topic_slug: str, base_dir: Path = Path(".")) -> Path:
    """初始化 wiki 目录结构"""
    wiki_dir = base_dir / f"{topic_slug}_wiki"
    (wiki_dir / "raw").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)

    manifest_file = wiki_dir / "raw" / "manifest.json"
    if not manifest_file.exists():
        manifest_file.write_text(
            json.dumps({"topic": topic_slug, "resources": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"✅ Wiki 目录初始化：{wiki_dir}")
    return wiki_dir


def main():
    parser = argparse.ArgumentParser(description="LLM Wiki 编译脚本")
    parser.add_argument("topic_slug", help="学习主题 slug（如 rust, machine-learning）")
    parser.add_argument(
        "--level",
        choices=["B", "C"],
        default="B",
        help="编译级别：B=课时粒度（默认），C=概念粒度",
    )
    parser.add_argument("--concept", help="C 级编译时指定概念名称")
    parser.add_argument("--trigger-reason", default="user_confusion", help="C 级编译触发原因")
    parser.add_argument("--init", action="store_true", help="只初始化目录结构，不编译")
    parser.add_argument(
        "--scaffold",
        type=int,
        metavar="LESSON_ID",
        help="为指定课时 ID 创建独立文件夹（如 --scaffold 2）",
    )
    default_data_dir = str(Path.home() / ".claude" / "coach-sessions")
    parser.add_argument("--base-dir", default=default_data_dir, help=f"学习数据根目录（默认 {default_data_dir}）")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    wiki_dir = base_dir / f"{args.topic_slug}_wiki"

    if args.init:
        init_wiki_dir(args.topic_slug, base_dir)
        return

    if not wiki_dir.exists():
        print(f"错误：Wiki 目录不存在：{wiki_dir}", file=sys.stderr)
        print(f"提示：先运行 --init 初始化目录", file=sys.stderr)
        sys.exit(1)

    state = load_state(wiki_dir)

    if args.scaffold is not None:
        lessons = state.get("plan", {}).get("lessons", [])
        lesson = next((l for l in lessons if l["id"] == args.scaffold), None)
        if not lesson:
            print(f"错误：找不到课时 ID {args.scaffold}", file=sys.stderr)
            sys.exit(1)
        manifest = load_manifest(wiki_dir)
        scaffold_lesson_dir(lesson, wiki_dir, manifest)
        save_state(wiki_dir, state)
        return

    if args.level == "B":
        compile_b(wiki_dir, state)
    elif args.level == "C":
        if not args.concept:
            print("错误：C 级编译需要指定 --concept 参数", file=sys.stderr)
            sys.exit(1)
        compile_c(wiki_dir, state, args.concept, args.trigger_reason)


if __name__ == "__main__":
    main()
