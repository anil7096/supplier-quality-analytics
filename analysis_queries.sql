-- name: supplier_ppm
-- Defect PPM and lot rejection rate per supplier (PPM = defects / inspected pieces * 1,000,000)
SELECT s.supplier_id, s.supplier_name,
       COUNT(*) AS lots,
       SUM(l.sample_size) AS pieces_inspected,
       SUM(l.defects_found) AS defects,
       ROUND(1000000.0 * SUM(l.defects_found) / SUM(l.sample_size)) AS ppm,
       ROUND(100.0 * SUM(l.disposition = 'Rejected') / COUNT(*), 1) AS lot_reject_pct,
       ROUND(100.0 * SUM(l.days_late = 0) / COUNT(*), 1) AS on_time_pct
FROM lots l JOIN suppliers s USING (supplier_id)
GROUP BY s.supplier_id ORDER BY ppm DESC;

-- name: defect_pareto
SELECT defect_type, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM defects), 1) AS pct
FROM defects GROUP BY defect_type ORDER BY n DESC;

-- name: category_ppm
SELECT p.category, ROUND(1000000.0 * SUM(l.defects_found) / SUM(l.sample_size)) AS ppm, COUNT(*) AS lots
FROM lots l JOIN parts p USING (part_id) GROUP BY p.category ORDER BY ppm DESC;

-- name: monthly_ppm
SELECT strftime('%Y-%m', receipt_date) AS month,
       ROUND(1000000.0 * SUM(defects_found) / SUM(sample_size)) AS ppm,
       COUNT(*) AS lots
FROM lots GROUP BY month ORDER BY month;

-- name: car_response
SELECT s.supplier_name, COUNT(*) AS cars, ROUND(AVG(c.response_days), 1) AS avg_response_days
FROM corrective_actions c JOIN suppliers s USING (supplier_id)
GROUP BY s.supplier_id HAVING cars >= 2 ORDER BY avg_response_days DESC;

-- name: cobra_before_after
SELECT CASE WHEN receipt_date >= '2026-04-01' THEN 'After corrective action' ELSE 'Before' END AS period,
       ROUND(1000000.0 * SUM(defects_found) / SUM(sample_size)) AS ppm, COUNT(*) AS lots
FROM lots WHERE supplier_id = (SELECT supplier_id FROM suppliers WHERE supplier_name = 'Cobra Fasteners')
GROUP BY period;

-- name: cost_of_poor_quality
-- Rough exposure: defective share of lot qty x unit cost, for rejected/sorted lots
SELECT s.supplier_name,
       ROUND(SUM(1.0 * l.defects_found / l.sample_size * l.lot_qty * p.unit_cost_inr)) AS est_defect_value_inr
FROM lots l JOIN suppliers s USING (supplier_id) JOIN parts p USING (part_id)
WHERE l.disposition IN ('Rejected','Sorted/Rework')
GROUP BY s.supplier_id ORDER BY est_defect_value_inr DESC LIMIT 5;
