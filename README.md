Real Estate Scripts 

#pro forma gen 2.0 (DONE) - For Work - Just need to scale op ex

import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import numbers
import calendar

class Tenant:
    def __init__(self, name, suite, sqft, rate_psf, lease_exp, lease_remaining=None, year1_override=None):
        self.name = name
        self.suite = suite
        self.sqft = sqft
        self.rate_psf = rate_psf
        self.lease_exp = lease_exp
        self.lease_exp_date = datetime.strptime(lease_exp, "%m-%d-%Y")
        self.original_lease_exp_date = self.lease_exp_date
        self.lease_remaining = lease_remaining
        self.year1_override = year1_override
        self.projected_rents = []
        self.projected_rates_psf = []
        self.tenant_growth_input = 0.0
        self.flat_increase = 0.0
        self.custom_percentage_increase = 0.0
        self.projection_type = None
        self.renewed = False
        self.renewal_projection_type = None
        self.renewal_duration_years = 5
        self.renewal_growth_rate = 0.0
        self.renewal_flat_increase = 0.0
        self.renewal_pct_increase = 0.0

    def calculate_as_is_rent(self):
        return self.sqft * self.rate_psf

    def project_rents(self, start_year, years, market_avg_rate, market_growth_pct):
        self.projected_rents = []
        self.projected_rates_psf = []

        # Determine base rate for year 1
        if self.year1_override is not None:
            year1_rate = self.year1_override / self.sqft
        else:
            year1_rate = self.rate_psf
        base_rate = year1_rate

        for i in range(years):
            current_year = start_year + i
            start_of_year = datetime(current_year, 1, 1)
            end_of_year   = datetime(current_year, 12, 31)

            expired = not self.renewed and self.lease_exp_date < start_of_year
            expires_this_year = not self.renewed and start_of_year <= self.lease_exp_date <= end_of_year

            exp_month = self.lease_exp_date.month
            exp_day   = self.lease_exp_date.day
            dim       = calendar.monthrange(current_year, exp_month)[1]

            # --- Year 1 ---
            if i == 0:
                rate = year1_rate
                rent = self.year1_override if self.year1_override is not None else self.sqft * year1_rate

            elif self.projection_type == "pro_rated":
                expiration_month = self.lease_exp_date.month
                expiration_day = self.lease_exp_date.day
                months_old_rate = 1 if expiration_month == 1 else min(expiration_month + (1 if expiration_day >= 15 else 0), 12)
                months_new_rate = max(12 - months_old_rate, 0)

                if self.flat_increase > 0:
                    old_rate = base_rate + self.flat_increase * (i - 1)
                    new_rate = base_rate + self.flat_increase * i
                else:
                    old_rate = base_rate * ((1 + self.custom_percentage_increase) ** (i - 1))
                    new_rate = base_rate * ((1 + self.custom_percentage_increase) ** i)

                blended_rate = ((old_rate * months_old_rate) + (new_rate * months_new_rate)) / 12
                rate = blended_rate
                rent = self.sqft * rate

            elif self.projection_type == "compounded":
                rate = base_rate * ((1 + self.tenant_growth_input) ** i)
                rent = self.sqft * rate

            else:
                rate = base_rate
                rent = self.sqft * rate

            self.projected_rents.append(rent)
            self.projected_rates_psf.append(rate)



    def set_projection_details(self):
        # FIRST LEASE TERM DETAILS
        print(f"\nEnter initial lease projection details for {self.name}:")
        self.projection_type = input(f"  Projection type (pro_rated/compounded): ").strip()
        if self.projection_type == "compounded":
            self.tenant_growth_input = float(input(f"  Annual growth rate (e.g. 2.5 for 2.5%): ")) / 100
        elif self.projection_type == "pro_rated":
            is_flat = input(f"  Is the pro-rated rate flat? (yes/no): ").strip().lower()
            if is_flat == "yes":
                self.flat_increase = float(input(f"  Flat rate increase per year: "))
            else:
                self.custom_percentage_increase = float(input(f"  Annual percent increase (e.g. 2.5 for 2.5%): ")) / 100
        else:
            raise ValueError("Invalid projection type entered")

        # RENEWAL PROMPT AND DETAILS
        renewal_prompt = input(f"Will {self.name}'s lease renew? (yes/no): ").strip().lower()
        if renewal_prompt == "yes":
            self.renewed = True
            print(f"\nEnter renewal lease terms for {self.name}:")
            self.renewal_projection_type = input("  Renewal projection type (pro_rated/compounded): ").strip()
            self.renewal_duration_years = int(input("  Renewal lease length (years): "))

            if self.renewal_projection_type == "compounded":
                self.renewal_growth_rate = float(input("  Renewal compounded growth rate (e.g. 2.5 for 2.5%): ")) / 100
            elif self.renewal_projection_type == "pro_rated":
                is_flat = input("  Is the renewal pro-rated rate flat? (yes/no): ").strip().lower()
                if is_flat == "yes":
                    self.renewal_flat_increase = float(input("  Renewal flat increase per year: "))
                else:
                    self.renewal_pct_increase = float(input("  Renewal annual % increase (e.g. 2.5 for 2.5%): ")) / 100
            else:
                raise ValueError("Invalid renewal projection type.")

