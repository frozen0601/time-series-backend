from abc import ABC, abstractmethod
from typing import List, Dict
import requests

# from subway.proto import gtfs_realtime_pb2
# from subway.proto import mercury_gtfs_realtime_pb2
from subway.models import SubwayStatus
from exceptions import StatusUpdateError


class SubwayStatusProvider(ABC):
    @abstractmethod
    def get_subway_line_names(self) -> List[str]:
        """Returns a list of subway line names"""
        pass

    @abstractmethod
    def get_latest_line_status(self) -> Dict[str, SubwayStatus]:
        """Returns a dictionary mapping subway line IDs to their SubwayStatus value"""
        pass


# class GTFSSubwayStatusProvider(SubwayStatusProvider):
#     def __init__(self):
#         self.urls = [
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
#             "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
#         ]

#     def get_latest_line_status(self) -> Dict[str, SubwayStatus]:
#         status_dict = {}

#         for url in self.urls:
#             response = requests.get(url)
#             if response.status_code == 200:
#                 feed = gtfs_realtime_pb2.FeedMessage()
#                 feed.ParseFromString(response.content)

#                 for entity in feed.entity:
#                     if entity.HasField("alert"):
#                         alert = entity.alert
#                         if alert.HasExtension(mercury_gtfs_realtime_pb2.mercury_alert):
#                             mercury = alert.Extensions[mercury_gtfs_realtime_pb2.mercury_alert]
#                             if mercury.HasField("alert_type") and mercury.alert_type == "Delays":
#                                 status_dict[entity.trip_update.trip.route_id] = SubwayStatus.DELAYED

#         return status_dict


class APISubwayStatusProvider(SubwayStatusProvider):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.url = "https://collector-otp-prod.camsys-apps.com/realtime/serviceStatus"
            cls._instance.headers = {"User-Agent": "Python/3.x MTA-Client/1.0"}
        return cls._instance

    def get_subway_line_names(self) -> List[str]:
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            line_names = set()
            for route in data.get("routeDetails", []):
                if route.get("mode") == "subway" and route.get("route"):
                    line_names.add(route.get("route"))

            return list(line_names)

        except Exception:
            return [
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "6X",
                "7",
                "7X",
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "FX",
                "G",
                "J",
                "L",
                "M",
                "N",
                "Q",
                "S",
                "SIR",
                "W",
                "Z",
            ]

    def get_latest_line_status(self) -> Dict[str, SubwayStatus]:
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            status_dict = {}

            for route in data.get("routeDetails", []):
                if route.get("mode") != "subway":
                    continue

                route_id = route.get("route")
                status = (
                    SubwayStatus.DELAYED
                    if any(detail.get("statusSummary") == "Delays" for detail in route.get("statusDetails", []))
                    else SubwayStatus.NORMAL
                )
                status_dict[route_id] = status

            return status_dict

        except Exception as e:
            raise StatusUpdateError(f"Failed to fetch subway status: {e}")


def get_subway_status_provider(provider_type: str = "api") -> SubwayStatusProvider:
    providers = {"api": APISubwayStatusProvider}
    return providers[provider_type]()


mta_client = APISubwayStatusProvider()
