# ==============================================================================
# 00_setup.R
# CostConformal-Return — shared setup: packages, paths, IO helpers, metrics
#
# Sourced by every stage (01_data_preparation.qmd, 02_eda_visualizations.qmd,
# 03_calibration_crc_visualizations.qmd / .R) so all stages use identical,
# tested primitives instead of re-implementing IO or metrics per stage.
#
# Place this file at: CostConformal-Return/R/00_setup.R
# ==============================================================================

# ---- 1. Packages -------------------------------------------------------------

required_packages <- c("data.table", "ggplot2", "scales")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message("Installing missing package: ", pkg)
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
}

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(scales)
  library(R.utils)
})

# ---- 2. Project paths ---------------------------------------------------------
# All paths are relative to the project root (where the .Rproj lives).
# Every stage sources this file from the project root, so relative paths
# resolve identically everywhere.

RAW_PICKLE_DIR <- file.path("data", "raw_pickle")
RAW_DIR         <- file.path("data", "raw_csv_gz")
PROCESSED_DIR   <- file.path("data", "processed")
MODEL_DIR       <- "models"
TABLE_DIR       <- file.path("outputs", "tables")
FIGURE_DIR      <- file.path("outputs", "figures")

# Create any output directories that don't exist yet. Raw directories are
# never created here — if they're missing, something upstream (the pickle
# conversion step) hasn't been run, and that should fail loudly, not silently
# make an empty folder.
for (d in c(PROCESSED_DIR, MODEL_DIR, TABLE_DIR, FIGURE_DIR)) {
  if (!dir.exists(d)) dir.create(d, recursive = TRUE)
}

# ---- 3. File existence guard ---------------------------------------------------

#' Stop with an informative message if any expected file is missing.
#' @param paths A named or unnamed character vector of file paths.
assert_files_exist <- function(paths) {
  missing <- paths[!file.exists(paths)]
  if (length(missing) > 0) {
    stop(
      "The following expected file(s) are missing:\n  ",
      paste(missing, collapse = "\n  "),
      "\n\nCheck that the pickle-to-CSV conversion step has been run ",
      "(see stage1_convert_pickle_to_csv.py) and that you are working ",
      "from the project root (next to the .Rproj file).",
      call. = FALSE
    )
  }
  invisible(TRUE)
}

# ---- 4. gzip CSV reader with safe hash-ID handling -----------------------------

#' Read a gzip-compressed CSV, forcing designated ID columns to character.
#'
#' Hashed identifiers (e.g. hash(customerId), hash(variantID)) must never be
#' read as numeric: a 64-bit hash stored as a double silently loses precision,
#' which then corrupts every downstream join. This reader guarantees those
#' columns come in as character strings regardless of how they look.
#'
#' @param path Path to a .csv.gz file.
#' @param id_columns Character vector of column names (as they appear in the
#'   raw file) that must be forced to character type.
#' @param select Optional character vector of columns to read. id_columns are
#'   always included even if omitted from `select`.
#' @return A data.table.
read_csv_gz <- function(path, id_columns = character(0), select = NULL) {
  if (!file.exists(path)) {
    stop("File not found: ", path, call. = FALSE)
  }

  if (!is.null(select)) {
    select <- union(select, id_columns)
  }

  col_classes <- if (length(id_columns) > 0) {
    setNames(rep("character", length(id_columns)), id_columns)
  } else {
    NULL
  }

  if (.Platform$OS.type == "windows") {
    dt <- fread(
      cmd = paste0('type "', path, '" | gzip -dc'),
      select = select,
      colClasses = col_classes,
      showProgress = FALSE
    )
  } else {
    dt <- fread(
      file = path,
      select = select,
      colClasses = col_classes,
      showProgress = FALSE
    )
  }

  # Belt-and-braces: force id columns to character even if fread's column
  # detection guessed otherwise (e.g. a select-without-colClasses edge case).
  for (col in id_columns) {
    if (col %in% names(dt) && !is.character(dt[[col]])) {
      dt[[col]] <- as.character(dt[[col]])
    }
  }

  dt
}

# ---- 5. Plot saving helper -----------------------------------------------------

#' Save a ggplot to outputs/figures/ at a fixed, report-ready resolution.
#' @param plot A ggplot object.
#' @param filename File name (e.g. "01_return_class_distribution.png").
#' @param width,height In inches.
#' @param dpi Resolution; the project standard is 300.
save_plot <- function(plot, filename, width = 8, height = 5, dpi = 300) {
  ggsave(
    filename = file.path(FIGURE_DIR, filename),
    plot = plot,
    width = width,
    height = height,
    dpi = dpi
  )
}

# ---- 6. Wilson score confidence interval for a proportion -----------------------

