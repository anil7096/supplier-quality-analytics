# Supplier Incoming-Quality Analytics (SQL + Python)

**Role focus:** Data Analyst / Quality Analytics | **Tools:** Python (pandas, NumPy, matplotlib), SQL (SQLite), p-chart / Pareto / scorecard methods

## Business problem
A manufacturer receives parts from 17 suppliers and inspects samples of every lot on arrival. Management wants to know **which suppliers cause the most quality loss, which defects to attack first, and whether corrective actions work**, so the buyer and quality teams can focus on the few suppliers that matter.

## Data (synthetic, reproducible)
`src/generate_data.py` (seed 42) builds a realistic dataset: 17 suppliers, 16 parts in 6 categories, **1,305 inspected lots** (Nov 2024 - Oct 2026), 1,656 defect records and 62 corrective-action requests. Patterns are planted on purpose (three weak suppliers, a monsoon effect on rubber/plastic parts, one supplier that improves after corrective action) so the analysis has something real to find. Replace the CSVs in `data/` with real inspection data and the same pipeline runs.

## Method
1. Load CSVs into SQLite and answer each question with SQL (`sql/analysis_queries.sql`: joins, aggregates, CASE, subqueries, HAVING, `strftime`).
2. Pareto of defect types, monthly PPM trend, and a **p-chart** (3-sigma, variable sample size) for the worst supplier.
3. **Weighted scorecard**: quality 50% (PPM), delivery 30% (on-time %), responsiveness 20% (corrective-action response days) -> A / B / C rating.

## Key findings (from this dataset)
- Overall defect rate is about **11,300 PPM**. **Horizon Wiring (~42,300 PPM), Cobra Fasteners (~23,900) and Nova Pressings (~22,400)** produce **45% of all defects** from 3 of 17 suppliers.
- Horizon Wiring also has the highest estimated defect value (about INR 11.4 lakh in rejected/sorted lots).
- **Cobra Fasteners' corrective action worked:** PPM fell from ~31,600 to ~10,100 after April 2026. Same method can verify any supplier's action plan.
- **Dimension out of tolerance** is the top defect (23%); the top 5 defect types account for 60% of defects.
- Scorecard puts those three suppliers on **Probation (C)**;  - nine suppliers in the middle, held back by a mix of late deliveries (Eastern Stampings and Kaveri Gaskets are on time only ~76-79%), moderately high PPM (Falcon, Apex, Lotus at 11-12k) or slow corrective-action response.

- **p-chart on Horizon Wiring:** no lot breaches the 3-sigma limit, so the process is stable but sits at about 4.2% defective. Per-lot sample sizes are small, so the chart cannot flag short spikes (such as its Jun-Aug 2025 deterioration, visible in the monthly view). The fix is a process-capability improvement, not lot-by-lot firefighting.

## Recommendations
1. Start supplier development audits with the three C-rated suppliers; require a 30/60/90-day recovery plan.
2. Focus incoming checks and supplier process audits on dimension control, thread and burr defects.
3. Track post-action PPM monthly (the Cobra before/after query) before closing any corrective action.

## Outputs
`outputs/*.png` (5 charts), `outputs/supplier_scorecard.csv`, plus a CSV for every SQL query.

## Run it
```bash
pip install pandas numpy matplotlib
python src/generate_data.py
python src/analysis.py
```

*Note: figures are from synthetic data; the project shows method, not real supplier performance.*
