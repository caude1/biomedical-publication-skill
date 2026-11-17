# Forest plot of subgroup odds ratios with an aligned table of counts. All data are synthetic.
# Run: Rscript forest-example.R   (reads forest-example.csv beside this script; writes forest-example.png and forest-example.pdf there)
# Odds ratios and confidence limits are plotted exactly as supplied in forest-example.csv.
library(grid)

args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grep("^--file=", args)])
here <- if (length(script)) dirname(normalizePath(script)) else getwd()
d <- read.csv(file.path(here, "forest-example.csv"), stringsAsFactors = FALSE)

# ---- Checks on the supplied values -------------------------------------------------------------
overall <- d[d$subgroup_heading == "Overall", ]
stopifnot(nrow(overall) == 1,
          d$ci_lower < d$odds_ratio, d$odds_ratio < d$ci_upper,
          d$events_exposed <= d$total_exposed, d$events_unexposed <= d$total_unexposed)
count_columns <- c("events_exposed", "total_exposed", "events_unexposed", "total_unexposed")
for (heading in setdiff(unique(d$subgroup_heading), "Overall")) {
  # The levels of each subgroup variable must partition the full cohort.
  stopifnot(colSums(d[d$subgroup_heading == heading, count_columns]) == unlist(overall[count_columns]))
}

# ---- Display text ------------------------------------------------------------------------------
# Row labels written out so that each reads without its section head.
row_label <- c("All patients" = "All patients",
               "Younger than 65 years" = "Younger than 65 years",
               "65 years or older" = "65 years or older",
               "Women" = "Women", "Men" = "Men",
               "No" = "Without diabetes", "Yes" = "With diabetes")
stopifnot(d$subgroup %in% names(row_label))
count <- function(x) format(x, big.mark = ",", trim = TRUE)
# Percentages are rounded half up in integer arithmetic, so 171/1,520 (exactly 11.25%) prints as 11.3.
percent <- function(events, total) sprintf("(%.1f)", ((2000 * events + total) %/% (2 * total)) / 10)
d$label <- unname(row_label[d$subgroup])
d$or_text <- sprintf("%.2f (%.2f–%.2f)", d$odds_ratio, d$ci_lower, d$ci_upper)

# One table row per line: the full cohort first, then a bold head and indented rows per variable.
all_patients <- which(d$subgroup_heading == "Overall")
rows <- data.frame(kind = "summary", text = d$label[all_patients], i = all_patients)
for (heading in setdiff(unique(d$subgroup_heading), "Overall")) {
  members <- which(d$subgroup_heading == heading)
  rows <- rbind(rows, data.frame(kind = "head", text = heading, i = NA),
                data.frame(kind = "level", text = d$label[members], i = members))
}

# ---- Layout in inches at the printed width (two columns) -----------------------------------------
page_width <- 7
row_pitch <- 0.205           # distance between row centers
section_gap <- 0.055         # extra space above each section head
first_row <- 0.80
rows$y <- first_row + row_pitch * (seq_len(nrow(rows)) - 1) +
  section_gap * cumsum(rows$kind == "head")
axis_y <- max(rows$y) + 0.19
page_height <- axis_y + 0.66

label_x <- 0.08
indent <- 0.14
low_x <- 2.03                # center of the low-staffing count column
high_x <- 3.08               # center of the high-staffing count column
or_x <- 4.17                 # center of the odds ratio text column
plot_left <- 4.90
plot_right <- 6.78
axis_limits <- c(0.70, 2.60)
axis_ticks <- c(0.75, 1, 1.5, 2, 2.5)
stopifnot(d$ci_lower >= axis_limits[1], d$ci_upper <= axis_limits[2])  # no interval leaves the axis
plot_x <- function(value) {
  plot_left + (plot_right - plot_left) * (log(value) - log(axis_limits[1])) / diff(log(axis_limits))
}

ink <- "#1A1A1A"
muted <- "#4D4D4D"
reference <- "#9A9A9A"
font <- "Arial"

from_top <- function(y) unit(1, "npc") - unit(y, "in")
text_at <- function(x, y, label, size = 7.5, face = "plain", colour = ink, align = "left") {
  grid.text(label, unit(x, "in"), from_top(y), just = c(align, "centre"),
            gp = gpar(fontfamily = font, fontface = face, fontsize = size, col = colour))
}
line_at <- function(x1, y1, x2, y2, colour = muted, lwd = 0.65) {
  grid.lines(unit(c(x1, x2), "in"), from_top(c(y1, y2)), gp = gpar(col = colour, lwd = lwd, lineend = "butt"))
}
width_in <- function(label, size = 7.5, face = "plain") {
  pushViewport(viewport(gp = gpar(fontfamily = font, fontface = face, fontsize = size)))
  on.exit(popViewport())
  max(convertWidth(stringWidth(label), "in", valueOnly = TRUE))
}

