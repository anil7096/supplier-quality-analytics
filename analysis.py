"""Load CSVs into SQLite, run the SQL, build scorecard + charts."""
import re, sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; D, O = ROOT/"data", ROOT/"outputs"
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e6e5e1"
plt.rcParams.update({"font.family":"DejaVu Sans","axes.edgecolor":GRID,"axes.labelcolor":MUTED,
  "xtick.color":MUTED,"ytick.color":MUTED,"axes.spines.top":False,"axes.spines.right":False,
  "axes.grid":True,"grid.color":GRID,"axes.axisbelow":True,"figure.dpi":150})

con = sqlite3.connect(":memory:")
for t in ["suppliers","parts","lots","defects","corrective_actions"]:
    pd.read_csv(D/f"{t}.csv").to_sql(t, con, index=False)
q = {m.group(1): m.group(2) for m in re.finditer(r"-- name: (\w+)\n(.*?)(?=\n-- name:|\Z)", (ROOT/"sql/analysis_queries.sql").read_text(), re.S)}
R = {k: pd.read_sql(v, con) for k, v in q.items()}
for k, v in R.items(): v.to_csv(O/f"{k}.csv", index=False)

# ---- weighted supplier scorecard (quality 50, delivery 30, responsiveness 20)
sc = R["supplier_ppm"].merge(pd.read_sql("SELECT supplier_id, AVG(response_days) r FROM corrective_actions GROUP BY supplier_id", con), on="supplier_id", how="left")
sc["r"] = sc["r"].fillna(sc["r"].median())
q_score = (1 - (sc.ppm.clip(upper=40000) / 40000)) * 100       # 0 PPM = 100, >=40k PPM = 0
d_score = sc.on_time_pct
r_score = (1 - (sc.r.clip(upper=25) / 25)) * 100
sc["score"] = (0.5*q_score + 0.3*d_score + 0.2*r_score).round(1)
sc["rating"] = pd.cut(sc.score, [-1, 70, 85, 101], labels=["C - Probation","B - Watch","A - Preferred"])
sc = sc.sort_values("score", ascending=False)
sc.rename(columns={"r":"avg_car_response_days"}).round(1).to_csv(O/"supplier_scorecard.csv", index=False)

# ---- chart 1: PPM by supplier
s = R["supplier_ppm"].sort_values("ppm")
fig, ax = plt.subplots(figsize=(8, 5.5))
cols = [ORANGE if v > s.ppm.median()*2 else BLUE for v in s.ppm]
ax.barh(s.supplier_name, s.ppm, color=cols, height=.6)
for y, v in enumerate(s.ppm): ax.text(v + 300, y, f"{int(v):,}", va="center", fontsize=7.5, color=INK)
ax.set_xlabel("Defect PPM (sampled pieces)"); ax.grid(axis="y", visible=False)
ax.set_title("Three suppliers sit far above the rest on defect PPM", loc="left", color=INK, fontsize=11)
fig.tight_layout(); fig.savefig(O/"01_supplier_ppm.png"); plt.close()

# ---- chart 2: Pareto of defect types
p = R["defect_pareto"]; p["cum"] = p.pct.cumsum()
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(p.defect_type, p.n, color=BLUE, width=.6); ax.set_ylabel("Defects")
ax.tick_params(axis="x", rotation=40); [t.set_ha("right") for t in ax.get_xticklabels()]
ax2 = ax.twinx(); ax2.plot(p.defect_type, p.cum, color=ORANGE, marker="o", lw=2)
ax2.set_ylim(0, 105); ax2.set_ylabel("Cumulative %"); ax2.grid(False); ax2.spines["right"].set_visible(False)
ax.set_title("Pareto: a handful of defect types drive most rejects", loc="left", color=INK, fontsize=11)
fig.tight_layout(); fig.savefig(O/"02_defect_pareto.png"); plt.close()

