from unittest import TestCase
from unittest.mock import patch, MagicMock
from subway.mta_data_fetcher import mta_client
from subway.models import SubwayStatus
import requests
from exceptions import StatusUpdateError


class MTADataClientTestCase(TestCase):
    def setUp(self):
        self.client = mta_client

    @patch("requests.get")
    def test_get_latest_line_status_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routeDetails": [
                {"mode": "subway", "route": "1", "statusDetails": [{"statusSummary": "Delays"}]},
                {"mode": "subway", "route": "2", "statusDetails": [{"statusSummary": "Good Service"}]},
            ]
        }
        mock_get.return_value = mock_response

        result = self.client.get_latest_line_status()

        self.assertEqual(
            result,
            {
                "1": SubwayStatus.DELAYED,
                "2": SubwayStatus.NORMAL,
            },
        )

    @patch("requests.get")
    def test_get_latest_line_status_failure(self, mock_get):
        # HTTP error
        mock_get.side_effect = requests.HTTPError("404 Client Error")
        with self.assertRaises(StatusUpdateError) as context:
            mta_client.get_latest_line_status()
        self.assertIn("Failed to fetch subway status", str(context.exception))

        # Connection error
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        with self.assertRaises(StatusUpdateError) as context:
            mta_client.get_latest_line_status()
        self.assertIn("Failed to fetch subway status", str(context.exception))

        # Invalid JSON
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b"invalid json"
        mock_get.return_value = mock_response
        with self.assertRaises(StatusUpdateError) as context:
            mta_client.get_latest_line_status()
        self.assertIn("Failed to fetch subway status", str(context.exception))
