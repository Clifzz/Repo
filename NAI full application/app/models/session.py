from __future__ import annotations
import json
from dataclasses import dataclass, field
from app.models.tenant import TenantModel


@dataclass
class ProFormaSession:
    building_name: str = ""
    start_year: int = 2025
    start_month: int = 1
    years: int = 10
    total_sqft: float = 0.0
    occupied_sqft: float = 0.0
    opex_psf: float = 0.0
    market_avg_rate: float = 0.0
    market_growth_pct: float = 0.0
    cap_rate: float = 0.0
    cap_delta: float = 0.0025
    tenants: list[TenantModel] = field(default_factory=list)

    def to_json(self) -> str:
        d = {
            "building_name": self.building_name, "start_year": self.start_year,
            "start_month": self.start_month, "years": self.years,
            "total_sqft": self.total_sqft, "occupied_sqft": self.occupied_sqft,
            "opex_psf": self.opex_psf, "market_avg_rate": self.market_avg_rate,
            "market_growth_pct": self.market_growth_pct, "cap_rate": self.cap_rate,
            "cap_delta": self.cap_delta,
            "tenants": [t.to_dict() for t in self.tenants],
        }
        return json.dumps(d)

    @classmethod
    def from_json(cls, s: str) -> ProFormaSession:
        d = json.loads(s)
        tenants = [TenantModel.from_dict(t) for t in d.pop("tenants", [])]
        return cls(tenants=tenants, **d)