draw_figure <- function() {
  grid.newpage()

  # Count cells are right-aligned so the totals and the percentages line up on their last digits.
  cell <- function(events, total) sprintf("%s/%s %s", count(events), count(total), percent(events, total))
  cell_w <- width_in(c(cell(d$events_exposed, d$total_exposed), cell(d$events_unexposed, d$total_unexposed)))
  count_cell <- function(center, y, events, total) {
    text_at(center + cell_w / 2, y, cell(events, total), align = "right")
  }

  # Column heads
  spanner_rule <- 0.43
  head_y <- 0.57
  text_at((low_x + high_x) / 2, 0.16, "Missed follow-up visit within 30 days,", 8, "bold", align = "centre")
  text_at((low_x + high_x) / 2, 0.30, "No./total (%)", 8, "bold", align = "centre")
  line_at(low_x - cell_w / 2 - 0.06, spanner_rule, high_x + cell_w / 2 + 0.06, spanner_rule, reference, 0.6)
  or_w <- width_in(d$or_text)
  text_at((or_x - or_w / 2 + plot_right) / 2, 0.30, "Low vs high staffing at discharge", 8, "bold", align = "centre")
  line_at(or_x - or_w / 2 - 0.06, spanner_rule, plot_right, spanner_rule, reference, 0.6)

  text_at(label_x, head_y, "Subgroup", 8, "bold")
  text_at(low_x, head_y, "Low staffing", 8, "bold", align = "centre")
  text_at(high_x, head_y, "High staffing", 8, "bold", align = "centre")
  text_at(or_x, head_y, "Odds ratio (95% CI)", 8, "bold", align = "centre")

  # Null line behind the marks
  line_at(plot_x(1), min(rows$y) - 0.12, plot_x(1), axis_y, reference, 0.8)

  for (r in seq_len(nrow(rows))) {
    y <- rows$y[r]
    if (rows$kind[r] == "head") {
      text_at(label_x, y, rows$text[r], face = "bold")
      next
    }
    v <- d[rows$i[r], ]
    text_at(label_x + if (rows$kind[r] == "level") indent else 0, y, rows$text[r])
    count_cell(low_x, y, v$events_exposed, v$total_exposed)
    count_cell(high_x, y, v$events_unexposed, v$total_unexposed)
    text_at(or_x, y, v$or_text, align = "centre")
    if (rows$kind[r] == "summary") {
      # Full cohort: a diamond whose width is the confidence interval.
      grid.polygon(unit(plot_x(c(v$ci_lower, v$odds_ratio, v$ci_upper, v$odds_ratio)), "in"),
                   from_top(y + c(0, -0.04, 0, 0.04)), gp = gpar(fill = ink, col = ink, lwd = 0.5))
    } else {
      line_at(plot_x(v$ci_lower), y, plot_x(v$ci_upper), y, ink, 1.05)
      grid.rect(unit(plot_x(v$odds_ratio), "in"), from_top(y), width = unit(0.075, "in"),
                height = unit(0.075, "in"), gp = gpar(fill = ink, col = NA))
    }
  }

  # Axis, its title and direction cues
  line_at(plot_x(axis_limits[1]), axis_y, plot_x(axis_limits[2]), axis_y)
  for (tick in axis_ticks) {
    line_at(plot_x(tick), axis_y, plot_x(tick), axis_y + 0.04)
    text_at(plot_x(tick), axis_y + 0.135, format(tick, drop0trailing = TRUE), 7.5, colour = muted, align = "centre")
  }
  text_at((plot_left + plot_right) / 2, axis_y + 0.32, "Odds ratio for a missed visit (log scale)", 8, align = "centre")
  text_at(plot_x(1) - 0.06, axis_y + 0.49, "\u2190 Lower with low staffing", 6.5, colour = muted, align = "right")
  text_at(plot_x(1) + 0.06, axis_y + 0.49, "Higher with low staffing \u2192", 6.5, colour = muted)
}

ragg::agg_png(file.path(here, "forest-example.png"), width = page_width, height = page_height,
              units = "in", res = 300, background = "white")
draw_figure()
invisible(dev.off())
cairo_pdf(file.path(here, "forest-example.pdf"), width = page_width, height = page_height, family = font)
draw_figure()
invisible(dev.off())
cat(sprintf("Wrote forest-example.png and forest-example.pdf at %.2f x %.2f in\n", page_width, page_height))
