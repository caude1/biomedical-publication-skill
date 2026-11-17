# Run Rscript figure-example.R in the output directory to write a PNG and vector PDF.
# All data are synthetic. Each adult had one referral and complete follow-up.
#
# The figure carries no title or legend of its own. The manuscript legend would read:
#   Figure 1. Booking and attendance after outpatient referral, by initial invitation channel.
#   A, Cumulative percentage of referrals with a first booking; curves step at the end of
#   each day. B, Attendance at a visit booked within 14 days, including visits that took
#   place later. The first row counts referrals without a booking as not attending. The
#   second row is restricted to referrals booked by day 14, a group defined after the
#   invitation. Staff selected the invitation channel, and follow-up to day 14 was complete.
#   Differences are unadjusted, with normal-approximation 95% CIs.
library(ggplot2)
library(grid)

referrals <- data.frame(
  channel = c("Telephone", "Portal"),
  referred = c(150, 200),
  attended = c(63, 80)
)
daily <- data.frame(
  day = rep(0:14, 2),
  channel = rep(referrals$channel, each = 15),
  new_bookings = c(
    0, 9, 8, 11, 10, 8, 7, 5, 5, 5, 4, 5, 5, 4, 4,
    0, 6, 7, 9, 12, 9, 8, 9, 7, 6, 4, 7, 5, 6, 5
  )
)
daily$booked <- ave(daily$new_bookings, daily$channel, FUN = cumsum)
daily$fraction <- daily$booked / referrals$referred[match(daily$channel, referrals$channel)]
last_day <- subset(daily, day == 14)
referrals$booked <- last_day$booked[match(referrals$channel, last_day$channel)]

# Each contrast is telephone minus portal, in percentage points. The uncorrected
# two-sample CI uses the unpooled normal approximation for independent groups.
risk_difference <- function(events, total) {
  test <- prop.test(events, total, correct = FALSE)
  c(estimate = unname(100 * (test$estimate[1] - test$estimate[2])),
    lower = 100 * test$conf.int[1], upper = 100 * test$conf.int[2])
}
# One decimal with a true minus sign. The column head and the cue under the axis give the direction.
signed_number <- function(x) sub("^-", "−", sprintf("%.1f", x))
format_ci <- function(result) {
  sprintf("%s to %s", signed_number(result["lower"]), signed_number(result["upper"]))
}
booking_difference <- risk_difference(referrals$booked, referrals$referred)
booking_note <- sprintf("Day 14, telephone minus portal\n%s percentage points (95%% CI, %s)",
                        signed_number(booking_difference["estimate"]), format_ci(booking_difference))

ink <- "#1A1A1A"
muted <- "#4D4D4D"
channels <- c(Telephone = "#BD5100", Portal = "#1B4590")
shapes <- c(Telephone = 16, Portal = 15)
# Show the last day's jump as a continuous stroke beneath each endpoint symbol.
last_day$starting_n <- referrals$referred[match(last_day$channel, referrals$channel)]
last_day$before_last_booking_day <- (last_day$booked - last_day$new_bookings) / last_day$starting_n
last_day$label <- sprintf("%s (n = %d), %.0f%%", last_day$channel, last_day$starting_n,
                          100 * last_day$fraction)

booking_plot <- ggplot(daily, aes(day, fraction, colour = channel)) +
  geom_step(aes(linetype = channel), linewidth = 0.67, direction = "hv") +
  geom_segment(data = last_day, aes(xend = day, y = before_last_booking_day, yend = fraction),
               linewidth = 0.67) +
  geom_point(data = last_day, aes(shape = channel), size = 1.65) +
  geom_text(data = last_day, aes(label = label), hjust = 0, nudge_x = 0.20,
            size = 7.8, size.unit = "pt", family = "Arial", show.legend = FALSE) +
  annotate("text", x = 6.85, y = 0.135, label = booking_note, hjust = 0, lineheight = 1.10,
           family = "Arial", size = 7.8, size.unit = "pt", colour = ink) +
  scale_colour_manual(values = channels) +
  scale_linetype_manual(values = c(Telephone = "42", Portal = "solid")) +
  scale_shape_manual(values = shapes) +
  scale_x_continuous(breaks = seq(0, 14, 2)) +
  scale_y_continuous(breaks = seq(0, 0.6, 0.2), labels = function(x) 100 * x) +
  coord_cartesian(xlim = c(0, 14), ylim = c(0, 0.64), expand = FALSE, clip = "off") +
  labs(x = "Days since referral", y = "Referrals booked, %") +
  theme_minimal(base_family = "Arial", base_size = 8) +
  theme(
    text = element_text(colour = ink),
    axis.text = element_text(size = 7.5, colour = muted),
    axis.line.x = element_line(colour = muted, linewidth = 0.3),
    axis.ticks.x = element_line(colour = muted, linewidth = 0.3),
    axis.ticks.length = unit(2.5, "pt"),
    axis.title.x = element_text(margin = margin(t = 5)),
    axis.title.y = element_text(margin = margin(r = 5)),
    panel.grid = element_blank(),
    panel.grid.major.y = element_line(colour = "#E2E2E2", linewidth = 0.3),
    legend.position = "none",
    plot.margin = margin(3, 61, 2, 1, unit = "pt")
  )

