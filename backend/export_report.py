"""Write docs/analysis_report.md from the live database."""
from pathlib import Path

from app.db import SessionLocal
from app.services.analysis import build_report
from app.services.report_markdown import render_report_markdown

OUT = Path(__file__).resolve().parents[1] / "docs" / "analysis_report.md"


def main() -> None:
    db = SessionLocal()
    try:
        report = build_report(db)
        OUT.write_text(render_report_markdown(report), encoding="utf-8")
    finally:
        db.close()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