# === Helper Function ===
from dateutil.relativedelta import relativedelta

def calculate_lease_remaining(lease_exp_date, start_year, start_month):

    as_of = datetime(start_year, start_month, 1)
    rd = relativedelta(lease_exp_date, as_of)
    fractional_years = rd.years + rd.months / 12
    return f"{rd.years} yrs, {rd.months} mos", fractional_years

# === Data Collection ===
class UserInput:
    def __init__(self):
        self.cap_delta = 0.0025
        self.building_name = ""
        self.total_sqft = 0
        self.occupied_sqft = 0
        self.opex_psf = 0
        self.growth_rate = 0
        self.cap_rate = 0
        self.market_avg_rate = 0
        self.market_growth_pct = 0
        self.start_year = 0
        self.start_month = 0
        self.years = 0

    def collect(self):
        self.building_name = input("Enter the name of the building for this proforma: ").strip()
        delta = input("Enter cap rate sensitivity delta (e.g., 0.25 for ±0.25%) or press Enter for default 0.25: ").strip()
        self.cap_delta = float(delta)/100 if delta else 0.0025
        print("=== Proforma Input ===")
        self.total_sqft = float(input("Total Sq/ft rented: "))
        self.occupied_sqft = float(input("Occupied square footage: "))
        self.opex_psf = float(input("Operating expenses per square foot ($): "))
        self.growth_rate = float(input("Market rent growth rate (e.g. 2.5 for 2.5%): ")) / 100
        self.cap_rate = float(input("Cap rate ( e.g. 6.25 for 6.25%): ")) / 100
        self.market_avg_rate = float(input("Market average rate (e.g. 21.50): "))
        self.market_growth_pct = float(input("Market rent growth percentage ( e.g. 2.5 for 2.5%): ")) / 100
        self.start_year = int(input("Enter start year of proforma (e.g. 2024): "))
        self.start_month = int(input("Enter start month of proforma (1–12): "))
        self.years = int(input("Enter number of years to project: "))

    def to_tuple(self):
        return (
        building_name, tenants, total_sqft, occupied_sqft, total_rent,
        opex_psf, growth_rate, cap_rate, cap_delta,
        market_avg_rate, market_growth_pct,
        start_year, start_month, years)


def collect_input():
    user_input = UserInput()
    user_input.collect()

    building_name = user_input.building_name
    total_sqft = user_input.total_sqft
    occupied_sqft = user_input.occupied_sqft
    opex_psf = user_input.opex_psf
    growth_rate = user_input.growth_rate
    cap_rate = user_input.cap_rate
    cap_delta = user_input.cap_delta
    market_avg_rate = user_input.market_avg_rate
    market_growth_pct = user_input.market_growth_pct
    start_year = user_input.start_year
    start_month = user_input.start_month
    years = user_input.years

    tenants = []
    num_tenants = int(input("Enter number of tenants: "))
    for i in range(num_tenants):
        print("")
        print(f"--- Tenant {i + 1} ---")
        name = input("  Name: ")
        suite = input("  Suite #: ")
        sqft = float(input("  Square footage: "))
        rate_psf = float(input("  Current rent per SF: "))
        lease_exp = input("  Lease expiration (MM-DD-YYYY): ")
        override = input("  Override Year 1 rent? Leave blank if none: ")
        year1_override = float(override) if override else None

        tenant = Tenant(name, suite, sqft, rate_psf, lease_exp, year1_override=year1_override)

        print("")
        print(f"--- Initial Lease Term Details for {tenant.name} ---")
        tenant.projection_type = input("  Projection type (pro_rated/compounded): ").strip()

        if tenant.projection_type == "compounded":
            tenant.tenant_growth_input = float(input("  Annual growth rate (e.g. 2.5 for 2.5%): ")) / 100
        elif tenant.projection_type == "pro_rated":
            is_flat = input("  Is the pro-rated rate flat? (yes/no): ").strip().lower()
            if is_flat == "yes":
                tenant.flat_increase = float(input("  Flat rate increase per year: "))
            else:
                tenant.custom_percentage_increase = float(input("  Annual percent increase (e.g. 2.5 for 2.5%): ")) / 100
        else:
            raise ValueError("Invalid projection type entered")

        # Only ask about renewal if lease expires within the projection window
        projection_end = datetime(start_year + years - 1, 12, 31)
        if tenant.lease_exp_date <= projection_end and input(f"Will {tenant.name}'s lease renew? (yes/no): ").strip().lower() == "yes":
            tenant.renewed = True
            # Ask for new lease start date and compute new expiration
            new_start = input("  New lease START date (MM-DD-YYYY): ").strip()
            start_dt = datetime.strptime(new_start, "%m-%d-%Y")
            term_years = int(input("  Renewal lease term (years): ").strip())
            tenant.renewal_duration_years = term_years
            tenant.lease_exp_date = start_dt + relativedelta(years=term_years)
            print("")
            print(f"--- Renewal Lease Terms for {tenant.name} ---")
            tenant.renewal_projection_type = input("  Renewal projection type (pro_rated/compounded): ").strip()
            if tenant.renewal_projection_type == "compounded":
                tenant.renewal_growth_rate = float(input("  Renewal growth rate (%): ").strip()) / 100
            else:
                if input("  Renewal pro-rated flat increase? (yes/no): ").strip().lower() == "yes":
                    tenant.renewal_flat_increase = float(input("  Renewal flat increase per year: ").strip())
                else:
                    tenant.renewal_pct_increase = float(input("  Renewal % increase per year: ").strip()) / 100
        tenants.append(tenant)

    total_rent = sum(t.sqft * t.rate_psf for t in tenants)

    return (
        building_name, tenants, total_sqft, occupied_sqft, total_rent,
        opex_psf, growth_rate, cap_rate, cap_delta, market_avg_rate, market_growth_pct,
        start_year, start_month, years
    )

