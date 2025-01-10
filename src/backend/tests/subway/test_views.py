from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from subway.models import SubwayLine, SubwayStatus
from unittest.mock import patch
import datetime
import json
import logging

from exceptions import StatusUpdateError


class SubwayViewsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.ERROR)  # Disable logging for tests

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)  # Re-enable logging
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        self.line1 = SubwayLine.objects.create(
            name="A", status=SubwayStatus.NORMAL, created_at=timezone.now() - datetime.timedelta(days=1)
        )
        self.line2 = SubwayLine.objects.create(
            name="B",
            status=SubwayStatus.DELAYED,
            created_at=timezone.now() - datetime.timedelta(days=1),
            delay_start_time=timezone.now() - datetime.timedelta(hours=1),
        )

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_status_endpoint(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        url = reverse("subway-status")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0], {"line": "A", "status": "normal"})
        self.assertEqual(data[1], {"line": "B", "status": "delayed"})

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_status_not_found(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        # Test non-existent line
        response = self.client.get(reverse("subway-status") + "?line=Z")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "No matching subway lines found"})

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_status_service_error(self, mock_update):
        mock_update.side_effect = StatusUpdateError("MTA API Error")

        response = self.client.get(reverse("subway-status"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "MTA API Error"})

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_status_filter_by_status(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        response = self.client.get(reverse("subway-status") + "?status=normal")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["line"], "A")

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_uptime_endpoint(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        url = reverse("subway-uptime")  # Changed from subway:uptime
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        self.assertTrue(any(d["line"] == "A" for d in data))
        self.assertTrue(any(d["line"] == "B" for d in data))

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_uptime_not_found(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        response = self.client.get(reverse("subway-uptime") + "?line=Z")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "No matching subway lines found"})

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_uptime_service_error(self, mock_update):
        mock_update.side_effect = StatusUpdateError("MTA API Error")

        response = self.client.get(reverse("subway-uptime"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "MTA API Error"})

    @patch("subway.models.SubwayLine.update_statuses")
    def test_get_uptime_filter_by_line(self, mock_update):
        mock_update.return_value = {"A": self.line1, "B": self.line2}

        response = self.client.get(reverse("subway-uptime") + "?line=A")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["line"], "A")
