from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class TenantModel:
    name: str
    suite: str
    sqft: float
    rate_psf: float
    lease_exp: str              # MM-DD-YYYY
    year1_override: Optional[float]
    projection_type: str        # "compounded" | "pro_rated"
    growth_rate: float
    flat_increase: float
    pct_increase: float
    renewed: bool
    renewal_start: str          # MM-DD-YYYY or ""
    renewal_term_years: int
    renewal_projection_type: str
    renewal_growth_rate: float
    renewal_flat_increase: float
    renewal_pct_increase: float

    def to_dict(self) -> dict:
        return {
            "name": self.name, "suite": self.suite,
            "sqft": self.sqft, "rate_psf": self.rate_psf,
            "lease_exp": self.lease_exp, "year1_override": self.year1_override,
            "projection_type": self.projection_type, "growth_rate": self.growth_rate,
            "flat_increase": self.flat_increase, "pct_increase": self.pct_increase,
            "renewed": self.renewed, "renewal_start": self.renewal_start,
            "renewal_term_years": self.renewal_term_years,
            "renewal_projection_type": self.renewal_projection_type,
            "renewal_growth_rate": self.renewal_growth_rate,
            "renewal_flat_increase": self.renewal_flat_increase,
            "renewal_pct_increase": self.renewal_pct_increase,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TenantModel:
        return cls(**d)
