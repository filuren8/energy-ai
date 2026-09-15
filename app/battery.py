import time
from dataclasses import dataclass

@dataclass
class SimulatedBattery:
    capacity_kwh: float
    max_power_kw: float
    min_soc: float
    max_soc: float
    soc: float
    efficiency: float
    power_kw: float = 0.0  # + discharge, - charge
    last_update: float = 0.0

    def __post_init__(self):
        self.last_update = time.monotonic()

    def update(self, requested_power_kw: float):
        now = time.monotonic()
        dt_h = max(0.0, now - self.last_update) / 3600.0
        self.last_update = now

        # Integrate the previously applied battery power.
        if self.power_kw >= 0:
            delta_kwh = -(self.power_kw / self.efficiency) * dt_h
        else:
            delta_kwh = (-self.power_kw * self.efficiency) * dt_h
        energy_kwh = self.capacity_kwh * self.soc / 100.0 + delta_kwh
        energy_kwh = min(self.capacity_kwh*self.max_soc/100, max(self.capacity_kwh*self.min_soc/100, energy_kwh))
        self.soc = 100.0 * energy_kwh / self.capacity_kwh

        requested_power_kw = max(-self.max_power_kw, min(self.max_power_kw, requested_power_kw))
        if self.soc <= self.min_soc and requested_power_kw > 0:
            requested_power_kw = 0.0
        if self.soc >= self.max_soc and requested_power_kw < 0:
            requested_power_kw = 0.0
        self.power_kw = requested_power_kw
        return self.snapshot()

    def snapshot(self):
        return {"soc": round(self.soc, 2), "power_kw": round(self.power_kw, 3),
                "capacity_kwh": self.capacity_kwh, "max_power_kw": self.max_power_kw}
