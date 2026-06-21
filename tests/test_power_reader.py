from app.power_reader import PowerSensor, summarize_power


def test_summarize_power_groups_cpu_gpu_other_and_baseline() -> None:
    sensors = [
        PowerSensor(name="CPU Package", value_watts=48.5, hardware_name="Intel CPU"),
        PowerSensor(name="GPU Board Power", value_watts=92.25, hardware_name="NVIDIA GPU"),
        PowerSensor(name="Memory Power", value_watts=8.0, hardware_name="Motherboard"),
    ]

    summary = summarize_power(sensors, baseline_watts=35.0)

    assert summary.cpu_watts == 48.5
    assert summary.gpu_watts == 92.25
    assert summary.other_watts == 43.0
    assert summary.total_watts == 183.75
    assert summary.sensor_count == 3
    assert summary.error is None


def test_summarize_power_ignores_missing_and_invalid_values() -> None:
    sensors = [
        PowerSensor(name="CPU Package", value_watts=None, hardware_name="CPU"),
        PowerSensor(name="GPU Power", value_watts=-4.0, hardware_name="GPU"),
        PowerSensor(name="GPU Power", value_watts=120.0, hardware_name="GPU"),
    ]

    summary = summarize_power(sensors, baseline_watts=35.0)

    assert summary.cpu_watts == 0.0
    assert summary.gpu_watts == 120.0
    assert summary.other_watts == 35.0
    assert summary.total_watts == 155.0
    assert summary.sensor_count == 1


def test_summarize_power_reports_error_when_no_power_sensors_are_available() -> None:
    summary = summarize_power([], baseline_watts=35.0)

    assert summary.total_watts == 35.0
    assert summary.other_watts == 35.0
    assert summary.sensor_count == 0
    assert summary.error == "No power sensors were found."
