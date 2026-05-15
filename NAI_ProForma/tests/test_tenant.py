# tests/test_tenant.py
from app.models.tenant import TenantModel


def test_to_dict_round_trip():
    t = TenantModel(
        name="Acme", suite="101", sqft=5000.0, rate_psf=20.0,
        lease_exp="12-31-2027", year1_override=110000.0,
        projection_type="compounded", growth_rate=0.025,
        flat_increase=0.0, pct_increase=0.0,
        renewed=True, renewal_start="01-01-2028", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.02,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )
    assert TenantModel.from_dict(t.to_dict()) == t


def test_optional_year1_override_none():
    t = TenantModel(
        name="X", suite="1", sqft=1000.0, rate_psf=15.0,
        lease_exp="06-30-2026", year1_override=None,
        projection_type="pro_rated", growth_rate=0.0,
        flat_increase=0.5, pct_increase=0.0,
        renewed=False, renewal_start="", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.0,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )
    d = t.to_dict()
    assert d["year1_override"] is None
    assert TenantModel.from_dict(d).year1_override is None