# Both attendance rows use the same attendees. Only the eligible denominator changes.
populations <- c("All referrals", "Referrals booked by day 14")
denominators <- list(referrals$referred, referrals$booked)
attendance_differences <- lapply(denominators, function(total) risk_difference(referrals$attended, total))

# Set type and panel alignment in physical units at the intended print width.
page_width <- 7
page_height <- 4.55
from_top <- function(y) unit(1, "npc") - unit(y, "in")
text_at <- function(x, y, label, size = 8, face = "plain", colour = ink, align = "left") {
  grid.text(label, unit(x, "in"), from_top(y), just = c(align, "centre"),
            gp = gpar(fontfamily = "Arial", fontface = face, fontsize = size, col = colour))
}
line_at <- function(x1, y1, x2, y2, colour = muted, lwd = 0.65) {
  grid.lines(unit(c(x1, x2), "in"), from_top(c(y1, y2)), gp = gpar(col = colour, lwd = lwd))
}
panel_heading <- function(letter, title, y) {
  box <- unit(0.15, "in")
  grid.rect(unit(0.215, "in"), from_top(y), width = box, height = box,
            gp = gpar(fill = "white", col = ink, lwd = 0.8))
  text_at(0.215, y, letter, 8.5, "bold", align = "centre")
  text_at(0.39, y, title, 8.5)
}

draw_figure <- function() {
  grid.newpage()
  panel_heading("A", "Time to first booking after referral", 0.16)
  pushViewport(viewport(x = unit(0.11, "in"), y = from_top(0.33),
                        width = unit(6.22, "in"), height = unit(2.24, "in"),
                        just = c("left", "top")))
  grid.draw(ggplotGrob(booking_plot))
  popViewport()

  panel_heading("B", "Attendance at a visit booked within 14 days", 2.80)
  text_at(2.55, 3.11, "Attended, No./total (%)", 8, "bold", align = "centre")
  text_at(5.25, 3.11, "Telephone minus portal, percentage points", 8, "bold", align = "centre")
  line_at(1.95, 3.23, 3.15, 3.23, "#9A9A9A", 0.6)
  line_at(3.35, 3.23, 6.87, 3.23, "#9A9A9A", 0.6)

  text_at(0.13, 3.36, "Denominator", 8, "bold")
  group_x <- c(2.20, 2.90)
  for (i in seq_len(nrow(referrals))) {
    text_at(group_x[i], 3.36, referrals$channel[i], 8, "bold", align = "centre")
  }
  text_at(3.95, 3.36, "Difference (95% CI)", 8, "bold", align = "centre")

  # Numerical and graphical columns use the same row centers and contrast values.
  rows <- c(3.64, 3.92)
  forest_x <- function(value) 5.72 + value * 0.044
  line_at(forest_x(0), 3.42, forest_x(0), 4.14, "#9A9A9A", 0.8)
  for (i in seq_along(populations)) {
    result <- attendance_differences[[i]]
    total <- denominators[[i]]
    text_at(0.13, rows[i], populations[i], size = 8)
    for (j in seq_along(group_x)) {
      cell <- sprintf("%d/%d (%.0f)", referrals$attended[j], total[j],
                      100 * referrals$attended[j] / total[j])
      text_at(group_x[j], rows[i], cell, align = "centre")
    }
    text_at(3.95, rows[i], sprintf("%s (%s)", signed_number(result["estimate"]), format_ci(result)),
            align = "centre")
    line_at(forest_x(result["lower"]), rows[i], forest_x(result["upper"]), rows[i], ink, 1.15)
    grid.points(unit(forest_x(result["estimate"]), "in"), from_top(rows[i]),
                pch = 15, size = unit(0.077, "in"), gp = gpar(col = ink))
  }

  line_at(forest_x(-25), 4.14, forest_x(25), 4.14, muted)
  for (tick in c(-20, 0, 20)) {
    line_at(forest_x(tick), 4.14, forest_x(tick), 4.18)
    text_at(forest_x(tick), 4.29, sub("^-", "−", as.character(tick)), 7.1, align = "centre")
  }

  # A muted cue says which direction is which, so the estimates need no plus signs.
  text_at(forest_x(0) - 0.08, 4.43, "← Higher with portal", 7.1, colour = muted, align = "right")
  text_at(forest_x(0) + 0.08, 4.43, "Higher with telephone →", 7.1, colour = muted)
}

ragg::agg_png("figure-example.png", width = page_width, height = page_height,
              units = "in", res = 300, background = "white")
draw_figure()
invisible(dev.off())
cairo_pdf("figure-example.pdf", width = page_width, height = page_height, family = "Arial")
draw_figure()
invisible(dev.off())
