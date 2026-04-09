from WorkAI.assess import queries


def test_assess_queries_use_contract_columns_not_hash_derivation() -> None:
    assert "hashtextextended" not in queries.LIST_EMPLOYEE_DAY_KEYS_SQL
    assert "hashtextextended" not in queries.FETCH_DAY_METRICS_SQL

    assert "employee_id" in queries.LIST_EMPLOYEE_DAY_KEYS_SQL
    assert "task_date" in queries.LIST_EMPLOYEE_DAY_KEYS_SQL

    assert "time_source = 'none'" in queries.FETCH_DAY_METRICS_SQL
    assert "result_confirmed = false" in queries.FETCH_DAY_METRICS_SQL


def test_scoring_queries_use_contract_task_fields_only() -> None:
    assert "employee_name_norm" not in queries.FETCH_SCORING_TASKS_BY_DATE_SQL
    assert "task_text_norm" not in queries.FETCH_SCORING_TASKS_BY_DATE_SQL
    assert "hashtextextended" not in queries.FETCH_SCORING_TASKS_BY_DATE_SQL

    assert "id" in queries.FETCH_SCORING_TASKS_BY_DATE_SQL
    assert "time_source" in queries.FETCH_SCORING_TASKS_BY_DATE_SQL
    assert "result_confirmed" in queries.FETCH_SCORING_TASKS_BY_DATE_SQL
    assert "is_smart" in queries.FETCH_SCORING_TASKS_BY_DATE_SQL


def test_aggregation_queries_use_db_contract_tables() -> None:
    assert "FROM tasks_normalized AS tn" in queries.FETCH_AGGREGATION_INPUT_BY_DATE_SQL
    assert "LEFT JOIN daily_task_assessments AS dta" in queries.FETCH_AGGREGATION_INPUT_BY_DATE_SQL
    assert "INSERT INTO operational_cycles" in queries.UPSERT_OPERATIONAL_CYCLE_SQL