def generate_assumptions_table(tenants, total_sqft, occupied_sqft, start_year, start_month, walt_value=None):
    """
    Builds the assumptions table and summary, computing WALT from the original lease expiration (pre-renewal).
    """
    data = []
    total_weighted_lease_term = 0.0
    total_as_is_rent = 0.0
    total_sqft_occupied = sum(t.sqft for t in tenants)

    for t in tenants:
        # Use original expiration for term remaining and display
        term_str, term_years = calculate_lease_remaining(
            t.original_lease_exp_date, start_year, start_month
        )
        as_is_rent = t.calculate_as_is_rent()
        total_as_is_rent += as_is_rent
        total_weighted_lease_term += term_years * t.sqft

        data.append([
            t.name,
            t.suite,
            t.sqft,
            f"${t.rate_psf:.2f}",
            t.original_lease_exp_date.strftime("%m-%d-%Y"),
            term_str,
            f"${as_is_rent:,.2f}"
        ])

    # Compute WALT from original expirations
    walt = (total_weighted_lease_term / total_sqft_occupied) if total_sqft_occupied else 0

    assumptions_df = pd.DataFrame(
        data,
        columns=["TENANCY", "SUITE #", "SIZE (SF)", "$/SF",
                 "LEASE EXP DATE", "LEASE TERM REMAINING", "AS IS RENT"]
    )

    percent_occupied = (occupied_sqft / total_sqft) * 100 if total_sqft else 0
    percent_vacant = 100 - percent_occupied

    totals_df = pd.DataFrame({
        "Label": [
            "TOTAL BUILDING RENT:",
            "TOTAL AS IS RENT:",
            "VACANT:",
            "OCCUPIED:",
            "W.A.L.T. (yrs)"
        ],
        "Value": [
            f"{total_sqft:,} SF",
            f"${total_as_is_rent:,.2f}",
            f"{percent_vacant:.2f}%",
            f"{percent_occupied:.2f}%",
            f"{walt:.2f}"
        ]
    })
    return assumptions_df, totals_df

# === Pro Forma Calculator ===
# This function calculates rental income, expenses, NOI, property value, and other key financial metrics.
def calculate_proforma(total_rent, opex_psf, growth_rate, cap_rate, tenants, market_avg_rate, market_growth_pct, start_year, years):
    total_sqft = sum(t.sqft for t in tenants)  # Calculate total square footage from tenants
    total_opex = total_sqft * opex_psf  # Total operating expenses
    expense_revenue_y1 = sum(t.sqft * opex_psf for t in tenants)  # Year 1 expense revenue
    expense_revenue = [expense_revenue_y1 * ((1 + 0.025) ** y) for y in range(years)]  # Expense revenue growth

    # === Generate projected rents for each tenant ===
    for tenant in tenants:
        tenant.project_rents(start_year, years, market_avg_rate, market_growth_pct)
        assert len(tenant.projected_rents) == years, f"Incomplete rent projection for {tenant.name}"

    # === Rental Revenue ===
    rental_revenue = [sum(t.projected_rents[y] for t in tenants) for y in range(years)]

    # === Combine Rental and Expense Revenue ===
    gross_revenue = [r + e for r, e in zip(rental_revenue, expense_revenue)]

    # === Calculate Annual Operating Expenses ===
    opex_by_year = [total_opex * ((1 + 0.025) ** y) for y in range(years)]
    opex_per_sf = [opex / total_sqft for opex in opex_by_year]  # Per square foot version

    # === Net Operating Income (NOI) and Value ===
    nois = [r + e - o for r, e, o in zip(rental_revenue, expense_revenue, opex_by_year)]  # NOI = Revenue - OpEx
    values = [noi / cap_rate for noi in nois]  # Property value = NOI / Cap Rate
    value_psfs = [v / total_sqft for v in values]  # Value per SF

    # === Weighted Average Rent Rate Across Tenants ===
    avg_rates = [sum(t.projected_rates_psf[y] * t.sqft for t in tenants) / total_sqft for y in range(years)]

    # === Expiring Rent Values ===
    expiring_rents_by_year = [0.0] * years

    for t in tenants:
    # parse once
      exp_dt = datetime.strptime(t.lease_exp, "%m-%d-%Y")
    # figure out which projection‐year index that maps into
    idx = exp_dt.year - start_year
    if 0 <= idx < years:
        expiring_rents_by_year[idx] += t.projected_rents[idx]

    expiring_rent_percents = [
    exp / rental_revenue[y] if rental_revenue[y] else 0
    for y, exp in enumerate(expiring_rents_by_year)
]

    # === Initial Weighted Average Rate for Reference ===
    weighted_avg_rate_2024 = sum(t.rate_psf * t.sqft for t in tenants) / total_sqft


    # === Compile All Results ===
    return {
        'tenants': tenants,
        'rental_revenue': rental_revenue,
        'expense_revenue': expense_revenue,
        'gross_revenue': gross_revenue,
        'opex_by_year': opex_by_year,
        'opex_per_sf': opex_per_sf,
        'nois': nois,
        'values': values,
        'value_psfs': value_psfs,
        'avg_rates': avg_rates,
        'opex': total_opex,
        'total_sqft': total_sqft,
        'expiring_rents_by_year': expiring_rents_by_year,
        'expiring_rent_percents': expiring_rent_percents,
        'market_avg_rate': market_avg_rate,
        'market_growth_pct': market_growth_pct,
        'weighted_avg_rate_2024': weighted_avg_rate_2024,
        'start_year': start_year
    }

    # === Output Display and Summary Functions ===

