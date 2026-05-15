# tests/test_projections.py
import pytest
from app.logic.projections import project_tenant_rents, calculate_lease_remaining
from app.models.tenant import TenantModel
from datetime import datetime


def _tenant(**kwargs):
    defaults = dict(
        name="T", suite="1", sqft=1000.0, rate_psf=20.0,
        lease_exp="12-31-2030", year1_override=None,
        projection_type="compounded", growth_rate=0.0,
        flat_increase=0.0, pct_increase=0.0,
        renewed=False, renewal_start="", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.0,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )
    defaults.update(kwargs)
    return TenantModel(**defaults)


def test_compounded_year1_no_override():
    t = _tenant(rate_psf=20.0, sqft=1000.0, growth_rate=0.025)
    rents, rates = project_tenant_rents(t, 2025, 3)
    assert rents[0] == pytest.approx(20000.0)
    assert rates[0] == pytest.approx(20.0)


def test_compounded_growth():
    t = _tenant(rate_psf=20.0, sqft=1000.0, growth_rate=0.025)
    rents, rates = project_tenant_rents(t, 2025, 3)
    assert rents[1] == pytest.approx(1000.0 * 20.0 * 1.025)
    assert rents[2] == pytest.approx(1000.0 * 20.0 * 1.025 ** 2)


def test_year1_override_sets_base():
    t = _tenant(rate_psf=20.0, sqft=1000.0, year1_override=25000.0, growth_rate=0.02)
    rents, rates = project_tenant_rents(t, 2025, 2)
    assert rents[0] == pytest.approx(25000.0)
    assert rents[1] == pytest.approx(25000.0 * 1.02)


def test_prorated_flat():
    # Lease expires June 15 → months_old=7, months_new=5
    t = _tenant(
        rate_psf=20.0, sqft=1000.0, lease_exp="06-15-2025",
        projection_type="pro_rated", flat_increase=1.0,
    )
    rents, rates = project_tenant_rents(t, 2025, 2)
    assert rents[0] == pytest.approx(20000.0)
    # Year 2: old_rate=20, new_rate=21, months_old=7, months_new=5
    blended = (20.0 * 7 + 21.0 * 5) / 12
    assert rates[1] == pytest.approx(blended)
    assert rents[1] == pytest.approx(1000.0 * blended)


def test_prorated_pct():
    t = _tenant(
        rate_psf=20.0, sqft=1000.0, lease_exp="06-15-2025",
        projection_type="pro_rated", pct_increase=0.03,
    )
    rents, rates = project_tenant_rents(t, 2025, 2)
    old_rate = 20.0
    new_rate = 20.0 * 1.03
    blended = (old_rate * 7 + new_rate * 5) / 12
    assert rates[1] == pytest.approx(blended)


def test_renewal_switchover():
    t = _tenant(
        rate_psf=20.0, sqft=1000.0, lease_exp="12-31-2026",
        projection_type="compounded", growth_rate=0.02,
        renewed=True, renewal_start="01-01-2027",
        renewal_term_years=5, renewal_projection_type="compounded",
        renewal_growth_rate=0.03,
    )
    rents, rates = project_tenant_rents(t, 2025, 4)
    # Year 1 (2025): base rate 20
    assert rents[0] == pytest.approx(20000.0)
    # Year 3 (2027): renewal kicks in, base = rate at renewal start
    # rate at end of original term year 2 (2026): 20*(1.02)^1 = 20.40
    renewal_base = 20.0 * (1.02 ** 1)
    assert rates[2] == pytest.approx(renewal_base)
    # Year 4 (2028): 1 year into renewal
    assert rates[3] == pytest.approx(renewal_base * 1.03)


def test_year1_override_zero_rent_free():
    t = _tenant(rate_psf=20.0, sqft=1000.0, year1_override=0.0, growth_rate=0.02)
    rents, rates = project_tenant_rents(t, 2025, 2)
    assert rents[0] == pytest.approx(0.0)
    assert rates[0] == pytest.approx(0.0)


def test_calculate_lease_remaining():
    exp = datetime(2027, 6, 30)
    label, years = calculate_lease_remaining(exp, 2025, 1)
    assert years == pytest.approx(2.5, abs=0.1)
    assert "yrs" in label
