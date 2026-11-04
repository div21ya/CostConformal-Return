#!/usr/bin/env python3
"""Build File 12 as a self-contained Word document using only Python's standard library."""
from __future__ import annotations

import csv
import shutil
import struct
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
OUT = ROOT / "12_comprehensive_project_report.docx"

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"

def tag(name: str, body: str = "", attrs: str = "") -> str:
    return f"<w:{name}{attrs}>{body}</w:{name}>"

def run(text: str, bold: bool = False, italic: bool = False, size: int | None = None, colour: str | None = None) -> str:
    props = ""
    if bold: props += "<w:b/>"
    if italic: props += "<w:i/>"
    if size: props += f'<w:sz w:val="{size}"/>'
    if colour: props += f'<w:color w:val="{colour}"/>'
    return f"<w:r><w:rPr>{props}</w:rPr><w:t xml:space=\"preserve\">{escape(str(text))}</w:t></w:r>"

def para(text: str = "", style: str | None = None, bold: bool = False, italic: bool = False,
         align: str | None = None, size: int | None = None, colour: str | None = None) -> str:
    ppr = ""
    if style: ppr += f'<w:pStyle w:val="{style}"/>'
    if align: ppr += f'<w:jc w:val="{align}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{run(text, bold, italic, size, colour)}</w:p>"

def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

