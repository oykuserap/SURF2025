"""
Meeting Summary Exporter
========================

Provides a class `MeetingSummaryExporter` to aggregate agenda summaries and (if
available) meeting dates, then export them to an Excel workbook.

Primary Output:
- Excel file with columns: Agenda Number, Meeting Date, Meeting Type, Organization,
  Source File, Summary (truncated or full), Original Length, Summary Length, Processed At

Usage Example:
--------------
from meeting_summary_exporter import MeetingSummaryExporter
exporter = MeetingSummaryExporter()
excel_path = exporter.export_excel()
print(f"Export created at: {excel_path}")

Optional Parameters:
- summaries_dir/json_data_dir: override default processed_data subfolders
- include_full_summary: when False (default), summary text is truncated to 1500 chars
- output_path: custom output filename

Dependencies: pandas, openpyxl
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import pandas as pd
from datetime import datetime

from config import OUTPUT_DIR
from utils import load_json, setup_logging

logger = setup_logging()

class MeetingSummaryExporter:
    """Aggregate meeting summaries + dates and export to Excel.

    It looks for:
      - processed_data/summaries/summary_*.json (produced by `SummaryGenerator`)
      - processed_data/json_data/data_*.json (structured extraction if available)
    """

    def __init__(
        self,
        summaries_dir: Optional[Path] = None,
        json_data_dir: Optional[Path] = None,
    ) -> None:
        self.summaries_dir = summaries_dir or (OUTPUT_DIR / "summaries")
        self.json_data_dir = json_data_dir or (OUTPUT_DIR / "json_data")
        self.output_dir = OUTPUT_DIR / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Preload meeting info map from structured json if exists
        self.meeting_info_map: Dict[int, Dict[str, Any]] = {}
        self._load_meeting_info()

    # ---------------------
    # Data Loading Helpers
    # ---------------------
    def _load_meeting_info(self) -> None:
        if not self.json_data_dir.exists():
            return
        for fp in self.json_data_dir.glob("data_*.json"):
            try:
                data = load_json(fp)
                if "error" in data:
                    continue
                agenda_number = data.get("agenda_number")
                extracted = data.get("extracted_data", {})
                meeting_info = extracted.get("meeting_info", {})
                if agenda_number is not None:
                    self.meeting_info_map[int(agenda_number)] = {
                        "meeting_date": meeting_info.get("date"),
                        "meeting_type": meeting_info.get("type"),
                        "organization": meeting_info.get("organization"),
                    }
            except Exception as e:
                logger.warning(f"Failed loading meeting info from {fp}: {e}")

    def _iter_summary_files(self):
        if not self.summaries_dir.exists():
            logger.warning("Summaries directory not found: %s", self.summaries_dir)
            return []
        return sorted(self.summaries_dir.glob("summary_*.json"))

    # ---------------------
    # Core Aggregation
    # ---------------------
    def collect_rows(self, include_full_summary: bool = False, summary_truncate: int = 1500) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for fp in self._iter_summary_files():
            try:
                data = load_json(fp)
            except Exception as e:
                logger.warning(f"Skipping {fp.name}: cannot read ({e})")
                continue
            if "error" in data:
                continue
            agenda_number = data.get("agenda_number")
            summary_text = data.get("summary", "") or ""
            if not include_full_summary and summary_truncate and len(summary_text) > summary_truncate:
                display_summary = summary_text[:summary_truncate] + "..."
            else:
                display_summary = summary_text
            meeting_meta = self.meeting_info_map.get(int(agenda_number)) if agenda_number is not None else {}
            rows.append({
                "agenda_number": agenda_number,
                "meeting_date": meeting_meta.get("meeting_date"),
                "meeting_type": meeting_meta.get("meeting_type"),
                "organization": meeting_meta.get("organization"),
                "source_file": data.get("source_file"),
                "summary": display_summary,
                "original_length": data.get("original_length"),
                "summary_length": data.get("summary_length"),
                "processed_at": data.get("processed_at"),
            })
        return rows

    # ---------------------
    # Export Methods
    # ---------------------
    def export_excel(
        self,
        output_path: Optional[Path] = None,
        include_full_summary: bool = False,
        summary_truncate: int = 1500,
    ) -> Path:
        rows = self.collect_rows(include_full_summary=include_full_summary, summary_truncate=summary_truncate)
        if not rows:
            raise RuntimeError("No summaries found to export")
        df = pd.DataFrame(rows)
        # Sort by meeting_date (if present) then agenda_number
        if "meeting_date" in df.columns:
            try:
                df["_date_sort"] = pd.to_datetime(df["meeting_date"], errors="coerce")
                df = df.sort_values(["_date_sort", "agenda_number"], ascending=[True, True])
                df = df.drop(columns=["_date_sort"])
            except Exception:
                pass
        # Determine output path
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"meeting_summaries_{ts}.xlsx"
        # Write Excel
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Summaries")
            # Simple metadata sheet
            meta_df = pd.DataFrame([
                {"key": "generated_at", "value": datetime.now().isoformat()},
                {"key": "total_rows", "value": len(df)},
                {"key": "full_summary", "value": include_full_summary},
            ])
            meta_df.to_excel(writer, index=False, sheet_name="Metadata")
        logger.info(f"Excel export written to {output_path}")
        return output_path

    def export_csv(
        self,
        output_path: Optional[Path] = None,
        include_full_summary: bool = False,
        summary_truncate: int = 1500,
    ) -> Path:
        rows = self.collect_rows(include_full_summary=include_full_summary, summary_truncate=summary_truncate)
        if not rows:
            raise RuntimeError("No summaries found to export")
        df = pd.DataFrame(rows)
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"meeting_summaries_{ts}.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"CSV export written to {output_path}")
        return output_path


def main():  # pragma: no cover simple CLI hook
    exporter = MeetingSummaryExporter()
    path = exporter.export_excel()
    print(f"Export created at: {path}")

if __name__ == "__main__":
    main()
