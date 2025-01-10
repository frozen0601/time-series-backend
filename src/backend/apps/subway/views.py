from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from exceptions import StatusUpdateError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer

from .models import SubwayLine
from .mta_data_fetcher import mta_client


import logging

logger = logging.getLogger(__name__)


@extend_schema(
    description="Get subway line statuses",
    parameters=[
        OpenApiParameter(name="line", description="Comma-separated line names", type=str),
        OpenApiParameter(name="status", description="Filter by status (normal, delayed)", type=str),
    ],
    responses={
        200: inline_serializer(
            name="UptimeResponse",
            fields={"line": serializers.CharField(), "status": serializers.CharField()},
            many=False,
        ),
        404: dict,
        503: dict,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value=[{"line": "1", "status": "normal"}, {"line": "2", "status": "delayed"}],
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Not Found Error",
            value={"error": "No matching subway lines found"},
            response_only=True,
            status_codes=["404"],
        ),
        OpenApiExample(
            "Service Unavailable Error",
            value={"error": "Failed to update statuses: Connection error"},
            response_only=True,
            status_codes=["503"],
        ),
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_status(request):
    """Fetch the status of subway lines with optional filters for line and status."""
    line_names = request.GET.get("line", "").split(",")
    line_statuses = request.GET.get("status", "").split(",")

    # Response with MTA data if available
    try:
        latest_statuses = mta_client.get_latest_line_status()

        response_data = []
        for line_name, subway_status in latest_statuses.items():
            if (not line_names or line_names == [""] or line_name in line_names) and (
                not line_statuses or line_statuses == [""] or subway_status.value in line_statuses
            ):
                response_data.append({"line": line_name, "status": subway_status.value})

        if not response_data:
            logger.error(
                f"[mta source] No matching subway lines found for line={line_names} and status={line_statuses}"
            )
            return Response({"error": "No matching subway lines found"}, status=status.HTTP_404_NOT_FOUND)

        response_data.sort(key=lambda x: x["line"])
        return Response(response_data, status=status.HTTP_200_OK)

    # otherwise fallback to database
    except Exception as e:
        logging.error(f"Failed to fetch statuses from MTA: {e}")
        return fallback_to_database(line_names, line_statuses)


def fallback_to_database(line_names, line_statuses):
    """Fallback method to fetch from database."""
    try:
        lines = SubwayLine.objects.all()
        if line_names and line_names != [""]:
            name_filter = Q()
            for name in line_names:
                name_filter |= Q(name__iexact=name.strip())
            lines = lines.filter(name_filter)

        if line_statuses and line_statuses != [""]:
            status_filter = Q()
            for line_status in line_statuses:
                status_filter |= Q(status__iexact=line_status.strip())
            lines = lines.filter(status_filter)

        if not lines.exists():
            logger.error(
                f"[database source] No matching subway lines found for line={line_names} and status={line_statuses}"
            )
            return Response({"error": "No matching subway lines found"}, status=status.HTTP_404_NOT_FOUND)

        lines = lines.order_by("name")
        response_data = [line.to_dict() for line in lines]
        return Response(response_data, status=status.HTTP_200_OK)

    except StatusUpdateError as e:
        logger.error(f"Failed to update statuses: {e}")
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Unexpected error during status fetch: {e}")
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    description="Get subway line uptime metrics",
    parameters=[OpenApiParameter(name="line", description="Comma-separated line names", type=str)],
    responses={
        200: inline_serializer(
            name="UptimeResponse",
            fields={"line": serializers.CharField(), "uptime": serializers.FloatField(allow_null=True)},
            many=False,
        ),
        404: dict,
        503: dict,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value=[
                {"line": "1", "uptime": 1.0},
                {"line": "2", "uptime": 0.074},
                {"line": "3", "uptime": 0.002},
                {"line": "A", "uptime": 0.769},
                {"line": "B", "uptime": 0.405},
            ],
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Not Found Error",
            value={"error": "No matching subway lines found"},
            response_only=True,
            status_codes=["404"],
        ),
        OpenApiExample(
            "Service Unavailable Error",
            value={"error": "Failed to update statuses: Connection error"},
            response_only=True,
            status_codes=["503"],
        ),
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_uptime(request):
    """Get uptime for all lines or filtered by line name."""
    line_names = request.GET.get("line", "").split(",")

    try:
        # Get lines and apply filter
        lines = SubwayLine.objects.all()
        if line_names and line_names != [""]:
            lines = lines.filter(name__iexact__in=[name.strip() for name in line_names])

        if not lines.exists():
            return Response({"error": "No matching subway lines found"}, status=status.HTTP_404_NOT_FOUND)

        lines = lines.order_by("name")
        return Response(
            [
                {
                    "line": line.name,
                    "uptime": round(line.uptime_ratio, 3) if line.uptime_ratio != -1.0 else None,
                }
                for line in lines
            ]
        )

    except StatusUpdateError as e:
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