# Displays the assumptions and summary metrics in table format
def display_assumptions(assumptions_df, totals_df, walt_value):
    print("=== ASSUMPTIONS TABLE ===")
    print(assumptions_df.to_string(index=False))  # Print tenant-level assumptions table

    print(f"W.A.L.T. (Weighted Average Lease Term): {walt_value} years")

    print("=== BUILDING SUMMARY ===")
    building_summary = totals_df[totals_df["Label"] != "W.A.L.T. (yrs)"]  # Exclude WALT row
    print(building_summary.to_string(index=False))  # Print summary table

# Displays year-by-year rent projections, value estimates, and sensitivity analysis
def display_output(result, cap_rate):
    years = len(result['rental_revenue'])
    start_year = result['start_year']
    total_building_sf = result['total_sqft']
    year_labels = [start_year + i for i in range(1, years + 1)]

    print("=== TENANT SF AND % OF PROPERTY BY YEAR (LEASE EXPIRY AWARE) ===")

   # Tables showing expiring square footage and % of building based on original expirations
    sf_matrix = []
    percent_matrix = []

    for t in result['tenants']:
        tenant_row = []
        percent_row = []
        for y in range(years):
            current_year = year_labels[y]
            # Flag original lease expirations in this projection year
            if t.original_lease_exp_date.year == current_year:
                tenant_row.append(t.sqft)
                percent_row.append(t.sqft / total_building_sf)
            else:
                tenant_row.append(0)
                percent_row.append(0)

        sf_matrix.append(tenant_row)
        percent_matrix.append(percent_row)

    # Print square footage and percentage tables
    sf_df = pd.DataFrame(sf_matrix, index=[t.name for t in result['tenants']], columns=year_labels)
    pct_df = pd.DataFrame(percent_matrix, index=[t.name for t in result['tenants']], columns=year_labels)

    print("-- Square Footage Expiring This Year --")
    print(sf_df.to_string())
    print("-- % of Property Expiring This Year --")
    print(pct_df.applymap(lambda x: f"{x:.6f}").to_string())

    # Overall Pro Forma Metrics
    print("=== PRO FORMA SUMMARY ===")
    print(f"Operating Expenses (Year 1): ${result['opex']:,.2f}")
    print(f"Cap Rate: {cap_rate*100:.2f}%")
    print(f"Market Avg Rate (Manual): ${result['market_avg_rate']:.2f}/SF")
    print(f"Market Growth % (Manual): {result['market_growth_pct']*100:.2f}%")
    print(f"2024 Weighted Avg Rate: ${result['weighted_avg_rate_2024']:.2f}/SF")

    print("=== TENANT DETAILS ===")
    for t in result['tenants']:
        print(f"Tenant: {t.name}")
        for y in range(len(t.projected_rents)):
            print(f"  Year {y+1}: ${t.projected_rents[y]:,.0f} @ ${t.projected_rates_psf[y]:.2f}/SF")

    # Main projection table
    print("=== PROJECTIONS (TOTALS) ===")
    df = pd.DataFrame({
        'Year': list(range(start_year + 1, start_year + years + 1)),
        'Rental Revenue': [f"${x:,.0f}" for x in result['rental_revenue']],
        'Expense Revenue': [f"${x:,.0f}" for x in result['expense_revenue']],
        'Total Revenue': [f"${x:,.0f}" for x in result['gross_revenue']],
        'OpEx ($)': [f"(${x:,.0f})" for x in result['opex_by_year']],
        'OpEx $/SF': [f"${x:.2f}" for x in result['opex_per_sf']],
        'NOI': [f"${x:,.0f}" for x in result['nois']],
        'Value': [f"${x:,.0f}" for x in result['values']],
        '$/SF': [f"${x:,.2f}" for x in result['value_psfs']],
        'Avg Rate/SF': [f"${x:,.2f}" for x in result['avg_rates']],
        'Expiring <2025': [f"${x:,.0f}" for x in result['expiring_rents_by_year']],
        '% of Total': [f"{x*100:.2f}%" for x in result['expiring_rent_percents']]
    })
    print(df.to_string(index=False))

    # Building value table by year
    print("=== BUILDING VALUE BY YEAR @ CAP RATE ===")
    value_df = pd.DataFrame({
        'Year': list(range(start_year + 1, start_year + years + 1 )),
        'Value ($)': [f"${v:,.0f}" for v in result['values']],
        'Value per SF ($/SF)': [f"${psf:,.2f}" for psf in result['value_psfs']]
    })
    print(value_df.to_string(index=False))

    # Sensitivity table: cap rate +/- 0.25%
    print("=== CAP RATE SENSITIVITY (±0.25%) ===")
    cap_rates = [cap_rate - 0.0025, cap_rate, cap_rate + 0.0025]
    sensitivity_data = []
    for cr in cap_rates:
        noi_y1 = result['nois'][0]
        value = noi_y1 / cr
        value_psf = value / result['total_sqft']
        sensitivity_data.append([f"{cr*100:.2f}%", f"${noi_y1:,.0f}", f"${value:,.0f}", f"${value_psf:,.2f}"])

    sensitivity_df = pd.DataFrame(sensitivity_data, columns=["Cap Rate", "NOI (Year 1)", "Value", "Value per SF"])
    print(sensitivity_df.to_string(index=False))





