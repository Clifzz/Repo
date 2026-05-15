from __future__ import annotations
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app.models.tenant import TenantModel


def project_tenant_rents(
    tenant: TenantModel, start_year: int, years: int
) -> tuple[list[float], list[float]]:
    rents: list[float] = []
    rates: list[float] = []

    lease_exp = datetime.strptime(tenant.lease_exp, "%m-%d-%Y")
    renewal_start = (
        datetime.strptime(tenant.renewal_start, "%m-%d-%Y")
        if tenant.renewed and tenant.renewal_start else None
    )

    base_rate = (tenant.year1_override / tenant.sqft) if tenant.year1_override is not None else tenant.rate_psf

    # Pre-compute pro-rated months split (only used when projection_type == "pro_rated")
    mo = lease_exp.month
    dy = lease_exp.day
    months_old = min(mo + (1 if dy >= 15 else 0), 12)
    months_new = max(12 - months_old, 0)

    for i in range(years):
        year = start_year + i

        if i == 0:
            rent = tenant.year1_override if tenant.year1_override is not None else tenant.sqft * base_rate
            rate = base_rate

        elif renewal_start and datetime(year, 1, 1) >= renewal_start:
            years_into_renewal = year - renewal_start.year
            renewal_base = _rate_at_renewal(tenant, renewal_start, start_year, base_rate)
            rate = _apply_growth(
                renewal_base, years_into_renewal,
                tenant.renewal_projection_type,
                tenant.renewal_growth_rate,
                tenant.renewal_flat_increase,
                tenant.renewal_pct_increase,
            )
            rent = tenant.sqft * rate

        elif tenant.projection_type == "pro_rated":
            if tenant.flat_increase > 0:
                old_rate = base_rate + tenant.flat_increase * (i - 1)
                new_rate = base_rate + tenant.flat_increase * i
            else:
                old_rate = base_rate * ((1 + tenant.pct_increase) ** (i - 1))
                new_rate = base_rate * ((1 + tenant.pct_increase) ** i)

            rate = (old_rate * months_old + new_rate * months_new) / 12
            rent = tenant.sqft * rate

        else:  # compounded
            rate = base_rate * ((1 + tenant.growth_rate) ** i)
            rent = tenant.sqft * rate

        rents.append(rent)
        rates.append(rate)

    return rents, rates


def _rate_at_renewal(
    tenant: TenantModel, renewal_start: datetime, start_year: int, base_rate: float
) -> float:
    # n is the number of growth steps applied up through the last year before renewal.
    # Year index i=0 → 0 growth steps; i=1 → 1 growth step; etc.
    # The last year before renewal is (renewal_start.year - 1), which is at index
    # (renewal_start.year - 1 - start_year).
    n = renewal_start.year - 1 - start_year
    assert n >= 0, f"renewal_start must be after start_year; got n={n}"
    return _apply_growth(
        base_rate, n,
        tenant.projection_type,
        tenant.growth_rate,
        tenant.flat_increase,
        tenant.pct_increase,
    )


def _apply_growth(
    base: float, n: int, proj_type: str, growth: float, flat: float, pct: float
) -> float:
    if proj_type == "compounded":
        return base * ((1 + growth) ** n)
    if proj_type == "pro_rated":
        return (base + flat * n) if flat > 0 else base * ((1 + pct) ** n)
    raise ValueError(f"Unknown projection_type: {proj_type!r}")


def calculate_lease_remaining(
    lease_exp: datetime, start_year: int, start_month: int
) -> tuple[str, float]:
    as_of = datetime(start_year, start_month, 1)
    rd = relativedelta(lease_exp, as_of)
    years_remaining = rd.years + rd.months / 12
    label = f"{rd.years} yrs, {rd.months} mos"
    return label, years_remaining
