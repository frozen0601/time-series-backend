from django.contrib import admin
from .models import MetricType, Session, TimeSeriesData

admin.site.register(MetricType)
admin.site.register(Session)
admin.site.register(TimeSeriesData)
