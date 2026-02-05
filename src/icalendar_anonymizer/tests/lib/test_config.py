# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for _config module."""

import pytest

from icalendar_anonymizer._config import (
    CONFIGURABLE_FIELDS,
    AnonymizeMode,
    validate_field_modes,
)


class TestAnonymizeMode:
    """Tests for AnonymizeMode enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert AnonymizeMode.KEEP.value == "keep"
        assert AnonymizeMode.REMOVE.value == "remove"
        assert AnonymizeMode.RANDOMIZE.value == "randomize"
        assert AnonymizeMode.REPLACE.value == "replace"

    def test_str_conversion(self):
        """Test enum value access."""
        assert AnonymizeMode.KEEP.value == "keep"
        assert AnonymizeMode.RANDOMIZE.value == "randomize"


class TestConfigurableFields:
    """Tests for CONFIGURABLE_FIELDS constant."""

    def test_contains_expected_fields(self):
        """Test that all expected fields are present."""
        # Define minimum required fields (allows future additions)
        minimum_expected = {
            "SUMMARY",
            "DESCRIPTION",
            "LOCATION",
            "COMMENT",
            "CONTACT",
            "RESOURCES",
            "CATEGORIES",
            "ATTENDEE",
            "ORGANIZER",
            "UID",
        }
        # Verify all minimum fields are present
        assert minimum_expected.issubset(CONFIGURABLE_FIELDS)
        # Verify no unexpected fields snuck in
        assert CONFIGURABLE_FIELDS.issubset(minimum_expected | set())


class TestValidateFieldModes:
    """Tests for validate_field_modes function."""

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert validate_field_modes(None) is None

    def test_empty_dict_returns_none(self):
        """Test that empty dict returns None."""
        assert validate_field_modes({}) is None

    def test_valid_config(self):
        """Test valid configuration is normalized correctly."""
        result = validate_field_modes({"summary": "keep", "location": "remove"})
        assert result == {"SUMMARY": AnonymizeMode.KEEP, "LOCATION": AnonymizeMode.REMOVE}

    def test_case_insensitive_field(self):
        """Test field names are case-insensitive."""
        result = validate_field_modes({"Summary": "keep", "LOCATION": "remove"})
        assert "SUMMARY" in result
        assert "LOCATION" in result

    def test_case_insensitive_mode(self):
        """Test mode values are case-insensitive."""
        result = validate_field_modes({"summary": "KEEP", "location": "Remove"})
        assert result == {"SUMMARY": AnonymizeMode.KEEP, "LOCATION": AnonymizeMode.REMOVE}

    def test_invalid_field_raises(self):
        """Test that invalid field name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown field"):
            validate_field_modes({"invalid_field": "keep"})

    def test_invalid_mode_raises(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            validate_field_modes({"summary": "invalid_mode"})

    def test_uid_remove_raises(self):
        """Test that UID cannot be set to remove mode."""
        with pytest.raises(ValueError, match="UID cannot be removed"):
            validate_field_modes({"uid": "remove"})

    def test_type_error_for_non_dict(self):
        """Test that non-dict input raises TypeError."""
        with pytest.raises(TypeError, match="must be dict or None"):
            validate_field_modes("not a dict")

    def test_all_modes_valid(self):
        """Test all valid modes work."""
        result = validate_field_modes(
            {
                "summary": "keep",
                "description": "remove",
                "location": "randomize",
                "comment": "replace",
            }
        )
        assert result["SUMMARY"] == AnonymizeMode.KEEP
        assert result["DESCRIPTION"] == AnonymizeMode.REMOVE
        assert result["LOCATION"] == AnonymizeMode.RANDOMIZE
        assert result["COMMENT"] == AnonymizeMode.REPLACE

    def test_all_fields_valid(self):
        """Test all configurable fields are accepted."""
        config = {field.lower(): "keep" for field in CONFIGURABLE_FIELDS}
        result = validate_field_modes(config)
        assert len(result) == len(CONFIGURABLE_FIELDS)
        for field in CONFIGURABLE_FIELDS:
            assert result[field] == AnonymizeMode.KEEP
