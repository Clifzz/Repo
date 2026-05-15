from __future__ import annotations
from datetime import datetime
from app.models.session import ProFormaSession
from app.logic.projections import project_tenant_rents, calculate_lease_remaining

OPEX_GROWTH = 0.025


def calculate_proforma(session: ProFormaSession) -> dict:
    tenants = session.tenants
    years = session.years
    start_year = session.start_year

    total_sqft = sum(t.sqft for t in tenants)

    tenant_rents: dict[int, list[float]] = {}
    tenant_rates: dict[int, list[float]] = {}
    for i, t in enumerate(tenants):
        rents, rates = project_tenant_rents(t, start_year, years)
        tenant_rents[i] = rents
        tenant_rates[i] = rates

    rental_revenue = [sum(tenant_rents[i][y] for i in range(len(tenants))) for y in range(years)]

    opex_y0 = total_sqft * session.opex_psf
    expense_revenue = [opex_y0 * ((1 + OPEX_GROWTH) ** y) for y in range(years)]
    opex_by_year = [opex_y0 * ((1 + OPEX_GROWTH) ** y) for y in range(years)]
    opex_per_sf = [o / total_sqft if total_sqft else 0.0 for o in opex_by_year]

    gross_revenue = [r + e for r, e in zip(rental_revenue, expense_revenue)]
    nois = [r + e - o for r, e, o in zip(rental_revenue, expense_revenue, opex_by_year)]
    values = [n / session.cap_rate for n in nois]
    value_psfs = [v / total_sqft if total_sqft else 0.0 for v in values]

    avg_rates = [
        sum(tenant_rates[i][y] * tenants[i].sqft for i in range(len(tenants))) / total_sqft
        for y in range(years)
    ]

    expiring_rents_by_year = [0.0] * years
    for i, t in enumerate(tenants):
        exp_date = datetime.strptime(t.lease_exp, "%m-%d-%Y")
        idx = exp_date.year - start_year
        if 0 <= idx < years:
            expiring_rents_by_year[idx] += tenant_rents[i][idx]

    expiring_rent_percents = [
        exp / rental_revenue[y] if rental_revenue[y] else 0.0
        for y, exp in enumerate(expiring_rents_by_year)
    ]

    market_rates = [session.market_avg_rate * ((1 + session.market_growth_pct) ** i) for i in range(years)]
    weighted_avg_rate = sum(t.rate_psf * t.sqft for t in tenants) / total_sqft if total_sqft else 0.0

    return {
        "tenant_rents": tenant_rents, "tenant_rates": tenant_rates,
        "rental_revenue": rental_revenue, "expense_revenue": expense_revenue,
        "gross_revenue": gross_revenue, "opex_by_year": opex_by_year,
        "opex_per_sf": opex_per_sf, "nois": nois, "values": values,
        "value_psfs": value_psfs, "avg_rates": avg_rates,
        "expiring_rents_by_year": expiring_rents_by_year,
        "expiring_rent_percents": expiring_rent_percents,
        "market_rates": market_rates, "weighted_avg_rate": weighted_avg_rate,
        "total_sqft": total_sqft,
    }


def generate_assumptions(session: ProFormaSession) -> tuple[list[dict], dict]:
    rows = []
    total_as_is = 0.0
    total_weighted = 0.0
    total_occ_sqft = sum(t.sqft for t in session.tenants)

    for t in session.tenants:
        exp_date = datetime.strptime(t.lease_exp, "%m-%d-%Y")
        term_str, term_years = calculate_lease_remaining(exp_date, session.start_year, session.start_month)
        as_is = t.sqft * t.rate_psf
        total_as_is += as_is
        total_weighted += term_years * t.sqft
        rows.append({
            "name": t.name, "suite": t.suite, "sqft": t.sqft,
            "rate_psf": t.rate_psf, "lease_exp": t.lease_exp,
            "term_remaining": term_str, "as_is_rent": as_is,
        })

    walt = total_weighted / total_occ_sqft if total_occ_sqft else 0.0
    pct_occ = (session.occupied_sqft / session.total_sqft * 100) if session.total_sqft else 0.0

    return rows, {
        "total_as_is_rent": total_as_is, "pct_occupied": pct_occ,
        "pct_vacant": 100.0 - pct_occ, "walt": walt,
    }
