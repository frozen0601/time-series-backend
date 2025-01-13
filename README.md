# Time Series Backend

This project is a backend solution for ingesting and querying time series data, built with **Django** and containerized using **Docker**.

It emphasizes performance and maintainability.

### Table of Contents
- [Setup](#setup)
- [APIs](#apis)
- [Stress Test](#stress-test)
- [Why PostgreSQL + TimescaleDB?](#why-postgresql--timescaledb)
- [Data Modeling](#data-modeling)
- [Future Work and Scale](#future-work-and-scale)

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
- support advanced filter in query
- bucket data into chuncks of 1-week buckets (PostgreSQL Hypertables)
- API documentation is available via ReDoc at [http://localhost:8000/redoc/](http://localhost:8000/redoc/).

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

## APIs

### 1. Ingest Data
`POST /api/sessions/`

**Description**: Allows you to ingest metric data into the system.

#### Example Request Body
```json
{
    "user_id": "uuid4",
    "session_id": "uuid4",
    "start_ts": "2025-01-01T00:00:00Z",
    "data": [
        {
            "series": "session.example.series",
            "time": "2025-01-01T00:01:00Z",
            "value": {
                "value": "example value"
            }
        },
        {
            "series": "session.urine.color",
            "time": "2025-01-01T00:01:00Z",
            "value": {
	        "r": 255
	        "g": 255
	        "b": 255
            }
        },
        {}, {}, {}
    ]
}
```
### 2. Query Data
`GET /api/metrictypes/?`

**Description**: Queries time series data based on various parameters.
| Parameter    | Type   | Location   | Description                                                                                  | Required | Default |
|--------------|--------|------------|----------------------------------------------------------------------------------------------|----------|---------|
| `user_id`    | `str`  | Query      | User ID                                                                                     | Yes      | -       |
| `session_id` | `str`  | Query      | Session ID                                                                                  | No       | -       |
| `series`     | `str`  | Query      | Series name. Supports regex and multiple values (comma-separated).                          | No       | -       |
| `interval`   | `str`  | Query      | Aggregation interval (`min`, `week`, `month`).                                              | No       | `week`  |
| `start_time` | `str`  | Query      | Start time for filtering.                                                                   | No       | 7 days  |
| `end_time`   | `str`  | Query      | End time for filtering.                                                                     | No       | now     |
| `agg_func`   | `str`  | Query      | Aggregation function (`avg`, `min`, `max`, `count`).                                        | No       | `avg`   |

### 3. Retrieve Available Metric Types
`GET /api/metrictypes/`

**Description**: Retrieves all the available metric types (series).
 
---

## Stress Test

A stress test with 250,000 data points (25,000 sessions, 10 points/session) showed:

```
Created 250000 total data points
Testing query performance...
[Query 1] Found 6735 buckets in 0.241s (day-level, avg).
[Query 2] Found 963 buckets in 0.183s (week-level, avg).
[Query 3] Found 222 buckets in 0.198s (month-level, avg).
[Query 4] Found 222 buckets in 0.298s (month-level, avg, 'session.urine.*').
Testing API endpoint performance...
[API Test 1] (Month-level, single series, avg):
  - Response time: 0.057s
  - Status code: 200
  - Results count: 23

[API Test 2] (Month-level, regex, multiple series, avg):
  - Response time: 0.141s
  - Status code: 200
  - Results count: 69

Test data rolled back successfully.
```

**Query Performance**: Day-level aggregations took 0.241s, week-level 0.183s, and month-level 0.198s. Week/month queries benefited from the 1-week chunk interval. Regex filtering added minor overhead (0.298s).

**API Performance**: Month-level API calls were fast: single series (0.057s), multiple series with regex (0.141s).

**Conclusion**: The system handles the tested data volume well, demonstrating robust performance across various aggregation levels. Further testing with larger datasets, concurrency, and query plan analysis is recommended. As data grows, setting up continuous aggregations for appropriate time intervals (e.g., month-level) could further optimize query performance and reduce computational overhead for frequently queried periods.

---

## Why PostgreSQL + TimescaleDB?

My previous experience with continuous status monitoring highlighted the challenges of managing growing time-series data and complex queries. While custom solutions like [data compression](https://github.com/frozen0601/mta-status-tracker/blob/d4367c827a332772e36534a9428138885a9a8f1b/src/backend/apps/subway/models.py#L33C9-L33C25) and metadata-driven retrieval helped, this project demands a more robust approach.

TimescaleDB, built on PostgreSQL, addresses these challenges directly:

*   **Automatic Preprocessing:** TimescaleDB can be set up to automatically preprocesses data into time-based chunks (e.g., daily, monthly). Instead of querying millions of raw records, queries can use pre-aggregated data from a few entries in higher-level chunks.
*   **Efficient Aggregation:** This dramatically improves query performance, especially for aggregations over large time ranges. (learn more: [video](https://youtu.be/c8_iHabi-nc?si=MP3BRNlinx4P-f_6&t=243))
*   **Relational Database Benefits:** Building on PostgreSQL provides the advantages of a mature relational database, including structured queries and robust scalability.

Choosing PostgreSQL + TimescaleDB has also influenced key decisions around data modeling and query implementation.

---

## Data Modeling

This document outlines the data modeling approach for the time-series backend, focusing on simplicity, performance, and alignment with initial requirements. It also considers extensibility for future needs.

### Models

*   **MetricType:**
    *   `series` (CharField, unique): Metric series name.
    *   `schema` (JSONField): JSON schema for data validation.
    *   Index: `series`

*   **Session:**
    *   `user_id` (UUIDField, indexed): User ID.
    *   `session_id` (UUIDField, primary key): Session ID.
    *   `start_ts` (DateTimeField): Session start time.

*   **TimeSeriesData (TimescaleDB Hypertable):**
    *   `session` (ForeignKey(Session)): Related session.
    *   `series` (ForeignKey(MetricType)): Metric type.
    *   `value` (JSONField): Data value (validated against `MetricType` schema).
    *   `time` (TimescaleDateTimeField, interval="1 week"): Data point time (hypertable partitioning key).
    *   Index: `(time, series, session)`


### Design Decisions

#### 1. Series Name Representation

How should we represent our metric series names (e.g., `session.gut_health_score`)? I weigh the pros and cons of two options.

##### 1.1 Flat Representation (Current Approach)

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

##### 1.2 Hierarchical Representation (Alternative Considered)

Uses a self-referential `parent` relationship in `MetricType` to split series names into hierarchical fields.

- **Pros**:
  - **Flexible Queries**: Easily filter or group by hierarchy levels.
  - **Clearer Validation**: Provides a structured framework for managing series names.

- **Cons**:
  - **Complexity**: Adds recursive lookups and join-heavy queries.
  - **Performance**: Slower for large datasets or deep hierarchies.
  - **Overkill**: Current needs are met with simpler regex filtering in the flat model.
    
---

#### 2. Metric Value Storage

This section evaluates three approaches for storing metric values, based on their simplicity, performance, and future extensibility.

##### 2.1 `TextField` with Casting (Current Approach)

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

##### 2.2 JSONField (Future-Proof Alternative)

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

---

## Future Work and Scale

*   **Continuous Aggregates:** Implement continuous aggregates (e.g., daily, monthly) for faster aggregation queries after analyzing query pattern.
*   **Data Compression:** Implement TimescaleDB compression for reduced storage costs and improved I/O.
*   **Percentile Aggregates:** Add support for percentile-based aggregations (median, p90, p99).
*   **Scalable Architecture:** Design a scalable system architecture with on-prem ingestion and cloud-based read replicas for high availability.