# ---- chart 3: monthly PPM trend
m = R["monthly_ppm"]
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(m.month, m.ppm, color=BLUE, lw=2); ax.set_xticks(m.month[::3]); ax.tick_params(axis="x", rotation=45)
ax.axhline(m.ppm.mean(), color=MUTED, ls="--", lw=1); ax.text(0, m.ppm.mean()*1.03, "average", color=MUTED, fontsize=8)
ax.set_ylabel("PPM"); ax.set_title("Monthly incoming PPM (all suppliers)", loc="left", color=INK, fontsize=11)
fig.tight_layout(); fig.savefig(O/"03_monthly_ppm.png"); plt.close()

# ---- chart 4: p-chart for worst supplier
worst = R["supplier_ppm"].iloc[0]
L = pd.read_sql(f"SELECT receipt_date, defects_found d, sample_size n FROM lots WHERE supplier_id='{worst.supplier_id}' ORDER BY receipt_date", con)
L["p"] = L.d / L.n; pbar = L.d.sum() / L.n.sum()
L["ucl"] = pbar + 3*np.sqrt(pbar*(1-pbar)/L.n); L["lcl"] = (pbar - 3*np.sqrt(pbar*(1-pbar)/L.n)).clip(lower=0)
out = L.p > L.ucl
fig, ax = plt.subplots(figsize=(8, 4))
x = range(len(L)); ax.plot(x, L.p*100, color=BLUE, lw=1.2, marker="o", ms=3)
ax.step(x, L.ucl*100, color=ORANGE, lw=1, where="mid"); ax.axhline(pbar*100, color=MUTED, lw=1)
ax.scatter(np.array(x)[out], L.p[out]*100, color=ORANGE, zorder=3, s=22, edgecolor="white", linewidth=1)
ax.set_xlabel("Lot sequence"); ax.set_ylabel("Defective % in sample")
ax.text(len(L)-1, pbar*100+.25, "mean", color=MUTED, fontsize=8, ha="right"); ax.text(len(L)-1, L.ucl.iloc[-1]*100+.25, "upper limit (3-sigma)", color=ORANGE, fontsize=8, ha="right")
ax.set_title(f"p-chart: {worst.supplier_name} is stable but at {pbar*100:.1f}% defective ({int(out.sum())} lots above the limit)", loc="left", color=INK, fontsize=10)
fig.tight_layout(); fig.savefig(O/"04_p_chart_worst_supplier.png"); plt.close()

# ---- chart 5: scorecard
fig, ax = plt.subplots(figsize=(8, 5.5))
cm = {"A - Preferred": BLUE, "B - Watch": "#eda100", "C - Probation": ORANGE}
t = sc.sort_values("score")
ax.barh(t.supplier_name, t.score, color=[cm[str(r)] for r in t.rating], height=.6)
for y, v in enumerate(t.score): ax.text(v + .6, y, f"{v:.0f}", va="center", fontsize=7.5, color=INK)
ax.set_xlim(0, 105); ax.grid(axis="y", visible=False); ax.set_xlabel("Weighted score (quality 50 / delivery 30 / responsiveness 20)")
ax.legend(handles=[plt.Rectangle((0,0),1,1,color=c) for c in cm.values()], labels=list(cm), loc="lower right", frameon=False, fontsize=8)
ax.set_title("Supplier scorecard", loc="left", color=INK, fontsize=11)
fig.tight_layout(); fig.savefig(O/"05_supplier_scorecard.png"); plt.close()

# ---- numbers for the README
print(R["supplier_ppm"].head(4).to_string(index=False)); print(p.head(5).to_string(index=False))
print(R["category_ppm"].to_string(index=False)); print(R["cobra_before_after"].to_string(index=False))
print(R["car_response"].head(3).to_string(index=False)); print(R["cost_of_poor_quality"].to_string(index=False))
print(sc[["supplier_name","score","rating"]].to_string(index=False))
tot = R["supplier_ppm"]; print("overall PPM", round(1e6*tot.defects.sum()/tot.pieces_inspected.sum()), "top3 share of defects", round(100*tot.defects.head(3).sum()/tot.defects.sum(),1))
print(m.sort_values("ppm", ascending=False).head(3).to_string(index=False))
