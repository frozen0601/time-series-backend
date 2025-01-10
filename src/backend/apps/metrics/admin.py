from django.contrib import admin
from .models import MetricType, TimeSeriesData

admin.site.register(MetricType)
admin.site.register(TimeSeriesData)