import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from openpyxl.styles import numbers, Font, Alignment, Border, Side, PatternFill
from openpyxl.drawing.image import Image
from datetime import datetime

# === Master Table Writer ===
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

def write_master_table(
        ws,
        assumptions_df,
        totals_df,
        result,
        tenants,
        start_year,
        years,
        cap_rate,
        cap_delta,
        total_sqft,
        start_row=6,
        start_col=1
    ):
    """
    Writes a unified table: tenant block, building summary, assumptions, then projections side-by-side.
    """
    thin = Side('thin')
    med = Side('medium')
    header_fill = PatternFill('solid', fgColor='4F81BD')
    subheader_fill = PatternFill('solid', fgColor='D9D9D9')  # Consider a lighter gray or alternate banding for rows

    proj_start = start_col + assumptions_df.shape[1] + 1

   # Move cell_border definition to very top so it's in scope for all table sections
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill('solid', fgColor='4F81BD')
    subheader_fill = PatternFill('solid', fgColor='D9D9D9')

    proj_start = start_col + assumptions_df.shape[1] + 1

   # === Expiring SF and % of property table above projections ===
    exp_sf = []
    exp_pct = []
    for y in range(years):
        current_year = start_year + y
        # Flag based on original expiration (pre-renewal), no offset hack
        sf_flag = sum(
            t.sqft for t in tenants
            if t.original_lease_exp_date.year == current_year + 1
        )
        exp_sf.append(sf_flag)
        exp_pct.append(sf_flag / total_sqft if total_sqft else 0)

    # Write SF row
    row_sf = start_row - 2
    first_sf_cell = ws.cell(row=row_sf, column=proj_start - 1, value="SF Expiring This Year")
    first_sf_cell.font = Font(bold=True)
    first_sf_cell.border = cell_border
    for i, v in enumerate(exp_sf):
        c = ws.cell(row=row_sf, column=proj_start + i, value=v)
        c.alignment = Alignment('center')
        c.border = cell_border

    # Write % row
    row_pct = start_row - 1
    first_pct_cell = ws.cell(row=row_pct, column=proj_start - 1, value="% Expiring This Year")
    first_pct_cell.font = Font(bold=True)
    first_pct_cell.border = cell_border
    for i, v in enumerate(exp_pct):
        c = ws.cell(row=row_pct, column=proj_start + i, value=v)
        c.number_format = '0.00%'
        c.alignment = Alignment('center')
        c.border = cell_border


    sc = start_col

    # Header row
    ws.merge_cells(start_row=start_row, start_column=sc,
                   end_row=start_row, end_column=proj_start-1)
    hdr = ws.cell(row=start_row, column=sc, value="ASSUMPTIONS & TENANCY DETAIL")
    hdr.font = Font(bold=True)
    hdr.fill = header_fill
    hdr.alignment = Alignment('center')
    for i in range(years):
        c = ws.cell(row=start_row, column=proj_start + i, value=str(start_year + i + 1))
        c.font = Font(bold=True);
        c.fill = header_fill;
        c.alignment = Alignment('center');
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Tenant block
    r = start_row + 1
    for j, col in enumerate(assumptions_df.columns, start=sc):
        c = ws.cell(row=r, column=j, value=col)
        c.font = Font(bold=True);
        c.fill = subheader_fill;
        c.alignment = Alignment('center');
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    r += 1
    for idx, row_vals in enumerate(assumptions_df.values.tolist()):
        for j, v in enumerate(row_vals, start=sc):
            c = ws.cell(row=r, column=j, value=v)
            c.alignment = Alignment('center');
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        r += 1
        if idx < len(assumptions_df) - 1:
            r += 1

    # W.A.L.T
    walt_row = r
    cell_walt = ws.cell(row=walt_row, column=sc+4, value="W.A.L.T.")
    cell_walt.font = Font(bold=True);
    cell_walt.border = Border(left=med, right=med, top=med, bottom=med)
    cell_walt_val = ws.cell(
        row=walt_row,
        column=sc+5,
        value=totals_df.loc[totals_df['Label'].str.startswith('W.A.L.T'),'Value'].iloc[0]
    )
    cell_walt_val.alignment = Alignment('center');
    cell_walt_val.border = Border(left=med, right=med, top=med, bottom=med)
    r += 2
    # Building Summary
    sf_str = totals_df.loc[totals_df['Label']=="TOTAL BUILDING RENT:",'Value'].values[0]
    total_sf = int(float(sf_str.replace(',','').split()[0]))
    as_is = totals_df.loc[totals_df['Label']=="TOTAL AS IS RENT:",'Value'].values[0]
    start_r = r; end_r = r+2; sc = start_col; ec = start_col+6
    for lbl in ["TOTAL BUILDING RENT:","VACANT:","OCCUPIED:"]:
        ws.cell(row=r, column=sc, value=lbl).font = Font(bold=True)
        if lbl == "TOTAL BUILDING RENT:":
            ws.cell(row=r, column=sc+1, value=total_sf)
            ws.cell(row=r, column=sc+6, value=as_is)
        else:
            pct_str = totals_df.loc[totals_df['Label']==lbl,'Value'].values[0]
            pct = float(pct_str.strip('%'))
            sf = int(total_sf * pct/100)
            ws.cell(row=r, column=sc+1, value=sf)
            ws.cell(row=r, column=sc+2, value=f"{pct:.1f}%")
        r += 1
    for row in range(start_r, end_r+1):
        ws.cell(row=row, column=sc).border = Border(left=med)
        ws.cell(row=row, column=ec).border = Border(right=med)
    for col in range(sc, ec+1):
        ws.cell(row=start_r, column=col).border = Border(top=med)
        ws.cell(row=end_r, column=col).border = Border(bottom=med)
    r = end_r + 2

    # Additional Assumptions
    extras_start = r  # mark start of metrics block
    extras = [
        ("Market Avg Rate ($/SF)", result['market_avg_rate']),
        ("Market Rent Growth (%)", result['market_growth_pct']*100),
        ("2024 Weighted Avg Rate ($/SF)", result['weighted_avg_rate_2024'])
    ]
    for lbl, val in extras:
        lbl_cell = ws.cell(row=r, column=sc, value=lbl)
        lbl_cell.font = Font(italic=True)
        ws.cell(row=r, column=sc+1, value=val).alignment = Alignment('center')
        r += 1
    r += 1

    # Assumptions roll-up rows
    ws.cell(row=r, column=sc, value="Rental Revenue").font = Font(bold=True)
    ws.cell(row=r, column=sc+6, value=as_is)
    r += 1
    ws.cell(row=r, column=sc, value=f"Expense Revenue (annual increase of {result['market_growth_pct']*100}%)").font = Font(bold=True)
    ws.cell(row=r, column=sc+6, value=result['expense_revenue'][0])
    r += 1
    ws.cell(row=r, column=sc, value="Other Revenue").font = Font(bold=True)
    ws.cell(row=r, column=sc+6, value=0)
    r += 1
    ws.cell(row=r, column=sc, value="Total Gross Revenue").font = Font(bold=True)
    ws.cell(row=r, column=sc+6, value=result['gross_revenue'][0])
    r += 2

    # --- Integrated Expense & NOI using summary_df ---
    summary_df = pd.DataFrame({
        "Label": [
            "OPERATING EXPENSES",
            "OPERATING EXPENSES ($ PSF)",
            "LESS RENTAL VACANCY LOSS",
            "NET OPERATING INCOME"
        ],
        "Year1": [
            result['opex_by_year'][0],
            result['opex_per_sf'][0],
            0,
            result['nois'][0]
        ]
    })
    for label, fmt in [
        ("OPERATING EXPENSES:",            '"($"#,##0_)'),
        ("OPERATING EXPENSES ($ PSF):",    '"$"#,##0.00'),
        ("LESS RENTAL VACANCY LOSS:",      "0.00%"),
        ("NET OPERATING INCOME:",          '"$"#,##0.00')
    ]:
        ws.cell(row=r, column=sc, value=label).font = Font(bold=True)
        val = summary_df.loc[summary_df['Label'] == label.rstrip(':'), 'Year1'].iloc[0]
        cell = ws.cell(row=r, column=sc+6, value=val)
        cell.alignment = Alignment(horizontal='right')
        cell.number_format = fmt
        r += 1

                # Apply outline border around metrics block
    extras_end = r - 1
    thin = Side('thin')
    # Loop through the metrics block and set border only on outer edges
    for row_b in range(extras_start, extras_end + 1):
        for col_b in range(sc, sc + 7):
            sides = {}
            if row_b == extras_start:
                sides['top'] = thin
            if row_b == extras_end:
                sides['bottom'] = thin
            if col_b == sc:
                sides['left'] = thin
            if col_b == sc + 6:
                sides['right'] = thin
            if sides:
                cell = ws.cell(row=row_b, column=col_b)
                cell.border = Border(**sides)

