"""Job Hunt CLI 入口。"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from src.matcher import analyze_gaps, generate_suggestions

console = Console()


@click.group()
def cli():
    """求职自动化工具箱 — JD匹配、简历优化、投递追踪。"""


@cli.command()
@click.option("--resume", "-r", prompt="简历文件路径", help="简历文本文件路径")
@click.option("--jd", "-j", prompt="JD文件路径", help="职位描述文本文件路径")
@click.option("--json-output", is_flag=True, help="以 JSON 格式输出")
def match(resume: str, jd: str, json_output: bool):
    """分析简历与 JD 的匹配度。"""
    resume_text = Path(resume).read_text()
    jd_text = Path(jd).read_text()

    result = analyze_gaps(resume_text, jd_text)
    suggestions = generate_suggestions(result)

    if json_output:
        click.echo(json.dumps({**result, "suggestions": suggestions}, indent=2))
        return

    console.print(f"\n[bold]📊 匹配分析结果[/bold]")
    console.print(f"  匹配度: [bold]{result['match_percent']}[/bold] ({result['match_quality']})")
    console.print(f"  JD 技能数: {result['jd_skill_count']}")
    console.print(f"  简历技能数: {result['resume_skill_count']}")
    console.print(f"  共同技能: {len(result['matched_skills'])}")

    if result["missing_skills"]:
        console.print(f"\n[bold red]🔴 缺失技能 ({len(result['missing_skills'])})[/bold red]")
        for s in result["missing_skills"]:
            console.print(f"  • {s}")

    if result["matched_skills"]:
        console.print(f"\n[bold green]✅ 已匹配技能 ({len(result['matched_skills'])})[/bold green]")
        console.print(f"  {', '.join(result['matched_skills'][:10])}")

    console.print(f"\n[bold yellow]💡 调整建议[/bold yellow]")
    for s in suggestions:
        console.print(f"  {s}")


@cli.command()
@click.argument("resume_file")
@click.argument("jd_file")
@click.option("--output", "-o", default="resume-tailored.md", help="输出路径")
def tailor(resume_file: str, jd_file: str, output: str):
    """根据 JD 定制简历。"""
    resume_text = Path(resume_file).read_text()
    jd_text = Path(jd_file).read_text()

    result = analyze_gaps(resume_text, jd_text)

    # 生成定制建议
    lines = [
        "# 🎯 简历定制报告\n",
        f"**目标岗位匹配度:** {result['match_percent']}\n",
        "## 需要补充的技能\n",
    ]
    for s in result["missing_skills"]:
        lines.append(f"- **{s}** — 在对应项目经历中补充此技术栈的实践描述\n")

    lines.extend([
        "\n## 建议强化描述\n",
    ])
    for s in result["matched_skills"]:
        lines.append(f"- 在简历中更突出 **{s}** 相关的工作成果（用量化数据）\n")

    Path(output).write_text("".join(lines))
    console.print(f"[green]✅ 简历定制建议已保存到 {output}[/green]")


@cli.command()
@click.option("--company", prompt="公司名")
@click.option("--role", prompt="职位")
@click.option("--status", type=click.Choice(["投递", "已联系", "面试", "待定", "拒绝", "offer"]), default="投递")
@click.option("--date", default="today", help="日期 (YYYY-MM-DD 或 today)")
def track(company: str, role: str, status: str, date: str):
    """记录投递进度。"""
    from datetime import date as dt_date
    d = str(dt_date.today()) if date == "today" else date
    log_path = Path("data/applications.csv")
    log_path.parent.mkdir(exist_ok=True)

    header = "date,company,role,status\n" if not log_path.exists() else ""
    with open(log_path, "a") as f:
        if header:
            f.write(header)
        f.write(f"{d},{company},{role},{status}\n")
    console.print(f"[green]✅ 已记录: {company} - {role} ({status})[/green]")


@cli.command()
def status():
    """查看投递状态汇总。"""
    log_path = Path("data/applications.csv")
    if not log_path.exists():
        console.print("[yellow]暂无投递记录[/yellow]")
        return

    with open(log_path) as f:
        lines = f.readlines()[1:]  # skip header

    table = Table(title="📋 投递记录")
    table.add_column("日期")
    table.add_column("公司")
    table.add_column("职位")
    table.add_column("状态")

    for line in lines:
        parts = line.strip().split(",")
        if len(parts) >= 4:
            table.add_row(parts[0], parts[1], parts[2], parts[3])
    console.print(table)


if __name__ == "__main__":
    cli()
