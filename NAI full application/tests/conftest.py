import pytest


@pytest.fixture
def single_tenant():
    from app.models.tenant import TenantModel
    return TenantModel(
        name="Acme Corp", suite="101", sqft=5000.0, rate_psf=20.0,
        lease_exp="12-31-2027", year1_override=None,
        projection_type="compounded", growth_rate=0.025,
        flat_increase=0.0, pct_increase=0.0,
        renewed=False, renewal_start="", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.02,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )


@pytest.fixture
def basic_session(single_tenant):
    from app.models.session import ProFormaSession
    return ProFormaSession(
        building_name="Test Tower", start_year=2025, start_month=1,
        years=5, total_sqft=10000.0, occupied_sqft=5000.0,
        opex_psf=8.0, market_avg_rate=22.0, market_growth_pct=0.025,
        cap_rate=0.065, cap_delta=0.0025,
        tenants=[single_tenant],
    )