# === Projection Tables ===# === Projection Tables ===
    proj_labels = []
    proj_values = []

# === Projection Tables ===
    # Initialize roll-up labels for projection roll-ups
    roll_labels = ["Rental Revenue"]
    proj_values = []
    for t in tenants:
        proj_labels.extend([f"{t.name} Rent", f"{t.name} Rate"]);
        proj_values.extend([t.projected_rents, t.projected_rates_psf])
    proj_labels.append("Avg Rate/SF"); proj_values.append(result['avg_rates'])


  # Roll-ups with market rows = ["Rental Revenue"]
    roll_vals = [result['rental_revenue']]
    years_list = list(range(years))
    market_rates = [result['market_avg_rate'] * ((1 + result['market_growth_pct']) ** i) for i in years_list]
    market_growths = [result['market_growth_pct']] * years
    weighted_rates = [result['weighted_avg_rate_2024'] * ((1 + result['market_growth_pct']) ** i) for i in years_list]
    roll_labels += ["Market Avg Rate ($/SF)", "Market Rent Growth (%)", "2024 Weighted Avg Rate ($/SF)"]
    roll_vals += [market_rates, market_growths, weighted_rates]
    # Repeat Rental Revenue here as requested
    roll_labels += ["Rental Revenue", "Expense Revenue (2.5% yr)", "Other Revenue", "Total Gross Revenue"]
    roll_vals += [result['rental_revenue'], result['expense_revenue'], [0] * years, result['gross_revenue']]

    value_labels = ["Value of Building", "PPSF"]
    value_vals = [result['values'], result['value_psfs']]

             # Write projection section
    rr = 8
    # Year labels under calendar year header
    for i in range(years):
        yl = ws.cell(row=rr-1, column=proj_start + i, value=f"Year {i+1}")
        yl.font      = Font(bold=True, underline='single')
        yl.alignment = Alignment('center')
        yl.border    = Border(left=thin, right=thin, top=thin, bottom=thin)

            # Tenant rents, rates, and average rate
    for label, vals in zip(proj_labels, proj_values):
        cell = ws.cell(row=rr, column=proj_start-1, value=label)
        # Highlight rates and Opex per SF in red
        if label.endswith("Rate") or label == "Avg Rate/SF":
            cell.font = Font(bold=True, color="FF0000")
        else:
            cell.font = Font(bold=True)



        for i, v in enumerate(vals):
            c = ws.cell(row=rr, column=proj_start+i, value=v)
            c.alignment = Alignment('center')
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            # Apply red font to projection values for those same labels
            if label == "Operating Expenses ($ PSF):" or label.endswith("Rate") or label == "Avg Rate/SF":
                c.font = Font(bold=True, color="FF0000")
            if isinstance(v, (int, float)):
                c.number_format = '"$"#,##0.00'
        rr += 1

