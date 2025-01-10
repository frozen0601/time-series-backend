# time-series-backend


## Time-Series Data Storage Design

This section describes the design for storing time-series data, prioritizing simplicity and performance for initial requirements.

### Current Approach: `TextField` with Casting

The `TimeSeriesData.value` field is currently implemented as a `TextField`.

**Rationale:**

*   **Simplicity:** Simplifies model code and avoids JSON processing overhead.
*   **Performance:** Offers comparable or better performance than `JSONField` for single values, especially with TimescaleDB continuous aggregates (pre-calculate aggregations).
*   **Current Needs:** Aligns with the requirement for each series to have a consistent data type (float, int, rgb string).

**Implementation:**

*   `TimeSeriesData.value`: `models.TextField()`
*   Validation/Conversion: Handled in `TimeSeriesData.clean()` based on `MetricType.value_type`.
*   Querying: Values are cast at query time (e.g., `Avg(models.F('value').cast(FloatField()))`).

### Future Considerations: Transitioning to `JSONField`

If future requirements include:

*   Multiple values per data point
*   Nested data structures
*   Variable attributes per series
*   Metadata or contextual information
*   Arrays of values

We will transition to `JSONField`.

**Transition Strategy:**

1.  Change `TimeSeriesData.value` from `TextField()` to `JSONField()`.
2.  (Optional) Implement schema validation in `MetricType` and `TimeSeriesData.clean()`.

```python
import jsonschema
from django.db import models

class MetricType(models.Model):
    # ... other fields
    schema = models.JSONField(null=True, blank=True, help_text="JSON Schema for value validation (optional)")

class TimeSeriesData(models.Model):
    # ... other fields
    value = models.JSONField()

    def clean(self):
        if self.series.schema:
            jsonschema.validate(instance=self.value, schema=self.series.schema)
```

### Alternatives Considered: Concrete Table Inheritance

Rejected due to increased complexity and query inefficiency outweighing potential storage benefits.
