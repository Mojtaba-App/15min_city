"""Persian markdown export of the accessibility report."""
from __future__ import annotations

from typing import Any, Dict, List


def _n(value: Any, digits: int = 0) -> str:
    if value is None:
        return "—"
    number = float(value)
    if digits == 0:
        return f"{int(round(number)):,}"
    return f"{number:,.{digits}f}"


def _table(headers: List[str], rows: List[List[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def render_report_markdown(report: Dict[str, Any]) -> str:
    meta = report["meta"]
    distribution = report["distribution"]
    lines = [
        "# گزارش تکمیلی دسترسی ۱۵ دقیقه‌ای اهواز",
        "",
        "این گزارش همان شاخص مقاله را می‌خواند و جزئیات آماری، مقایسه مکانی، حساسیت آستانه و موجودی خدمات را به آن اضافه می‌کند. جدول پایه مقاله تغییر نکرده است.",
        "",
        f"شهر: {meta['city']}. بلوک‌ها: {_n(meta['blocks'])}. جمعیت ثبت‌شده: {_n(meta['population'])}. سرعت پیاده‌روی: {meta['walking_speed_mps']} متر بر ثانیه. آستانه مقاله: {meta['paper_threshold_sec']} ثانیه.",
        "",
        meta["score_definition"],
        "",
        "## ۱. توزیع امتیاز",
        "",
        f"میانگین ساده {_n(meta['avg_score'], 2)} از ۴ است (با سه رقم اعشار {_n(meta['avg_score_exact'], 3)}) و میانگین وزنی با جمعیت {_n(meta['weighted_avg_score'], 3)} از ۴. بیشینه مشاهده‌شده {meta['max_score']} است و امتیاز ۴ در شهر وجود ندارد.",
        "",
        _table(
            ["امتیاز", "برچسب", "بلوک", "درصد بلوک", "درصد تجمعی بلوک", "جمعیت", "درصد جمعیت", "درصد تجمعی جمعیت"],
            [[
                row["score"],
                row["label"],
                _n(row["blocks"]),
                _n(row["block_pct"], 2),
                _n(row["cumulative_block_pct"], 2),
                _n(row["population"]),
                _n(row["population_pct"], 2),
                _n(row["cumulative_population_pct"], 2),
            ] for row in distribution["rows"]],
        ),
        "",
        "## ۲. ترکیب دسته‌ها",
        "",
        "هر ردیف یک ترکیب واقعی از چهار پرچم است. درصدها سهم همان ترکیب از کل بلوک‌ها و از کل جمعیت است.",
        "",
        _table(
            ["ترکیب", "امتیاز", "بلوک", "درصد بلوک", "جمعیت", "درصد جمعیت"],
            [[
                row["label"],
                row["score"],
                _n(row["blocks"]),
                _n(row["block_pct"], 2),
                _n(row["population"]),
                _n(row["population_pct"], 2),
            ] for row in report["combinations"] if row["blocks"] > 0],
        ),
        "",
        "## ۳. پوشش هر دسته",
        "",
        _table(
            ["دسته", "بلوک", "درصد بلوک", "جمعیت ساکن این بلوک‌ها", "درصد جمعیت"],
            [[
                row["label"],
                _n(row["blocks"]),
                _n(row["block_pct"], 2),
                _n(row["population"]),
                _n(row["population_pct"], 2),
            ] for row in distribution["coverage"]],
        ),
        "",
        "## ۴. منطقه و محله",
        "",
        (
            f"{_n(meta['unmatched_blocks'])} بلوک با جمعیت {_n(meta['unmatched_population'])} "
            "درون مرز محله قرار نگرفتند و در جدول‌های زیر نیستند."
        ),
        "",
        "### منطقه",
        "",
        _table(
            ["منطقه", "بلوک", "جمعیت", "میانگین ساده", "میانگین وزنی", "درصد بلوک امتیاز ۰", "آموزش ٪", "سلامت ٪", "خرید ٪", "تفریح ٪"],
            [[
                row["district_label"],
                _n(row["blocks"]),
                _n(row["population"]),
                _n(row["avg_score"], 3),
                _n(row["weighted_avg_score"], 3),
                _n(row["pct_score_0"], 2),
                _n(row["education_pct"], 2),
                _n(row["health_pct"], 2),
                _n(row["shopping_pct"], 2),
                _n(row["recreation_pct"], 2),
            ] for row in report["zones"]["districts"]],
        ),
        "",
        "### برخوردارترین محله‌ها",
        "",
        report["zones"]["highlights"]["best_rule"],
        "",
        _zone_table(report["zones"]["highlights"]["best"]),
        "",
        "### کم‌برخوردارترین محله‌ها",
        "",
        report["zones"]["highlights"]["underserved_rule"],
        "",
        _zone_table(report["zones"]["highlights"]["underserved"]),
        "",
        "## ۵. نمونه‌های مکانی",
        "",
    ]
    block = report["examples"]["highest_score_block"]
    zero = report["examples"]["zero_access_neighborhood"]
    lines.extend([
        (
            f"بلوک {block['block_gid']} در {block['neighborhood'] or 'خارج از محله'} "
            f"({block['district_label']}) امتیاز {block['score']} دارد. "
            f"جمعیت بلوک {_n(block['population'])}. "
            f"تعداد خدمت در ۱۵ دقیقه: آموزش {block['n_education']}، سلامت {block['n_health']}، "
            f"خرید {block['n_shopping']}، تفریح {block['n_recreation']}. "
            f"مختصات: {block['lat']}, {block['lon']}."
        ),
        "",
        (
            f"پهنه بدون دسترسی با بیشترین جمعیت: {zero['name']} ({zero['district_label']}). "
            f"بلوک‌ها {_n(zero['blocks'])}، جمعیت {_n(zero['population'])}، "
            f"میانگین وزنی {_n(zero['weighted_avg_score'], 3)}، "
            f"سهم امتیاز صفر {_n(zero['pct_score_0'], 2)} درصد. "
            f"مختصات مرکز: {zero['lat']}, {zero['lon']}."
        ),
        "",
        "محله‌های با میانگین وزنی بالاتر، با همان شرط حداقل ۱۰ بلوک:",
        "",
        _zone_table(report["examples"]["best_neighborhoods"]),
        "",
        "## ۶. حساسیت شاخص",
        "",
        _table(
            ["سناریو", "آستانه (ثانیه)", "میانگین ساده", "میانگین وزنی", "درصد بلوک امتیاز ۰", "آموزش ٪", "سلامت ٪", "خرید ٪", "تفریح ٪"],
            [[
                item["label"],
                item["threshold_sec"],
                _n(item["avg_score"], 2),
                _n(item["weighted_avg_score"], 3),
                _n(next(row["block_pct"] for row in item["rows"] if row["score"] == 0), 2),
                _n(item["coverage"][0]["block_pct"], 2),
                _n(item["coverage"][1]["block_pct"], 2),
                _n(item["coverage"][2]["block_pct"], 2),
                _n(item["coverage"][3]["block_pct"], 2),
            ] for item in report["sensitivity"]["scenarios"]],
        ),
        "",
        "## ۷. تعداد خدمت در دسترس",
        "",
        report["supply"]["definition"],
        "",
        _table(
            ["دسته", "بلوک بدون خدمت", "دقیقاً یک خدمت", "دو خدمت یا بیشتر", "بیشینه تعداد", "درصد جمعیت با دو خدمت یا بیشتر"],
            [[
                row["label"],
                _n(row["blocks_with_0"]),
                _n(row["blocks_with_1"]),
                _n(row["blocks_with_2_or_more"]),
                _n(row["max_facilities"]),
                _n(row["population_pct_2_or_more"], 2),
            ] for row in report["supply"]["categories"]],
        ),
        "",
        "هم‌خوانی بازشماری ۱۵ دقیقه با پرچم مقاله: "
        + ("بله، اختلاف صفر است." if report["reconciliation"]["paper_flags_match_recount"] else "خیر. اختلاف در جدول زیر است."),
        "",
        _table(
            ["دسته", "بلوک در مقاله", "بازشماری", "اختلاف"],
            [[row["label"], _n(row["paper_blocks"]), _n(row["recount_blocks"]), _n(row["delta"])] for row in report["reconciliation"]["by_category"]],
        ),
        "",
        "## ۸. موجودی خدمات مبدأ",
        "",
        report["inventory"]["note"],
        "",
        f"تعداد کل خدمات: {_n(report['inventory']['total_facilities'])}.",
        "",
        _table(
            ["دسته", "تعداد خدمت"],
            [[row["label"], _n(row["facilities"])] for row in report["inventory"]["categories"]],
        ),
        "",
        "انواعی که در داده هستند و قاعده فعلی آن‌ها را خارج از امتیاز گذاشته است:",
        "",
        _table(
            ["نوع", "تعداد", "دسته نزدیک"],
            [[row["service_type"], _n(row["facilities"]), row["suggested_label"]] for row in report["inventory"]["unclassified_relevant"]],
        ),
        "",
        "## ۹. محدودیت‌ها",
        "",
    ])
    for index, item in enumerate(report["limitations"], start=1):
        lines.append(f"{index}. {item}")
    lines.extend([
        "",
        "داشبورد همین ارقام را از `/accessibility/report` می‌خواند و نقشه کامل بلوک‌ها، چهار لایه دسته، و لایه محله و منطقه را نشان می‌دهد.",
        "",
    ])
    return "\n".join(lines)


def _zone_table(rows: List[Dict[str, Any]]) -> str:
    return _table(
        ["محله", "منطقه", "بلوک", "جمعیت", "میانگین ساده", "میانگین وزنی", "درصد بلوک امتیاز ۰", "درصد جمعیت امتیاز ۰"],
        [[
            row["name"],
            row["district_label"],
            _n(row["blocks"]),
            _n(row["population"]),
            _n(row["avg_score"], 3),
            _n(row["weighted_avg_score"], 3),
            _n(row["pct_score_0"], 2),
            _n(row["pct_population_score_0"], 2),
        ] for row in rows],
    )
