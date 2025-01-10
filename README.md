
## Project Data Modeling

This document outlines the data modeling approach for the time-series backend, focusing on simplicity, performance, and alignment with initial requirements. It also considers extensibility for future needs.

### 1. Series Name Representation

How should we represent our metric series names (e.g., `session.gut_health_score`)? I weigh the pros and cons of two options.

#### 1.1 Flat Representation (Current Approach)

The current implementation uses a single `series` field (`CharField`) in `MetricType`.

- **Advantages**:
  - Simplicity: Keeps models and queries straightforward.
  - Regex Filtering: Directly supports regex filtering using `series__regex`.
  - Matches Current Needs: Works well for querying by specific series.

- **Implementation**:
  ```python
  MetricType.series = models.CharField(max_length=255, unique=True)
  ```

- **Example Query**:
  ```python
  TimeSeriesData.objects.filter(series__regex=r"^session\.urine\..*")
  ```

#### 1.2 Hierarchical Representation (Alternative Considered)

Uses a self-referential `parent` relationship in `MetricType` to split series names into hierarchical fields.

- **Pros**:
  - **Flexible Queries**: Easily filter or group by hierarchy levels.
  - **Clearer Validation**: Provides a structured framework for managing series names.

- **Cons**:
  - **Complexity**: Adds recursive lookups and join-heavy queries.
  - **Performance**: Slower for large datasets or deep hierarchies.
  - **Overkill**: Current needs are met with simpler regex filtering in the flat model.
    
---

### 2. Metric Value Storage

This section evaluates three approaches for storing metric values, based on their simplicity, performance, and future extensibility.

#### 2.1 `TextField` with Casting (Current Approach)

The `TimeSeriesData.value` field is implemented as a `TextField`, with type validation and conversion based on `MetricType.value_type`.

- **Advantages**:
  - Simplicity: Straightforward implementation for single, consistent value types per series.
  - Performance: Efficient enough since we got TimescaleDB's continuous aggregates and pre-calculated queries.

- **Implementation**:
  ```python
  value = models.TextField()
  ```

- **Validation**:
  Conversion and validation are handled during data ingestion based on the series' `value_type`.

- **Querying Example**:
  ```python
  Avg(models.F('value').cast(FloatField()))
  ```

#### 2.2 JSONField (Future-Proof Alternative)

Transitioning to `JSONField` would support nested or complex data structures.

- **Advantages**:
  - Flexibility: Supports multiple values, nested data, or metadata.
  - Future-Proof: Accommodates evolving data requirements.

- **Disadvantages**:
  - Performance Overhead: Adds complexity for single-value metrics.

- **Implementation Example**:
  ```python
    import jsonschema
    
    class MetricType(models.Model):
        # other fields
        schema = models.JSONField(null=True, blank=True)
    
    class TimeSeriesData(models.Model):
        # other fields
        value = models.JSONField()
    
        def clean(self):
            if self.series.schema:
                jsonschema.validate(instance=self.value, schema=self.series.schema)
  ```

#### 2.3 Concrete Table Inheritance (Rejected)

Using separate tables for each metric type could improve storage efficiency but this increase complexity (require extra join) and queries become more complex and less efficient.
The benefit of slightly reduced storage space for some data types is usually outweighed by the increased query complexity and performance overhead.
