"""
Data Ingestion app tests
"""

from django.test import TestCase
from .models import ImportLog


class ImportLogModelTest(TestCase):
    """Tests for ImportLog model"""

    def test_import_log_creation(self):
        """Test ImportLog creation"""
        log = ImportLog.objects.create(
            source="test_source",
            status="running",
            records_processed=100,
        )
        assert log.source == "test_source"
        assert log.status == "running"
        assert log.records_processed == 100

    def test_import_log_str(self):
        """Test ImportLog string representation"""
        log = ImportLog.objects.create(source="usuarios.csv", status="success")
        assert "usuarios.csv" in str(log)
        assert "success" in str(log)
