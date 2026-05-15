# tests/test_calculator.py
import pytest
from app.logic.calculator import calculate_proforma, generate_assumptions


def test_rental_revenue_sums_tenants(basic_session):
    result = calculate_proforma(basic_session)
    # Single tenant: 5000 SF * $20/SF = $100,000 Y1
    assert result["rental_revenue"][0] == pytest.approx(100000.0)


def test_noi_equals_revenue_minus_opex(basic_session):
    result = calculate_proforma(basic_session)
    for y in range(basic_session.years):
        expected = result["rental_revenue"][y] + result["expense_revenue"][y] - result["opex_by_year"][y]
        assert result["nois"][y] == pytest.approx(expected)


def test_building_value_is_noi_over_cap(basic_session):
    result = calculate_proforma(basic_session)
    for y in range(basic_session.years):
        assert result["values"][y] == pytest.approx(result["nois"][y] / basic_session.cap_rate)


def test_expiring_rent_bug_fixed(basic_session):
    # Bug in original: loop body outside for, only last tenant counted.
    # With one tenant expiring in 2027 (year index 2 from 2025), rent should
    # be non-zero only at index 2.
    result = calculate_proforma(basic_session)
    assert result["expiring_rents_by_year"][2] > 0
    assert result["expiring_rents_by_year"][0] == 0.0


def test_generate_assumptions_walt(basic_session):
    rows, summary = generate_assumptions(basic_session)
    assert len(rows) == 1
    assert summary["walt"] > 0
    assert summary["pct_occupied"] == pytest.approx(50.0)


def test_expiring_rent_two_tenants(basic_session):
    from app.models.tenant import TenantModel
    from app.models.session import ProFormaSession
    # Two tenants expiring in different years: tenant A in 2025 (idx 0), B in 2027 (idx 2)
    t_a = TenantModel(
        name="Tenant A", suite="101", sqft=3000.0, rate_psf=20.0,
        lease_exp="12-31-2025", year1_override=None,
        projection_type="compounded", growth_rate=0.0,
        flat_increase=0.0, pct_increase=0.0,
        renewed=False, renewal_start="", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.0,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )
    t_b = TenantModel(
        name="Tenant B", suite="102", sqft=2000.0, rate_psf=25.0,
        lease_exp="12-31-2027", year1_override=None,
        projection_type="compounded", growth_rate=0.0,
        flat_increase=0.0, pct_increase=0.0,
        renewed=False, renewal_start="", renewal_term_years=5,
        renewal_projection_type="compounded", renewal_growth_rate=0.0,
        renewal_flat_increase=0.0, renewal_pct_increase=0.0,
    )
    session = ProFormaSession(
        building_name="Two-Tenant Test", start_year=2025, start_month=1,
        years=5, total_sqft=10000.0, occupied_sqft=5000.0,
        opex_psf=8.0, market_avg_rate=22.0, market_growth_pct=0.025,
        cap_rate=0.065, cap_delta=0.0025,
        tenants=[t_a, t_b],
    )
    result = calculate_proforma(session)
    # A expires year 0 (2025): should have non-zero expiring rent at index 0
    assert result["expiring_rents_by_year"][0] == pytest.approx(3000.0 * 20.0)
    # B expires year 2 (2027): should have non-zero expiring rent at index 2
    assert result["expiring_rents_by_year"][2] == pytest.approx(2000.0 * 25.0)
    # No other year should have expiring rent
    assert result["expiring_rents_by_year"][1] == 0.0
