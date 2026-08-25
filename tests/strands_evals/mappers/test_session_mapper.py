"""Tests for the SessionMapper base class."""

from datetime import datetime, timedelta, timezone

from strands_evals.mappers.session_mapper import SessionMapper
from strands_evals.types.trace import Session


class _ConcreteMapper(SessionMapper):
    """Minimal concrete subclass for testing base-class methods."""

    def map_to_session(self, spans: list) -> Session:
        raise NotImplementedError


class TestParseTimestamp:
    """Tests for parse_timestamp handling various formats and ensuring UTC output."""

    def setup_method(self):
        self.mapper = _ConcreteMapper()

    def test_none_returns_aware_utc(self):
        result = self.mapper.parse_timestamp(None)
        assert result.tzinfo is not None

    def test_iso_string_with_z(self):
        result = self.mapper.parse_timestamp("2026-07-22T16:34:19.917561Z")
        assert result.tzinfo == timezone.utc
        assert result.year == 2026 and result.month == 7

    def test_nanosecond_epoch_int(self):
        """Nanosecond epoch integer is converted to aware UTC datetime."""
        result = self.mapper.parse_timestamp(1700000000000000000)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023

    def test_string_nanosecond_epoch(self):
        """String-encoded nanosecond epoch (OTLP JSON uint64) is correctly parsed."""
        result = self.mapper.parse_timestamp("1700000000000000000")
        assert result.tzinfo == timezone.utc
        assert result.year == 2023 and result.month == 11

    def test_aware_datetime_passthrough(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert self.mapper.parse_timestamp(dt) == dt

    def test_naive_datetime_gets_utc(self):
        """A naive datetime is assumed UTC and returned aware."""
        naive = datetime(2024, 6, 15, 12, 0, 0)
        result = self.mapper.parse_timestamp(naive)
        assert result.tzinfo is not None
        assert result == datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_non_utc_datetime_normalized(self):
        """An aware datetime in a non-UTC tz is converted to UTC."""
        plus5 = timezone(timedelta(hours=5))
        dt = datetime(2024, 6, 15, 17, 0, 0, tzinfo=plus5)
        result = self.mapper.parse_timestamp(dt)
        assert result.tzinfo == timezone.utc
        assert result == datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_iso_string_without_offset_gets_utc(self):
        """An ISO string with no offset is assumed UTC."""
        result = self.mapper.parse_timestamp("2024-01-01T00:00:00")
        assert result.tzinfo is not None
        assert result == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_iso_string_with_offset_normalized(self):
        """An ISO string with a non-UTC offset is converted to UTC."""
        result = self.mapper.parse_timestamp("2024-06-15T17:00:00+05:00")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_invalid_string_returns_aware_utc(self):
        """An unparseable string falls back to current UTC time."""
        result = self.mapper.parse_timestamp("not-a-timestamp")
        assert result.tzinfo is not None
