# CostConformal-Return

CostConformal-Return is an end-to-end data-science project for predicting e-commerce returns and turning calibrated probabilities into a value-sensitive intervention policy using Conformal Risk Control (CRC).

The project asks more than *“Will this order be returned?”* It asks *“Which orders should receive an intervention so that value-weighted missed-return exposure stays below a selected risk target?”*

## Highlights

- Validated event, customer and product data with leakage-safe joins and splits.
- Training-only preprocessing: missing-value treatment, encoding and normalisation.
- EDA, descriptive statistics, confidence intervals and feature engineering.
- SQLite data layer for stored split retrieval.
- A 14-model machine-learning comparison and hyperparameter tuning.
- Isotonic probability calibration.
- Global and category-aware CRC intervention thresholds.
- Subgroup burden, future-period drift and bootstrap policy comparisons.
- A self-contained interactive results demo.

## Repository structure

```text
CostConformal-Return/
├── 01_data_preparation.qmd                 # validation, joins and splits
├── 01b_preprocessing.qmd                   # preprocessing contract
├── 02_eda_visualizations.qmd               # exploratory analysis
├── 03_calibration_crc_visualizations.qmd   # initial calibration and CRC
├── 04_feature_engineering.qmd               # feature screening and selection
├── 05_database_connectivity.qmd             # SQLite persistence/retrieval
├── 06_model_zoo.qmd                         # model-zoo training
├── 07_hyperparameter_tuning.qmd             # tuning experiments
├── 08_comparative_evaluation.qmd            # model comparison/selection
├── 09_phase3_crc_policy_evaluation.qmd      # final policy evaluation
├── 10_statistical_analysis.qmd              # Wilson/bootstrap inference
├── 11_final_report.qmd                      # project final report
├── 12_comprehensive_project_report.qmd      # consolidated report source
├── 12_comprehensive_project_report.docx     # consolidated Word report
├── 13_extended_statistical_analysis.qmd     # detailed statistics supplement
├── R/00_setup.R                             # common setup, I/O and metrics
├── data/                                    # raw/processed data and SQLite DB
├── models/                                  # serialized model/calibration artifacts
├── outputs/tables/                          # persisted numeric outputs
├── outputs/figures/                         # report-ready figures
├── files/                                   # rendered reports for stages 1–11
├── live_demo/                               # standalone browser demo
└── scripts/                                 # supporting build utilities
```

## Key results

- **Best predictive model:** XGBoost, validation ROC-AUC **0.8211**.
- **Selected calibration:** isotonic regression, with the strongest reported Brier score and log loss.
- **Final candidates:** XGBoost and Elastic-Net.
- **CRC policy:** selects an intervention threshold for risk targets from 1% to 10%.
- **At α = 5%:** the XGBoost policy has an IID-holdout missed-exposure risk of about **4.87%** with an intervention workload of about **53.8%**.
- **Monitoring conclusion:** feature PSI drift was low, but selected future-period policy targets can still be missed; regular outcome-based recalibration is recommended.

## Run the live demo locally

The demo is dependency-free and runs in any modern browser.

```bash
python3 -m http.server 8000
```

Open [http://localhost:8000/live_demo/](http://localhost:8000/live_demo/).

It includes project-stage navigation, model comparison, calibration information, adjustable CRC risk targets, category-aware results, subgroup burden, and future-period monitoring.

## Render reports

Install [Quarto](https://quarto.org/docs/get-started/) and ensure the R packages referenced in `R/00_setup.R` are available. Render a single report from the project root:

```bash
quarto render 12_comprehensive_project_report.qmd
quarto render 13_extended_statistical_analysis.qmd
```


<<<<<<< HEAD
=======
## Deploy the live demo with GitHub Pages

A GitHub Actions workflow is included at `.github/workflows/deploy-live-demo.yml`.

1. Create a GitHub repository and push this project to its `main` branch.
2. In GitHub, open **Settings → Pages** and set **Source** to **GitHub Actions**.
3. Push a change to `main`, or run **Deploy live demo to GitHub Pages** manually from the repository’s **Actions** tab.
4. GitHub will show the deployed URL in the completed workflow, normally:

   ```text
   https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPOSITORY-NAME/
   ```

The Pages build publishes the standalone `live_demo/` directory as the site home page and the rendered HTML reports in `files/`. Large raw data, trained model artifacts and restricted project files are not published.

## Reproducibility and responsible sharing

- Do not publish data that is private, licence-restricted or too large for GitHub.
- The outputs, figures and reports support traceability without requiring the raw data to be public.
- Pin R package versions with `renv` before a public release.
- Re-run the full pipeline in stage order if raw data or modelling decisions change.

## Team

| Name | Registration number |
|---|---|
| [Team Member 1] | [Registration Number] |
| [Team Member 2] | [Registration Number] |
| [Team Member 3] | [Registration Number] |

## License

Add a license before publishing the repository publicly.

