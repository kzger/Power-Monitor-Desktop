from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.config import libre_hardware_monitor_dll_path


@dataclass(frozen=True)
class PowerSensor:
    name: str
    value_watts: float | None
    hardware_name: str = ""
    hardware_type: str = ""


@dataclass(frozen=True)
class PowerSummary:
    total_watts: float
    cpu_watts: float
    gpu_watts: float
    other_watts: float
    baseline_watts: float
    sensors: tuple[PowerSensor, ...]
    sensor_count: int
    error: str | None = None


def summarize_power(
    sensors: Iterable[PowerSensor],
    baseline_watts: float,
    error: str | None = None,
) -> PowerSummary:
    valid_sensors = tuple(
        sensor
        for sensor in sensors
        if sensor.value_watts is not None and sensor.value_watts >= 0.0
    )

    cpu_sensors = tuple(sensor for sensor in valid_sensors if _is_cpu_sensor(sensor))
    gpu_sensors = tuple(sensor for sensor in valid_sensors if _is_gpu_sensor(sensor))
    cpu_ids = {id(sensor) for sensor in cpu_sensors}
    gpu_ids = {id(sensor) for sensor in gpu_sensors}
    other_sensor_watts = sum(
        sensor.value_watts or 0.0
        for sensor in valid_sensors
        if id(sensor) not in cpu_ids and id(sensor) not in gpu_ids
    )

    cpu_watts = _preferred_sum(cpu_sensors, ("package", "cpu package"))
    gpu_watts = _preferred_sum(
        gpu_sensors,
        ("board power", "gpu power", "total board power", "asic power"),
    )
    baseline = max(0.0, baseline_watts)
    other_watts = baseline + other_sensor_watts
    total_watts = cpu_watts + gpu_watts + other_watts

    summary_error = error
    if not valid_sensors and summary_error is None:
        summary_error = "No power sensors were found."

    return PowerSummary(
        total_watts=round(total_watts, 2),
        cpu_watts=round(cpu_watts, 2),
        gpu_watts=round(gpu_watts, 2),
        other_watts=round(other_watts, 2),
        baseline_watts=baseline,
        sensors=valid_sensors,
        sensor_count=len(valid_sensors),
        error=summary_error,
    )


class LibreHardwareMonitorReader:
    def __init__(self, dll_path: Path | None = None) -> None:
        self._dll_path = dll_path or libre_hardware_monitor_dll_path()
        self._computer = None
        self._sensor_type = None
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def open(self) -> None:
        if self._computer is not None:
            return

        if not self._dll_path.exists():
            raise FileNotFoundError(
                f"LibreHardwareMonitor DLL not found: {self._dll_path}"
            )

        try:
            import clr  # type: ignore[import-not-found]

            clr.AddReference(str(self._dll_path))
            from LibreHardwareMonitor.Hardware import Computer, SensorType  # type: ignore

            computer = Computer()
            for property_name in (
                "IsCpuEnabled",
                "IsGpuEnabled",
                "IsMemoryEnabled",
                "IsMotherboardEnabled",
                "IsControllerEnabled",
                "IsStorageEnabled",
            ):
                try:
                    setattr(computer, property_name, True)
                except Exception:
                    pass
            computer.Open()

            self._computer = computer
            self._sensor_type = SensorType
            self._last_error = None
        except Exception as exc:
            self._last_error = f"Failed to initialize LibreHardwareMonitor: {exc}"
            self.close()
            raise RuntimeError(self._last_error) from exc

    def read_power_sensors(self) -> tuple[PowerSensor, ...]:
        try:
            self.open()
            if self._computer is None or self._sensor_type is None:
                return ()

            sensors: list[PowerSensor] = []
            for hardware in self._computer.Hardware:
                sensors.extend(self._read_hardware_power_sensors(hardware))

            self._last_error = None
            return tuple(sensors)
        except Exception as exc:
            self._last_error = str(exc)
            return ()

    def read_summary(self, baseline_watts: float) -> PowerSummary:
        sensors = self.read_power_sensors()
        return summarize_power(sensors, baseline_watts, error=self._last_error)

    def close(self) -> None:
        computer = self._computer
        self._computer = None
        if computer is None:
            return

        # LibreHardwareMonitor exposes Close(); Dispose() may also exist.
        for method_name in ("Close", "Dispose"):
            method = getattr(computer, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

    def _read_hardware_power_sensors(self, hardware: object) -> list[PowerSensor]:
        sensors: list[PowerSensor] = []
        self._update_hardware(hardware)
        sensors.extend(self._power_sensors_from_hardware(hardware))

        subhardware_items = getattr(hardware, "SubHardware", ())
        for subhardware in subhardware_items:
            self._update_hardware(subhardware)
            sensors.extend(self._power_sensors_from_hardware(subhardware))

        return sensors

    def _update_hardware(self, hardware: object) -> None:
        update = getattr(hardware, "Update", None)
        if callable(update):
            update()

    def _power_sensors_from_hardware(self, hardware: object) -> list[PowerSensor]:
        hardware_name = str(getattr(hardware, "Name", ""))
        hardware_type = str(getattr(hardware, "HardwareType", ""))
        result: list[PowerSensor] = []

        for sensor in getattr(hardware, "Sensors", ()):
            if str(getattr(sensor, "SensorType", "")) != "Power":
                continue

            value = getattr(sensor, "Value", None)
            result.append(
                PowerSensor(
                    name=str(getattr(sensor, "Name", "")),
                    value_watts=float(value) if value is not None else None,
                    hardware_name=hardware_name,
                    hardware_type=hardware_type,
                )
            )

        return result


def _is_cpu_sensor(sensor: PowerSensor) -> bool:
    text = _sensor_text(sensor)
    return "cpu" in text or "processor" in text or "central processor" in text


def _is_gpu_sensor(sensor: PowerSensor) -> bool:
    text = _sensor_text(sensor)
    gpu_markers = (
        "gpu",
        "graphics",
        "nvidia",
        "geforce",
        "radeon",
        "amd radeon",
        "intel arc",
    )
    return any(marker in text for marker in gpu_markers)


def _sensor_text(sensor: PowerSensor) -> str:
    return " ".join(
        (sensor.name, sensor.hardware_name, sensor.hardware_type)
    ).casefold()


def _preferred_sum(sensors: Iterable[PowerSensor], preferred_names: tuple[str, ...]) -> float:
    sensor_tuple = tuple(sensors)
    preferred = tuple(
        sensor
        for sensor in sensor_tuple
        if any(name in sensor.name.casefold() for name in preferred_names)
    )
    selected = preferred or sensor_tuple
    return sum(sensor.value_watts or 0.0 for sensor in selected)
