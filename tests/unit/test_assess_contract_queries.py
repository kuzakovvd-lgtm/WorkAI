from WorkAI.assess import queries


def test_assess_queries_use_contract_columns_not_hash_derivation() -> None:
    assert "hashtextextended" not in queries.LIST_EMPLOYEE_DAY_KEYS_SQL
    assert "hashtextextended" not in queries.FETCH_DAY_METRICS_SQL

    assert "employee_id" in queries.LIST_EMPLOYEE_DAY_KEYS_SQL
    assert "task_date" in queries.LIST_EMPLOYEE_DAY_KEYS_SQL

    assert "time_source = 'none'" in queries.FETCH_DAY_METRICS_SQL
    assert "result_confirmed = false" in queries.FETCH_DAY_METRICS_SQL
