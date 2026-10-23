"""Generate a synthetic incoming-inspection dataset for 17 suppliers (seeded, reproducible)."""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parents[1] / "data"

# --- suppliers: baseline defect rate (fraction) and on-time delivery probability
sup_names = ["Apex Forge","Bharat Castings","Cobra Fasteners","Deccan Rubber","Eastern Stampings",
             "Falcon Plastics","Giri Springs","Horizon Wiring","Indus Bearings","Jyoti Coatings",
             "Kaveri Gaskets","Lotus Machining","Meridian Seals","Nova Pressings","Orion Fittings",
             "Prime Alloys","Quest Tooling"]
cities = ["Chennai","Hosur","Pune","Bengaluru","Coimbatore","Hyderabad","Sriperumbudur","Aurangabad"]
base_def = rng.uniform(0.002, 0.012, 17)
base_def[[2, 7, 13]] = [0.028, 0.034, 0.022]          # three problem suppliers
ontime = rng.uniform(0.90, 0.99, 17)
ontime[[4, 10]] = [0.71, 0.78]                          # two late suppliers
suppliers = pd.DataFrame({
    "supplier_id": [f"S{i+1:02d}" for i in range(17)], "supplier_name": sup_names,
    "city": rng.choice(cities, 17), "tier": rng.choice(["Tier-1","Tier-2"], 17, p=[.6,.4]),
    "years_with_company": rng.integers(1, 15, 17)})

# --- parts
cats = {"Stamped":["Bracket","Panel","Reinforcement"], "Machined":["Shaft","Housing","Gear blank"],
        "Rubber/Plastic":["Seal","Gasket","Clip"], "Electrical":["Harness","Connector"],
        "Fastener":["Bolt","Nut","Washer"], "Spring":["Coil spring","Clutch spring"]}
rows = [(c, p) for c, ps in cats.items() for p in ps]
parts = pd.DataFrame(rows, columns=["category","part_name"])
parts.insert(0, "part_id", [f"P{i+1:03d}" for i in range(len(parts))])
parts["unit_cost_inr"] = rng.integers(8, 900, len(parts))
# each supplier supplies 3-5 parts
sp_map = {s: rng.choice(parts.part_id, rng.integers(3, 6), replace=False) for s in suppliers.supplier_id}

defect_types = {"Stamped":["Burr","Dimension out of tolerance","Crack","Surface scratch"],
 "Machined":["Dimension out of tolerance","Surface finish","Burr","Thread damage"],
 "Rubber/Plastic":["Flash","Short shot","Dimension out of tolerance","Colour variation"],
 "Electrical":["Loose crimp","Wrong connector","Insulation damage","Continuity fail"],
 "Fastener":["Thread damage","Plating defect","Dimension out of tolerance","Wrong grade"],
 "Spring":["Load out of spec","Free-length error","Rust","Dimension out of tolerance"]}

# --- lots: 24 months, ~ 3 lots / supplier / month
dates = pd.date_range("2024-11-01", "2026-10-15", freq="D")
lot_rows, defect_rows, lid = [], [], 1
for si, s in suppliers.iterrows():
    for d in dates:
        if rng.random() > 0.11: continue
        pid = rng.choice(sp_map[s.supplier_id]); cat = parts.loc[parts.part_id == pid, "category"].iloc[0]
        qty = int(rng.choice([500, 1000, 2000, 5000]))
        sample = {500: 50, 1000: 80, 2000: 125, 5000: 200}[qty]
        rate = base_def[si]
        # planted patterns: Cobra improves after corrective action (Apr-2026); Horizon spike Jun-Aug 2025;
        # Nova bad on Electrical-like rubber? -> just persistently high; monsoon bump for Rubber/Plastic
        if s.supplier_name == "Cobra Fasteners" and d >= pd.Timestamp("2026-04-01"): rate *= 0.35
        if s.supplier_name == "Horizon Wiring" and pd.Timestamp("2025-06-01") <= d <= pd.Timestamp("2025-08-31"): rate *= 2.0
        if cat == "Rubber/Plastic" and d.month in (6, 7, 8, 9): rate *= 1.4
        defects = int(rng.binomial(sample, min(rate, 0.5)))
        accept_no = {50: 1, 80: 2, 125: 3, 200: 5}[sample]
        disp = "Accepted" if defects <= accept_no else rng.choice(["Rejected","Sorted/Rework","Deviation accepted"], p=[.5,.35,.15])
        late = rng.random() > ontime[si]
        lot_rows.append((f"L{lid:05d}", d.date(), s.supplier_id, pid, qty, sample, defects, disp,
                         int(rng.integers(1, 6)) if late else 0))
        for _ in range(defects):
            defect_rows.append((f"L{lid:05d}", rng.choice(defect_types[cat], p=[.38,.30,.20,.12])))
        lid += 1
lots = pd.DataFrame(lot_rows, columns=["lot_id","receipt_date","supplier_id","part_id","lot_qty",
        "sample_size","defects_found","disposition","days_late"])
defects = pd.DataFrame(defect_rows, columns=["lot_id","defect_type"])
# --- corrective-action requests: raised for rejected lots, response time varies by supplier
car = lots[lots.disposition == "Rejected"][["lot_id","supplier_id","receipt_date"]].copy()
car["response_days"] = (rng.gamma(3, 2.2, len(car)) * np.where(car.supplier_id.isin(["S05","S11"]), 1.8, 1)).round().astype(int).clip(1, 45)
suppliers.to_csv(OUT/"suppliers.csv", index=False); parts.to_csv(OUT/"parts.csv", index=False)
lots.to_csv(OUT/"lots.csv", index=False); defects.to_csv(OUT/"defects.csv", index=False)
car.to_csv(OUT/"corrective_actions.csv", index=False)
print({k: len(v) for k, v in dict(suppliers=suppliers, parts=parts, lots=lots, defects=defects, car=car).items()})
