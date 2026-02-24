"""
Unit tests for PDF title extraction.

Tests various PDF formats to ensure titles are extracted correctly.
"""

import pytest
from pathlib import Path
from scripts.convert_reports import (
    extract_title,
    clean_title,
    extract_text_from_pdf,
    clean_pdf_text,
    extract_impact_time,
    extract_duration,
)


class TestExtractTitle:
    """Test cases for extract_title function."""

    def test_single_line_title(self):
        text = """Core node restarts on LEAP
Status: Draft
Overview"""
        assert extract_title(text) == "Core node restarts on LEAP"

    def test_multiline_title(self):
        text = """Starting Server of users with 2i2c admin emails from admin panel fails
on earthscope
Status: Draft
Overview"""
        expected = "Starting Server of users with 2i2c admin emails from admin panel fails on earthscope"
        assert extract_title(text) == expected

    def test_pagerduty_header_with_url(self):
        text = """Postmortem Report - [dubois:ephemeral] Unable to start servers - PagerDuty https://2i2c-org.pagerduty.com/postmortems/18938471-9999-036b-7a41-0a8da5b8257a/export
[dubois:ephemeral] Unable to start servers
Status: Closed
Overview"""
        assert extract_title(text) == "[dubois:ephemeral] Unable to start servers"

    def test_no_status_field(self):
        text = """Custom Incident Report
This is a custom document without status field
Overview"""
        # Should return first non-empty line as fallback
        assert extract_title(text) == "Custom Incident Report"

    def test_empty_lines_before_status(self):
        text = """My Incident Title


Status: Draft"""
        assert extract_title(text) == "My Incident Title"

    def test_whitespace_handling(self):
        text = """  Title with extra    spaces
Status: Draft"""
        assert extract_title(text) == "Title with extra spaces"

    def test_title_with_date_prefix_stripped(self):
        text = """Incident report July 21 2025 - Openscapes hub pods dying
Status: Draft"""
        assert extract_title(text) == "Openscapes hub pods dying"

    def test_no_status_field_fallback(self):
        text = """EarthScope Investigation
Overview
This is an addendum"""
        assert extract_title(text) == "EarthScope Investigation"

    def test_docling_heading_prefix_stripped(self):
        """Docling outputs titles with ## prefix; clean_title removes it."""
        # After clean_pdf_text strips ## markers, title is plain text.
        # But if ## survives (e.g. via fallback path), clean_title removes it.
        assert clean_title("## EarthScope Investigation") == "EarthScope Investigation"


class TestCleanTitle:
    """Test cases for clean_title function."""

    def test_strip_incident_report_prefix(self):
        assert (
            clean_title("Incident report August 12 2025 - LEAP hub outage")
            == "LEAP hub outage"
        )
        assert (
            clean_title("Incident report July 21 2025 - Openscapes hub pods dying")
            == "Openscapes hub pods dying"
        )

    def test_strip_postmortem_prefix(self):
        assert (
            clean_title("Postmortem Report - Core node restarts")
            == "Core node restarts"
        )

    def test_no_prefix_unchanged(self):
        assert clean_title("Core node restarts on LEAP") == "Core node restarts on LEAP"


class TestCleanPdfText:
    """Test cases for clean_pdf_text."""

    def test_url_spaces_fixed(self):
        text = "See https:// github.com/2i2c-org/infrastructure/pull/123 for details"
        cleaned = clean_pdf_text(text)
        assert "https://github.com/" in cleaned
        assert "https:// " not in cleaned

    def test_heading_markers_stripped(self):
        text = "## Overview\n\nSome content\n\n### Sub-section\n\nMore content"
        cleaned = clean_pdf_text(text)
        assert "## " not in cleaned
        assert "Overview" in cleaned
        assert "Sub-section" in cleaned

    def test_timezone_footer_removed(self):
        text = "Some content\n*All times listed in Pacific Time (US & Canada).\nMore"
        cleaned = clean_pdf_text(text)
        assert "*All times listed" not in cleaned

    def test_impact_time_section_removed(self):
        text = "Action Items\n- Fix it\n\nIMPACT TIME\nFeb 11 at 08:46 to Feb 11 at 22:44\n\nDURATION\n13h 58m\n"
        cleaned = clean_pdf_text(text)
        assert "IMPACT TIME" not in cleaned
        assert "DURATION" not in cleaned
        assert "Fix it" in cleaned


class TestMetadataExtraction:
    """Test impact time and duration extraction from docling-style output."""

    def test_impact_time_from_docling_section(self):
        text = "IMPACT TIME\nFeb 11 at 08:46 to Feb 11 at 22:44\n"
        assert extract_impact_time(text) == "Feb 11 at 08:46 to Feb 11 at 22:44"

    def test_impact_time_truncated_header(self):
        # Some PDFs truncate the column header to "IMPACT TIM"
        text = "IMPACT TIM\nAug 29 at 09:00 to Aug 29 at 11:00\n"
        assert extract_impact_time(text) == "Aug 29 at 09:00 to Aug 29 at 11:00"

    def test_impact_time_fallback_inline(self):
        text = "The incident lasted from Sep 6 at 05:25 to Sep 6 at 10:48 total."
        assert extract_impact_time(text) == "Sep 6 at 05:25 to Sep 6 at 10:48"

    def test_duration_from_docling_section(self):
        text = "DURATION\n13h 58m\n"
        assert extract_duration(text) == "13h 58m"

    def test_duration_multipart(self):
        text = "DURATION\n4d 1h 30m\n"
        assert extract_duration(text) == "4d 1h 30m"

    def test_duration_with_seconds(self):
        text = "DURATION\n2h 13m 22s\n"
        assert extract_duration(text) == "2h 13m 22s"


class TestPDFExtraction:
    """Integration tests for PDF extraction using docling."""

    def test_metadata_extracted_before_cleaning(self):
        """Docling includes right-column metadata; we extract it before cleaning."""
        pdf_path = Path("reports/2026-02-11-dubois-user-image-issue.pdf")
        text_raw = extract_text_from_pdf(pdf_path)

        # Raw text should contain the metadata sections
        assert "IMPACT TIME" in text_raw or "DURATION" in text_raw

        # We can extract metadata from raw text
        impact_time = extract_impact_time(text_raw)
        duration = extract_duration(text_raw)
        assert impact_time != "Unknown", f"Expected impact time, got Unknown"
        assert duration != "Unknown", f"Expected duration, got Unknown"

        # After cleaning, metadata sections are removed
        cleaned = clean_pdf_text(text_raw)
        assert "OWNER OF REVIEW PROCESS" not in cleaned
        assert "Unable to start servers" in cleaned

    def test_main_content_present(self):
        """Key content sections survive extraction and cleaning."""
        pdf_path = Path("reports/2026-02-11-dubois-user-image-issue.pdf")
        text_raw = extract_text_from_pdf(pdf_path)
        cleaned = clean_pdf_text(text_raw)

        assert "Unable to start servers" in cleaned
        assert "Overview" in cleaned
        assert "Resolution" in cleaned


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