def table(rows: list[list[str]], widths: list[int] | None = None) -> str:
    if not rows: return para("No output available.", italic=True)
    cols = max(len(r) for r in rows)
    widths = widths or [9000 // cols] * cols
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    xml = '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>' + ''.join(
        f'<w:{edge} w:val="single" w:sz="4" w:color="B7C7D9"/>' for edge in ["top","left","bottom","right","insideH","insideV"]
    ) + '</w:tblBorders></w:tblPr><w:tblGrid>' + grid + '</w:tblGrid>'
    for ridx, row in enumerate(rows):
        cells = ""
        for i in range(cols):
            value = row[i] if i < len(row) else ""
            shade = '<w:shd w:fill="1F4E78"/>' if ridx == 0 else ""
            p = f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{run(value, bold=ridx == 0, size=17 if ridx == 0 else 16, colour="FFFFFF" if ridx == 0 else None)}</w:p>'
            cells += f'<w:tc><w:tcPr><w:tcW w:w="{widths[min(i, len(widths)-1)]}" w:type="dxa"/>{shade}</w:tcPr>{p}</w:tc>'
        xml += f'<w:tr>{cells}</w:tr>'
    return xml + '</w:tbl>'

def read_csv(name: str, columns: list[str] | None = None, limit: int | None = None, percent: set[str] | None = None) -> list[list[str]]:
    path = TABLES / name
    if not path.exists(): return [["Output", "Status"], [name, "Not available"]]
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        data = list(reader)
        headers = reader.fieldnames or []
    cols = columns or (list(data[0]) if data else headers)
    if not cols:
        return [["Output", "Status"], [name, "Empty result: no rows met this diagnostic criterion"]]
    def format_value(c: str, v: str) -> str:
        if c in (percent or set()):
            try: return f"{float(v) * 100:.2f}%"
            except ValueError: return v
        if c in {"auc", "pr_auc", "brier", "log_loss", "tau", "psi", "ks_statistic", "js_divergence"}:
            try: return f"{float(v):.4f}"
            except ValueError: return v
        if c.startswith("n_") or c in {"rows", "events", "returns", "returned", "retained", "train_n", "val_n", "n_eval", "n", "event_rows"}:
            try: return f"{int(float(v)):,}"
            except ValueError: return v
        return v
    out = [[c.replace("_", " ") for c in cols]]
    for row in data[:limit]: out.append([format_value(c, row.get(c, "")) for c in cols])
    return out

def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    return struct.unpack(">II", header[16:24])

images: list[tuple[Path, str]] = []
def picture(path: Path, caption: str) -> str:
    if not path.exists(): return para(f"Figure unavailable: {caption}", italic=True)
    idx = len(images) + 1
    images.append((path, f"rId{idx+1}"))
    width, height = png_size(path)
    max_width = 5_900_000
    ratio = min(max_width / width, 4_400_000 / height)
    cx, cy = int(width * ratio), int(height * ratio)
    drawing = f'''<w:drawing><wp:inline xmlns:wp="{WP}" distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{idx}" name="Figure {idx}" descr="{escape(caption)}"/>
<a:graphic xmlns:a="{DRAWING}"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="{PIC}">
<pic:nvPicPr><pic:cNvPr id="0" name="{path.name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId{idx+1}" xmlns:r="{REL}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>'''
    return f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r>{drawing}</w:r></w:p>' + para(caption, italic=True, align="center", size=18)

def heading(n: int, text: str) -> str:
    return para(text, style=f"Heading{n}")

doc: list[str] = []
doc += [para("COSTCONFORMAL-RETURN", bold=True, size=44, colour="1F4E78", align="center"),
        para("Comprehensive Project Report", bold=True, size=32, align="center"),
        para("Calibrated machine learning and Conformal Risk Control for value-sensitive e-commerce return intervention", italic=True, size=22, align="center"),
        para("", size=18),
        para("Team Member 1 — Registration No.: [INSERT REGISTRATION NUMBER]", align="center"),
        para("Team Member 2 — Registration No.: [INSERT REGISTRATION NUMBER]", align="center"),
        para("Team Member 3 — Registration No.: [INSERT REGISTRATION NUMBER]", align="center"),
        para(f"Date: {date.today().strftime('%d %B %Y')}", align="center"), page_break()]

doc += [heading(1, "Abstract"),
        para("CostConformal-Return converts an e-commerce return-prediction task into a value-sensitive intervention policy. The project validates and joins event, customer and product data; applies leakage-safe preprocessing and exploratory analysis; trains a diverse machine-learning model zoo; tunes leading models; and calibrates their probabilities. Conformal Risk Control (CRC) then selects an intervention threshold for a user-selected risk target. The controlled outcome is value-weighted missed-return exposure, rather than a simple false-negative count. The final work evaluates global and category-aware CRC, subgroup burden, future-period drift, calibration and paired-bootstrap comparisons between XGBoost and Elastic-Net. The result is not only a predictive model, but an operationally meaningful and auditable decision policy."),
        heading(1, "1. Introduction"),
        para("E-commerce returns generate reverse-logistics cost and affect inventory availability. A conventional classifier predicts whether an order may be returned, but a deployable decision system must also produce calibrated probabilities, account for order value, define a transparent intervention threshold and demonstrate robustness outside the development data."),
        para("Research question: Can calibrated machine-learning probabilities be transformed into an intervention policy that controls value-weighted missed-return exposure at a chosen target level?", bold=True),
        para("The project is organised into three phases: Phase 1 covers validation, leakage-safe joins, preprocessing, EDA and baseline CRC; Phase 2 covers feature engineering, database connectivity, model-zoo training and tuning; Phase 3 performs final calibration, CRC policy assessment, subgroup/drift audits and statistical comparison."),
        heading(1, "2. Dataset Description"),
        para("The ASOS benchmark contains event-level observations linked to customer and product nodes for official training and future-test periods. The binary target is isReturned. Return-reason ratio fields are excluded to avoid post-outcome leakage. The pipeline keeps missingness indicators and fits preprocessing transformations only on training data."),
        table(read_csv("01_dataset_validation_summary.csv", ["split","event_rows","customers","variants","return_count","return_rate"], percent={"return_rate"})),
        para("Table 1. Official dataset validation summary.", italic=True, align="center"),
        table(read_csv("02_join_audit.csv", ["split","rows","customer_match_rate","product_match_rate","complete_match_rate"], percent={"customer_match_rate","product_match_rate","complete_match_rate"})),
        para("Table 2. Customer and product join audit.", italic=True, align="center"),
        table(read_csv("03_split_summary.csv", ["analysis_split","rows","returned","retained","return_rate","price_available_rate"], percent={"return_rate","price_available_rate"})),
        para("Table 3. Leakage-safe split summary.", italic=True, align="center"),
        heading(1, "3. EDA and Visualisations"),
        para("The descriptive analysis establishes that return prevalence is near 55%, while return behaviour varies across product types, customer history and discount regimes. This heterogeneity supports nonlinear modelling and category-aware policy assessment. The future period is assessed separately because similar prevalence alone cannot guarantee stable calibrated-risk performance.")]

eda_figures = [
    ("01_return_class_distribution.png", "Figure 1. Return class distribution.", "Inference: returns form a substantial share of events, close to 55%, so this is not an extreme rarity problem. Probability quality and the cost of missed returns are therefore more informative than accuracy alone."),
    ("02_product_price_by_return_outcome.png", "Figure 2. Product price by return outcome.", "Inference: price distributions overlap across outcomes, so price should not be treated as a standalone rule. It is valuable when combined with customer and product history, and it supports the value-weighted exposure objective."),
    ("03_return_rate_by_product_type.png", "Figure 3. Return rate by product type.", "Inference: return probability differs strongly by product category. This validates retaining product type as a feature and motivates the category-aware CRC thresholds used later in the policy."),
    ("04_customer_history_density.png", "Figure 4. Customer history distribution by outcome.", "Inference: the customer-history distributions differ by outcome, showing that prior customer activity and prior returns carry predictive signal beyond the current order."),
    ("05_discount_ratio_vs_return_rate.png", "Figure 5. Discount ratio and observed return rate.", "Inference: return behaviour changes across discount levels, but the relationship is not sufficient by itself for a fixed business rule. Discount is therefore used with other covariates in the learned models."),
    ("08_return_rate_by_official_period.png", "Figure 6. Return rate by official period.", "Inference: the future-period return rate differs slightly from training. Even a small aggregate change makes temporal testing necessary because calibration and policy risk can change without a dramatic prevalence shift.")
]
for fig, cap, insight in eda_figures:
    doc += [picture(FIGURES / fig, cap), para(insight, italic=True, colour="365F91")]

doc += [table(read_csv("09_return_rate_by_product_type.csv", ["productType","events","returns","return_rate","ci_lower","ci_upper"], limit=15, percent={"return_rate","ci_lower","ci_upper"})),
        para("Table 4. Product-type return rates with confidence intervals.", italic=True, align="center"),
        heading(1, "4. Statistical Analysis"),
        para("Descriptive statistics cover class distribution, price/outcome summaries, customer histories, product-type rates, discount bins and period rates. Preprocessing reports document missingness before/after treatment, categorical encoding and numeric normalisation. Wilson confidence intervals quantify uncertainty in intervention workload, while paired bootstrap intervals compare final policy outcomes on matched observations."),
        table(read_csv("13_missingness_before.csv", limit=20, percent={"missing_rate"})),
        para("Table 5. Missingness before preprocessing.", italic=True, align="center"),
        table(read_csv("14_missingness_after.csv", limit=20, percent={"missing_rate"})),
        para("Table 6. Missingness after preprocessing.", italic=True, align="center"),
        table(read_csv("s10_01_wilson_ci_intervention_rate.csv", ["model_id","alpha","tau","n_intervened","n","rate","ci_low","ci_high"], percent={"rate","ci_low","ci_high"})),
        para("Table 7. Wilson 95% confidence intervals for intervention rate.", italic=True, align="center"),
        table(read_csv("s10_04_significance_summary.csv", ["split","metric","alpha","xgboost_value","elastic_net_value","mean_diff","diff_ci_low","diff_ci_high","significant"], limit=20, percent={"xgboost_value","elastic_net_value","mean_diff","diff_ci_low","diff_ci_high"})),
        para("Table 8. Statistical-significance summary from paired bootstrap comparison.", italic=True, align="center"),
        para("Inference: neither finalist is universally preferred at every risk target. The better policy depends on the acceptable residual risk and intervention workload, which is why policy-level bootstrap comparison is required in addition to ROC-AUC."),
        heading(1, "5. ML Models Used"),
        para("Data → validation and leakage-safe joins → train-only preprocessing/feature engineering → model zoo → tuning and validation selection → calibration → independent CRC calibration → global/category thresholds → IID holdout, subgroup and future-period audit → intervention decision.", bold=True),
        para("The model zoo includes logistic, ridge, lasso and elastic-net regression; Naive Bayes; KNN; linear SVM; neural net; decision tree; random forest; Extra Trees; GBM; XGBoost; and LightGBM."),
        table(read_csv("model_zoo_01_leaderboard.csv", ["model_id","family","auc","pr_auc","brier","log_loss","accuracy","precision","recall","f1","fit_seconds"], percent={"accuracy","precision","recall","f1"})),
        para("Table 9. Complete model-zoo validation leaderboard.", italic=True, align="center")]

model_figures = [
    ("model_auc_comparison.png", "Figure 7. Model ROC-AUC comparison.", "Inference: XGBoost provides the strongest overall ranking performance, with LightGBM and GBM closely following. The narrow leading margin supports retaining Elastic-Net as a second finalist rather than relying on a single algorithm."),
    ("model_pr_auc_comparison.png", "Figure 8. Model precision-recall AUC comparison.", "Inference: the leading tree and regularised-linear models maintain strong precision-recall behaviour, confirming that their ranking advantage also holds when attention is focused on returned orders."),
    ("model_brier_comparison.png", "Figure 9. Model Brier score comparison.", "Inference: the leading models also have better probability-quality scores, but calibration is still required before using their outputs as decision thresholds."),
    ("model_tuning_gain.png", "Figure 10. Hyperparameter-tuning gain.", "Inference: tuning yields incremental rather than dramatic gains for the strongest models. This indicates that model-family choice and reliable calibration matter at least as much as exhaustive hyperparameter search.")
]
for fig, cap, insight in model_figures:
    doc += [picture(FIGURES / fig, cap), para(insight, italic=True, colour="365F91")]

doc += [table(read_csv("model_tuning_summary.csv", ["model_id","n_configs","best_auc","worst_auc","auc_range_across_grid","hyperparameters"])),
        para("Table 10. Tuning summary.", italic=True, align="center"),
        table(read_csv("model_final_selection.csv", ["model_id","label","auc","pr_auc","brier","n_eval","selected","reason","gap_ci_low","gap_ci_high"])),
        para("Table 11. Final model selection. XGBoost is top-ranked; Elastic-Net is retained as a close, distinct model family.", italic=True, align="center"),
        heading(1, "6. Calibration and Conformal Risk Control"),
        para("Calibration assesses whether estimated probabilities agree with observed outcome frequency. Isotonic regression is selected using Brier score and log loss. CRC then computes a threshold tau for a chosen alpha risk target. Orders with calibrated probability at least tau receive an intervention. The policy controls value-weighted missed-return exposure, providing an explicit risk–workload trade-off."),
        table(read_csv("model_15_calibration_final_evaluation.csv", ["method","brier","log_loss","selected","brier_improvement_vs_raw","logloss_improvement_vs_raw"])),
        para("Table 12. Final calibration evaluation.", italic=True, align="center"),
        table(read_csv("model_18_crc_final_evaluation.csv", ["alpha","tau","iid_holdout_risk","iid_holdout_intervention_rate","future_test_risk","future_test_intervention_rate","risk_target_met_on_holdout","risk_target_met_on_future_test"], percent={"iid_holdout_risk","iid_holdout_intervention_rate","future_test_risk","future_test_intervention_rate"})),
        para("Table 13. Global CRC results across targets.", italic=True, align="center")]

policy_figures = [
    ("07_calibration_curve.png", "Figure 11. Calibration curve.", "Inference: isotonic calibration brings predicted probabilities closer to observed return frequencies. This is critical because CRC uses probability scores to set intervention thresholds."),
    ("06_value_exposure_and_intervention_by_threshold.png", "Figure 12. Exposure and intervention trade-off.", "Inference: stricter risk targets require intervention on a larger fraction of orders. The graph makes the operational cost of lowering residual missed-return exposure visible."),
    ("09_category_aware_crc_risk.png", "Figure 13. Category-aware CRC risk.", "Inference: category-specific thresholds reduce excess risk in several categories relative to a global threshold. Remaining target misses are monitoring findings, not evidence that a single threshold works equally well everywhere.")
]
for fig, cap, insight in policy_figures:
    doc += [picture(FIGURES / fig, cap), para(insight, italic=True, colour="365F91")]

doc += [table(read_csv("model_21_category_crc_final_evaluation.csv", ["productType","n_holdout","risk_with_global_threshold","risk_with_category_threshold","global_over_target","category_over_target","risk_change_category_minus_global"], percent={"risk_with_global_threshold","risk_with_category_threshold","risk_change_category_minus_global"})),
        para("Table 14. Category-aware CRC holdout evaluation.", italic=True, align="center"),
        heading(1, "7. Final Policy Evaluation, Subgroups and Drift"),
        table(read_csv("p3_10_final_policy_comparison.csv", ["model_id","alpha","tau","calibration_intervention_rate","holdout_risk","holdout_intervention_rate","future_test_risk","future_test_intervention_rate","risk_target_met_on_future_test"], percent={"calibration_intervention_rate","holdout_risk","holdout_intervention_rate","future_test_risk","future_test_intervention_rate"})),
        para("Table 15. XGBoost versus Elastic-Net final policy comparison.", italic=True, align="center"),
        table(read_csv("model_23_subgroup_final_evaluation.csv", ["subgroup_variable","subgroup_value","n","intervention_rate","false_negative_exposure"], limit=25, percent={"intervention_rate","false_negative_exposure"})),
        para("Table 16. Subgroup intervention burden and missed exposure.", italic=True, align="center"),
        table(read_csv("model_24_future_drift_final_evaluation.csv", ["variable","psi","ks_statistic","js_divergence","psi_flag","psi_severity"])),
        para("Table 17. Future-period drift diagnostics.", italic=True, align="center"),
        para("Inference: the reported PSI values are below threshold, but future-period risk misses occur for some model/target combinations. Distributional drift monitoring must therefore be supplemented by direct outcome and policy-risk monitoring; the project correctly recommends recalibration."),
        heading(1, "8. Output Screenshots (Results)")]

result_figures = [
    ("model_roc_curves.png", "Figure 14. ROC curves for final models.", "Inference: the final models discriminate returned from retained orders well, with XGBoost showing the strongest area-under-curve result. The curves support its selection as the main predictive candidate."),
    ("model_pr_curves.png", "Figure 15. Precision-recall curves for final models.", "Inference: the precision-recall curves confirm useful positive-class ranking. This matters because interventions are targeted at high-probability return orders rather than applied uniformly."),
    ("model_confusion_matrices.png", "Figure 16. Confusion matrices.", "Inference: fixed classification counts show the trade-off between catching returns and creating interventions. CRC improves on a single fixed cutoff by selecting this trade-off according to an explicit risk target."),
    ("p3_policy_intervention_comparison.png", "Figure 17. Final intervention-policy comparison.", "Inference: workload decreases as the permitted alpha increases. XGBoost and Elastic-Net cross over at different targets, so the operationally preferred model depends on the organisation's chosen tolerance."),
    ("s10_difference_ci.png", "Figure 18. Bootstrap confidence intervals.", "Inference: intervals that do not cross zero indicate statistically detectable policy differences. The figure supports comparing models on both risk and workload rather than reporting ROC-AUC alone.")
]
for fig, cap, insight in result_figures:
    doc += [picture(FIGURES / fig, cap), para(insight, italic=True, colour="365F91")]

doc += [heading(1, "9. Conclusion"),
        para("CostConformal-Return is an end-to-end, decision-aware machine-learning project. XGBoost is the highest-performing validation model, while Elastic-Net remains a strong comparator. Isotonic calibration is selected for probability quality. CRC makes the risk/workload trade-off explicit, and category-aware thresholds improve policy granularity. Crucially, future-period auditing shows that low input drift does not guarantee every risk target is met, which justifies outcome-based monitoring and recalibration."),
        heading(1, "10. R Code"),
        para("Complete source code is preserved in the project root: R/00_setup.R; 01_data_preparation.qmd; 01b_preprocessing.qmd; 02_eda_visualizations.qmd; 03_calibration_crc_visualizations.qmd; 04_feature_engineering.qmd; 05_database_connectivity.qmd; 06_model_zoo.qmd; 07_hyperparameter_tuning.qmd; 08_comparative_evaluation.qmd; 09_phase3_crc_policy_evaluation.qmd; and 10_statistical_analysis.qmd."),
        para("Key implementation functions include safe gzip CSV reading, Wilson confidence intervals, ROC-AUC, PR-AUC, Brier score, log loss, confusion-matrix metrics, calibrated probability scoring and CRC threshold evaluation."),
        heading(1, "11. GitHub Repository"),
        para("Repository URL: [INSERT YOUR GITHUB REPOSITORY URL HERE]", bold=True),
        para("Before publishing, add a README that states the objective, data-access conditions, R/Python versions, package lockfile, execution/render order and live-demo instructions. Do not upload restricted raw data."),
        heading(1, "12. Output Inventory"),
        para("The project persists 82 CSV output tables, trained models, a SQLite database, report-ready figures and rendered stage reports. The tables included in this document cover dataset validation, joins, splits, EDA, preprocessing, feature selection, model zoo, tuning, calibration, CRC, category thresholds, subgroup audit, drift diagnostics and statistical inference."),
        table(read_csv("model_27_final_stage3_status.csv")),
        para("Table 18. Final Stage 3 quality gate.", italic=True, align="center")]

# Exhaustive appendices: retain every persisted result, figure and trained-model artifact.
doc += [page_break(), heading(1, "Appendix C. Additional Feature-Engineering and Model Screenshots"),
        para("These figures complete the visual evidence not repeated in the main narrative.")]
extra_figures = [
    ("10_feature_correlation_heatmap.png", "Figure C1. Feature-correlation heatmap.", "Inference: highly correlated features are identified before fitting, reducing redundant linear predictors and helping prevent unstable coefficient estimates."),
    ("11_lasso_coefficients.png", "Figure C2. LASSO coefficient path/selection.", "Inference: LASSO shrinks weak predictors and retains a compact linear feature set, reducing variance while preserving predictive signal."),
    ("12_rf_importance_screening.png", "Figure C3. Random-forest importance screening.", "Inference: non-linear importance ranking identifies variables that add predictive value beyond a purely linear feature-selection view."),
    ("model_elastic_net_importance.png", "Figure C4. Elastic-Net feature importance.", "Inference: the selected linear model concentrates contribution in a limited set of customer/product history and contextual features, improving interpretability."),
    ("model_xgboost_importance.png", "Figure C5. XGBoost feature importance.", "Inference: XGBoost captures non-linear and interaction-based signal; its importance profile complements the Elastic-Net view rather than replacing it."),
    ("s10_holdout_risk_comparison.png", "Figure C6. IID-holdout policy-risk comparison.", "Inference: observed risk must be read jointly with intervention workload. The figure supports selecting a policy based on an explicit alpha target, not model score alone.")
]
for fig, cap, insight in extra_figures:
    doc += [picture(FIGURES / fig, cap), para(insight, italic=True, colour="365F91")]

doc += [page_break(), heading(1, "Appendix D. Complete Persisted Output Tables"),
        para("This appendix reproduces every remaining CSV result table saved by the project. It includes exposure setup, database checks, feature-selection screens, tuning grids, raw versus calibrated performance, Phase 3 intermediate diagnostics and ROC/PR curve points. The 1,600-point curve table is intentionally retained for complete numeric traceability.")]
primary_tables = {
    "01_dataset_validation_summary.csv", "02_join_audit.csv", "03_split_summary.csv", "09_return_rate_by_product_type.csv",
    "13_missingness_before.csv", "14_missingness_after.csv", "model_zoo_01_leaderboard.csv", "model_tuning_summary.csv",
    "model_final_selection.csv", "model_15_calibration_final_evaluation.csv", "model_18_crc_final_evaluation.csv",
    "model_21_category_crc_final_evaluation.csv", "model_23_subgroup_final_evaluation.csv", "model_24_future_drift_final_evaluation.csv",
    "model_27_final_stage3_status.csv", "p3_10_final_policy_comparison.csv", "s10_01_wilson_ci_intervention_rate.csv",
    "s10_04_significance_summary.csv"
}
for output_path in sorted(TABLES.glob("*.csv")):
    if output_path.name in primary_tables:
        continue
    doc += [heading(2, output_path.name), table(read_csv(output_path.name)), para(f"Complete contents of {output_path.name}.", italic=True, align="center")]

model_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "models").rglob("*") if p.is_file())
doc += [page_break(), heading(1, "Appendix E. Trained Model and Registry Artifact Inventory"),
        para("The following serialized artifacts are present in the project. They provide the reproducible saved objects behind the tables and policy evaluation."),
        table([["Saved artifact"]] + [[p] for p in model_files]),
        heading(1, "Appendix F. Rendered Stage-Report Inventory"),
        para("Rendered HTML evidence is available for stages 1 through 11 in the files directory. File 12 is the consolidated document version of this evidence.")]

styles = '''<w:styles xmlns:w="%s"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:color w:val="1F4E78"/><w:sz w:val="30"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="2F75B5"/><w:sz w:val="24"/></w:rPr></w:style></w:styles>''' % NS
document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{NS}" xmlns:r="{REL}"><w:body>{''.join(doc)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="900" w:right="900" w:bottom="900" w:left="900"/></w:sectPr></w:body></w:document>'''
rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
for index, (path, rid) in enumerate(images, 1): rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{index}.png"/>')

content_types = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>','<Default Extension="xml" ContentType="application/xml"/>','<Default Extension="png" ContentType="image/png"/>','<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>','<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>']
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' + ''.join(content_types) + '</Types>')
    z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr("word/document.xml", document)
    z.writestr("word/styles.xml", styles)
    z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(rels) + '</Relationships>')
    for index, (path, _) in enumerate(images, 1): z.write(path, f"word/media/image{index}.png")
print(OUT)
