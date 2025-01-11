# Time Series Backend

This project is a backend solution for ingesting and querying time series data, built with **Django** and containerized using **Docker**.

It emphasizes performance and maintainability.

### Tech Stack
-   Backend: Django 5
-   Database: PostgreSQL + TimescaleDB
-   Caching: Redis
-   Containerization: Docker

### Kanban Board

Project tracking is available on the [Kanban Board](https://github.com/users/frozen0601/projects/4).

### Features
- ingest data through RESTful endpoint `POST api/session/`
- query aggregated data through RESTful endpoint `GET api/timeseries/`
- support advanced filter in query, including options to filter by
  -   `user_id`
  -   `session_id`
  -   `series` (supports regex and returning multiple data series)
  -   `interval` (e.g. `min`, `week`, `month`)
  -   `start_time`, `end_time`
  -   `agg_func` (`avg`, `max`, `min`, `count`)
- bucket data into chuncks of 1-week buckets (PostgreSQL Hypertables)
- API documentation is available via ReDoc at [http://localhost:8000/redoc/](http://localhost:8000/redoc/).

### Future Work
- implement continuous aggregates for faster queries
- set up data compression
- add percentile-based aggregates (e.g., median, p90, p99).

---

## Setup

1. **Clone the Repository and Navigate to the Folder**

    ```bash
    git https://github.com/frozen0601/time-series-backend.git
    cd time-series-backend
    ```
2. **Create `.env` at the root of the project with the following context**
    ```bash
    DJANGO_SETTINGS_MODULE=settings.base
    DEBUG=False
    DB_HOST=db
    DB_PORT=5432
    DB_NAME=postgres
    DB_PASSWORD=postgres
    DB_USERNAME=postgres
    ```

2. **(on First Run) Initialize the Project**
   
   Run the following command to build the Docker environment and run.

    ```bash
    make init
    ```

    `make init` is equivalent to:
    ```bash
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	docker compose exec django python manage.py migrate
	docker compose exec django python manage.py seed_metric_types
    ```

4. **Run**
    ```bash
    docker compose up -d
    ```

---
## Why PostgreSQL + TimescaleDB?

My previous experience with continuous status monitoring highlighted the challenges of managing growing time-series data and complex queries. While custom solutions like [data compression](https://github.com/frozen0601/mta-status-tracker/blob/d4367c827a332772e36534a9428138885a9a8f1b/src/backend/apps/subway/models.py#L33C9-L33C25) and metadata-driven retrieval helped, this project demands a more robust approach.

TimescaleDB, built on PostgreSQL, addresses these challenges directly:

*   **Automatic Preprocessing:** TimescaleDB can be set up to automatically preprocesses data into time-based chunks (e.g., daily, monthly). Instead of querying millions of raw records, queries can use pre-aggregated data from a few entries in higher-level chunks.
*   **Efficient Aggregation:** This dramatically improves query performance, especially for aggregations over large time ranges. (learn more: [video](https://youtu.be/c8_iHabi-nc?si=MP3BRNlinx4P-f_6&t=243))
*   **Relational Database Benefits:** Building on PostgreSQL provides the advantages of a mature relational database, including structured queries and robust scalability.

Choosing PostgreSQL + TimescaleDB has also influenced key decisions around data modeling and query implementation.


## Data Modeling

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
