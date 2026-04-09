from WorkAI.notifier import should_alert_on_cost_spike, should_alert_on_failed_runs


def test_cost_spike_requires_history() -> None:
    assert should_alert_on_cost_spike(today_cost=50.0, history=[10.0, 20.0]) is False


def test_cost_spike_threshold() -> None:
    history = [10.0, 10.0, 10.0, 10.0]
    assert should_alert_on_cost_spike(today_cost=14.9, history=history) is False
    assert should_alert_on_cost_spike(today_cost=15.0, history=history) is True


def test_failed_runs_threshold() -> None:
    assert should_alert_on_failed_runs(failed_runs=0, total_runs=0) is False
    assert should_alert_on_failed_runs(failed_runs=2, total_runs=5) is False
    assert should_alert_on_failed_runs(failed_runs=3, total_runs=20) is False
    assert should_alert_on_failed_runs(failed_runs=3, total_runs=10) is True