# After Avg Rate/SF, write Rental Revenue row
    ws.cell(row=rr, column=proj_start-1, value=roll_labels[0]).font = Font(bold=True)
    for i, v in enumerate(roll_vals[0]):
        c = ws.cell(row=rr, column=proj_start+i, value=v)
        c.alignment = Alignment('center')
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        c.number_format = '"$"#,##0.00'
    rr += 1
    # three blank rows after Rental Revenue
    rr += 3

            # Now write remaining roll-up rows: Market Avg Rate, Market Rent Growth, 2024 Weighted Avg Rate,
    # Expense Revenue, Other Revenue, Total Gross Revenue
    for label, vals in zip(roll_labels[1:], roll_vals[1:]):
        cell = ws.cell(row=rr, column=proj_start-1, value=label)
        cell.font = Font(bold=True)
        for i, v in enumerate(vals):
            c = ws.cell(row=rr, column=proj_start+i, value=v)
            c.alignment = Alignment('center')
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)

            # Apply red font to Operating Expenses per SF projection values
            if label == "Operating Expenses ($ PSF):":
                c.font = Font(bold=True, color="FF0000")
            if label == "Market Rent Growth (%)":
                c.number_format = "0.00%"
            else:
                c.number_format = '"$"#,##0.00'
        rr += 1
        # Insert blank row after Weighted Avg Rate ($/SF)
        if label == "2024 Weighted Avg Rate ($/SF)":
            rr += 1
        if label == "Total Gross Revenue":
            rr += 1

               # Expense and NOI sections
    for label, vals in zip(
        ["Operating Expenses:", "Operating Expenses ($ PSF):", "Less Vacancy Loss:", "Net Operating Income:"],
        
        [
            [round(x, 2) for x in result['opex_by_year']],
            [round(x, 2) for x in result['opex_per_sf']],
            [0] * years,
            result['nois']
        ]
    ):
        cell = ws.cell(row=rr, column=proj_start-1, value=label)
        # Only color label for expense per SF or total expense
        if label == "Operating Expenses ($ PSF):" or label == "Operating Expenses:":
            cell.font = Font(bold=True, color="FF0000")

        for i, v in enumerate(vals):
            c = ws.cell(row=rr, column=proj_start+i, value=v)
            c.alignment = Alignment('center')
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            # Color and format value cells
            if label == "Operating Expenses ($ PSF):":
                c.font = Font(bold=True, color="FF0000")
                c.number_format = '"$"#,##0.00'
            elif label == "Operating Expenses:":
                c.font = Font(bold=True, color="FF0000")
                c.number_format = '"$"#,##0.00'
        rr += 1

    # Year labels in Value table header
    for i in range(years):
        yl = ws.cell(row=rr, column=proj_start + i, value=f"Year {i+1}")
        yl.font      = Font(bold=True, underline='single')
        yl.alignment = Alignment('center')
        yl.border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    rr += 1
    for label, vals in zip(value_labels, value_vals):
        cell = ws.cell(row=rr, column=proj_start-1, value=label)
        cell.font = Font(bold=True)
        for i, v in enumerate(vals):
            c = ws.cell(row=rr, column=proj_start+i, value=v)
            c.alignment = Alignment('center')
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            c.number_format = "#,##0.00"
        rr += 1

     # === Cap Rate Sensitivity Table ===
    sensitivity_col = start_col
    # Define border style for all cells
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Header row for sensitivity section
    hdr = ws.cell(row=rr, column=sensitivity_col,
                  value=f"CAP RATE SENSITIVITY (±{cap_delta*100:.2f}%)")
    hdr.font = Font(bold=True)
    hdr.border = cell_border
    rr += 1

    # Column headings
    for j, h in enumerate(["Cap Rate", "NOI", "Value", "$/Foot"]):
        c = ws.cell(row=rr, column=sensitivity_col + j, value=h)
        c.font = Font(bold=True)
        c.alignment = Alignment('center')
        c.border = cell_border
    rr += 1

    # Data rows: shade rows alternating light/dark/light green
    light_green = PatternFill('solid', fgColor='C6EFCE')  # light green
    dark_green  = PatternFill('solid', fgColor='00B050')  # darker green
    for idx, delta in enumerate((-cap_delta, 0, cap_delta)):
        cr = cap_rate + delta
        noi = result['nois'][0]
        val = noi / cr
        ppsf = val / total_sqft
        # Choose fill color: light for first and third, dark for second
        fill = light_green if idx in (0, 2) else dark_green
        for j, v in enumerate([f"{cr*100:.2f}%", noi, val, ppsf]):
            cell = ws.cell(row=rr, column=sensitivity_col + j, value=v)
            cell.alignment = Alignment('center')
            cell.border = cell_border
            cell.fill = fill
            # Number formats
            if j == 0:
                cell.number_format = "0.00%"
            elif j in (1, 2):
                cell.number_format = '"$"#,##0'
            else:
                cell.number_format = '"$"#,##0.00'
        rr += 1


