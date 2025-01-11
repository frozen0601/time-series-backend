from django.db.models import Func, FloatField


class PercentileCont(Func):
    """Calculate the percentile of a field using the PERCENTILE_CONT SQL function."""

    function = "PERCENTILE_CONT"
    template = "%(function)s(%(percentile)s) WITHIN GROUP (ORDER BY %(expressions)s)"
    output_field = FloatField()

    def __init__(self, expression, percentile):
        super().__init__(expression, percentile=percentile)
