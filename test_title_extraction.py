"""
Unit tests for PDF title extraction.

Tests various PDF formats to ensure titles are extracted correctly.
"""

import pytest
from scripts.convert_reports import extract_title, clean_title


class TestExtractTitle:
    """Test cases for extract_title function."""

    def test_single_line_title(self):
        """Test extraction of single-line title before Status."""
        text = """Core node restarts on LEAP
Status: Draft
Overview"""
        assert extract_title(text) == "Core node restarts on LEAP"

    def test_multiline_title(self):
        """Test extraction of multi-line title before Status."""
        text = """Starting Server of users with 2i2c admin emails from admin panel fails
on earthscope
Status: Draft
Overview"""
        expected = "Starting Server of users with 2i2c admin emails from admin panel fails on earthscope"
        assert extract_title(text) == expected

    def test_pagerduty_header_with_url(self):
        """Test extraction when PagerDuty export header with URL is present."""
        text = """Postmortem Report - [dubois:ephemeral] Unable to start servers - PagerDuty https://2i2c-org.pagerduty.com/postmortems/18938471-9999-036b-7a41-0a8da5b8257a/export
[dubois:ephemeral] Unable to start servers
Status: Closed
Overview"""
        assert extract_title(text) == "[dubois:ephemeral] Unable to start servers"

    def test_no_status_field(self):
        """Test fallback when Status field is missing."""
        text = """Custom Incident Report
This is a custom document without status field
Overview"""
        # Should return first non-empty line as fallback
        assert extract_title(text) == "Custom Incident Report"

    def test_empty_lines_before_status(self):
        """Test handling of empty lines before Status."""
        text = """My Incident Title


Status: Draft"""
        assert extract_title(text) == "My Incident Title"

    def test_whitespace_handling(self):
        """Test that extra whitespace is cleaned up."""
        text = """  Title with extra    spaces
Status: Draft"""
        assert extract_title(text) == "Title with extra spaces"

    def test_title_with_date_prefix_stripped(self):
        """Test that 'Incident report [date] -' prefix is stripped."""
        text = """Incident report July 21 2025 - Openscapes hub pods dying
Status: Draft"""
        assert extract_title(text) == "Openscapes hub pods dying"

    def test_no_status_field_fallback(self):
        """Test fallback when Status field is missing (earthscope-deeper-dive case)."""
        text = """EarthScope Investigation
Overview
This is an addendum"""
        assert extract_title(text) == "EarthScope Investigation"


class TestCleanTitle:
    """Test cases for clean_title function."""

    def test_strip_incident_report_prefix(self):
        """Test stripping 'Incident report [date] -' prefix."""
        assert clean_title("Incident report August 12 2025 - LEAP hub outage") == "LEAP hub outage"
        assert clean_title("Incident report July 21 2025 - Openscapes hub pods dying") == "Openscapes hub pods dying"

    def test_strip_postmortem_prefix(self):
        """Test stripping 'Postmortem Report -' prefix."""
        assert clean_title("Postmortem Report - Core node restarts") == "Core node restarts"

    def test_no_prefix_unchanged(self):
        """Test that titles without prefixes remain unchanged."""
        assert clean_title("Core node restarts on LEAP") == "Core node restarts on LEAP"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