# === Add borders to all title cells in column H ===
    title_col = start_col + 7  # Column H
    for row_idx in range(start_row, rr):
        title_cell = ws.cell(row=row_idx, column=title_col)
        if title_cell.value is not None:
            title_cell.border = cell_border

# === Export Function ===
# Final export function definition
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

def export_projections_format(
    building_name,
    assumptions_df,
    totals_df,
    result,
    tenants,
    cap_rate,
    cap_delta,
    total_sqft
):
    wb = Workbook()
    ws = wb.active
    ws.title = "Proforma Output"

    # 1) Title & header
    years = len(result['rental_revenue'])
    col_end = 1 + assumptions_df.shape[1] + years
    ws.merge_cells(start_row=1, start_column=1, end_row=3, end_column=col_end)
    t = ws.cell(row=1, column=1, value=f"{building_name} Pro-Forma / Rent Roll")
    t.font = Font(size=18, bold=True)
    t.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    t.alignment = Alignment(horizontal="center", vertical="center")

    # 2) Pull WALT from totals_df
    raw_walt = totals_df.loc[totals_df['Label']=="W.A.L.T. (yrs)", 'Value'].iloc[0]
    # leave as string (e.g. "24.00") so we preserve formatting

    # 3) Master table (which now uses the updated assumptions & WALT internally)
    write_master_table(
        ws,
        assumptions_df,
        totals_df,
        result,
        tenants,
        result['start_year'],
        years,
        cap_rate,
        cap_delta,
        total_sqft
    )

    # 5) Auto‐fit columns
    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 2

    # 6) Save
    filename = f"{building_name.replace(' ', '_')}_Proforma.xlsx"
    wb.save(filename)
    print(f"Saved {filename}")

# === Main Execution ===
if __name__ == "__main__":
    building_name, tenants, total_sqft, occupied_sqft, total_rent, \
    opex_psf, growth_rate, cap_rate, cap_delta, market_avg_rate, \
    market_growth_pct, start_year, start_month, years = collect_input()

    # regenerate assumptions (with correct WALT logic)
    assumptions_df, totals_df = generate_assumptions_table(
        tenants, total_sqft, occupied_sqft, start_year, start_month
    )

    # calculate projections
    result = calculate_proforma(
        total_rent, opex_psf, growth_rate, cap_rate,
        tenants, market_avg_rate, market_growth_pct,
        start_year, years
    )

    # show on terminal
    raw_walt = totals_df.loc[totals_df['Label']=="W.A.L.T. (yrs)", 'Value'].iloc[0]
    display_assumptions(assumptions_df, totals_df, float(raw_walt))
    display_output(result, cap_rate)

    # write to Excel (including explicit WALT stamp)
    export_projections_format(
        building_name,
        assumptions_df,
        totals_df,
        result,
        tenants,
        cap_rate,
        cap_delta,
        total_sqft
    )