#' Wilson score interval for a binomial proportion.
#' @param successes Number of successes (e.g. returns).
#' @param n Total trials (e.g. events).
#' @param conf_level Confidence level, default 0.95.
#' @return A list with p_hat, lower, upper.
wilson_ci <- function(successes, n, conf_level = 0.95) {
  if (n == 0) return(list(p_hat = NA_real_, lower = NA_real_, upper = NA_real_))

  z <- qnorm(1 - (1 - conf_level) / 2)
  p_hat <- successes / n
  denom <- 1 + (z^2) / n
  center <- p_hat + (z^2) / (2 * n)
  margin <- z * sqrt((p_hat * (1 - p_hat) / n) + (z^2) / (4 * n^2))

  list(
    p_hat = p_hat,
    lower = (center - margin) / denom,
    upper = (center + margin) / denom
  )
}

# ---- 7. Classification metrics --------------------------------------------------

#' Rank-based ROC-AUC (Mann-Whitney U formulation) — no external deps.
#' @param y_true Vector of 0/1 labels.
#' @param y_prob Vector of predicted probabilities/scores.
auc_roc <- function(y_true, y_prob) {
  ok <- !is.na(y_true) & !is.na(y_prob)
  y_true <- y_true[ok]; y_prob <- y_prob[ok]

  n_pos <- as.double(sum(y_true == 1))
  n_neg <- as.double(sum(y_true == 0))
  if (n_pos == 0 || n_neg == 0) return(NA_real_)

  r <- rank(y_prob, ties.method = "average")
  (sum(r[y_true == 1]) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
}

#' PR-AUC via step-function (precision-recall) integration.
#' @param y_true Vector of 0/1 labels.
#' @param y_prob Vector of predicted probabilities/scores.
pr_auc <- function(y_true, y_prob) {
  ok <- !is.na(y_true) & !is.na(y_prob)
  y_true <- y_true[ok]; y_prob <- y_prob[ok]

  ord <- order(y_prob, decreasing = TRUE)
  y_true <- y_true[ord]

  tp <- cumsum(y_true == 1)
  fp <- cumsum(y_true == 0)
  n_pos <- sum(y_true == 1)
  if (n_pos == 0) return(NA_real_)

  precision <- tp / (tp + fp)
  recall <- tp / n_pos

  # Prepend the (recall=0, precision=1) anchor point, then integrate via
  # the trapezoidal rule over unique recall values.
  recall <- c(0, recall)
  precision <- c(1, precision)

  sum(diff(recall) * (head(precision, -1) + tail(precision, -1)) / 2)
}

#' Brier score (mean squared error of predicted probabilities).
brier_score <- function(y_true, y_prob) {
  ok <- !is.na(y_true) & !is.na(y_prob)
  mean((y_prob[ok] - y_true[ok])^2)
}

#' Log-loss (binary cross-entropy), with probability clipping to avoid -Inf.
log_loss <- function(y_true, y_prob, eps = 1e-15) {
  ok <- !is.na(y_true) & !is.na(y_prob)
  y_true <- y_true[ok]
  y_prob <- pmin(pmax(y_prob[ok], eps), 1 - eps)
  -mean(y_true * log(y_prob) + (1 - y_true) * log(1 - y_prob))
}

#' Confusion-matrix-derived metrics at a fixed decision threshold.
#' @param y_true Vector of 0/1 labels.
#' @param y_prob Vector of predicted probabilities/scores.
#' @param threshold Decision threshold (predict 1 if y_prob >= threshold).
#' @return A named list: tp, fp, tn, fn, precision, recall, f1, accuracy,
#'   specificity, intervention_rate.
confusion_metrics <- function(y_true, y_prob, threshold) {
  ok <- !is.na(y_true) & !is.na(y_prob)
  y_true <- y_true[ok]; y_prob <- y_prob[ok]

  pred <- as.integer(y_prob >= threshold)

  tp <- sum(pred == 1 & y_true == 1)
  fp <- sum(pred == 1 & y_true == 0)
  tn <- sum(pred == 0 & y_true == 0)
  fn <- sum(pred == 0 & y_true == 1)

  precision <- if ((tp + fp) > 0) tp / (tp + fp) else NA_real_
  recall    <- if ((tp + fn) > 0) tp / (tp + fn) else NA_real_
  f1 <- if (!is.na(precision) && !is.na(recall) && (precision + recall) > 0) {
    2 * precision * recall / (precision + recall)
  } else {
    NA_real_
  }
  specificity <- if ((tn + fp) > 0) tn / (tn + fp) else NA_real_

  list(
    threshold = threshold,
    tp = tp, fp = fp, tn = tn, fn = fn,
    precision = precision,
    recall = recall,
    f1 = f1,
    accuracy = (tp + tn) / length(y_true),
    specificity = specificity,
    intervention_rate = mean(pred == 1)
  )
}

message("00_setup.R loaded: paths, IO helpers, and metrics are ready.")

