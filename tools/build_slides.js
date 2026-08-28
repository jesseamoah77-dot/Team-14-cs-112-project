/*
 * Build the final presentation deck.
 *
 *     node tools/build_slides.js
 *
 * Writes docs/cs112-final-presentation.pptx. Chart images come from
 * 01-grid-analysis/outputs/ (run the notebooks first if that folder is empty);
 * app screenshots live in docs/slide-assets/. Speaker notes carry what to say -
 * presenters should rehearse from the notes, not read the slides.
 *
 * If the require below fails:  npm install pptxgenjs   (from the tools/ folder)
 */

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const OUTPUTS = path.join(ROOT, "01-grid-analysis", "outputs");
const ASSETS = path.join(ROOT, "docs", "slide-assets");
const OUT_FILE = path.join(ROOT, "docs", "cs112-final-presentation.pptx");

// Palette: navy carries the deck, ice for panels, amber as the single accent.
const NAVY = "1F2A5C";
const NAVY_DARK = "141C40";
const ICE = "D7E3F7";
const ICE_SOFT = "EEF3FB";
const AMBER = "E8A33D";
const INK = "222833";
const MUTED = "5A6472";
const WHITE = "FFFFFF";
const GREEN = "3E8E5C";
const RED = "C0392B";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };

const W = 13.33;
const H = 7.5;
const MARGIN = 0.6;

function assertExists(file) {
  if (!fs.existsSync(file)) {
    console.error(`missing image: ${file}\nRun the analysis notebooks to regenerate outputs/.`);
    process.exit(1);
  }
  return file;
}

// ---------------------------------------------------------------- helpers

function darkSlide(kicker, title, subtitle, notes) {
  const slide = pres.addSlide();
  slide.background = { color: NAVY_DARK };
  slide.addText(kicker, {
    x: MARGIN, y: 2.35, w: W - 2 * MARGIN, h: 0.4,
    fontSize: 16, color: AMBER, bold: true, charSpacing: 2, margin: 0,
  });
  slide.addText(title, {
    x: MARGIN, y: 2.75, w: W - 2 * MARGIN, h: 1.4,
    fontSize: 44, color: WHITE, bold: true, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: MARGIN, y: 4.2, w: W - 2 * MARGIN, h: 0.9,
      fontSize: 18, color: ICE, margin: 0,
    });
  }
  if (notes) slide.addNotes(notes);
  return slide;
}

function contentSlide(title, notes) {
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  slide.addText(title, {
    x: MARGIN, y: 0.45, w: W - 2 * MARGIN, h: 0.75,
    fontSize: 32, color: NAVY, bold: true, margin: 0,
  });
  if (notes) slide.addNotes(notes);
  return slide;
}

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill }, line: { type: "none" }, rectRadius: 0.08,
  });
}

function statCallout(slide, x, y, w, value, label, valueColor = NAVY) {
  card(slide, x, y, w, 1.55, ICE_SOFT);
  slide.addText(value, {
    x: x + 0.15, y: y + 0.12, w: w - 0.3, h: 0.85,
    fontSize: 40, bold: true, color: valueColor, align: "center", margin: 0,
  });
  slide.addText(label, {
    x: x + 0.15, y: y + 0.98, w: w - 0.3, h: 0.5,
    fontSize: 12.5, color: MUTED, align: "center", margin: 0,
  });
}

function bullets(slide, items, opts) {
  slide.addText(
    items.map((text, i) => ({
      text,
      options: { bullet: { code: "2022", indent: 12 }, breakLine: i < items.length - 1 },
    })),
    { fontSize: 14.5, color: INK, paraSpaceAfter: 8, valign: "top", margin: 0, ...opts },
  );
}

function flowStep(slide, x, y, w, h, label, sub, fill, textColor) {
  card(slide, x, y, w, h, fill);
  slide.addText(label, {
    x: x + 0.08, y: y + 0.1, w: w - 0.16, h: 0.4,
    fontSize: 14, bold: true, color: textColor, align: "center", margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x: x + 0.08, y: y + 0.5, w: w - 0.16, h: h - 0.6,
      fontSize: 10.5, color: textColor === WHITE ? ICE : NAVY, align: "center", margin: 0,
    });
  }
}

function arrow(slide, x, y, w) {
  slide.addShape(pres.ShapeType.rightArrow, {
    x, y, w, h: 0.28, fill: { color: AMBER }, line: { type: "none" },
  });
}

// ================================================================ 1 · title
{
  const slide = pres.addSlide();
  slide.background = { color: NAVY_DARK };
  slide.addText("CS 112 · COMPUTER PROGRAMMING FOR CS · SUMMER 2026", {
    x: MARGIN, y: 1.9, w: W - 2 * MARGIN, h: 0.4,
    fontSize: 15, color: AMBER, bold: true, charSpacing: 2, margin: 0,
  });
  slide.addText("Grid Data to Working Systems", {
    x: MARGIN, y: 2.35, w: W - 2 * MARGIN, h: 1.0, fontSize: 48, color: WHITE, bold: true, margin: 0,
  });
  slide.addText(
    "National electricity grid network analysis · GridCare-Lite · ClinicCare-Lite",
    { x: MARGIN, y: 3.45, w: W - 2 * MARGIN, h: 0.5, fontSize: 20, color: ICE, margin: 0 });
  const chips = [
    ["10 / 44 / 55", "utilities · substations · lines"],
    ["3", "applications built"],
    ["134", "automated tests"],
  ];
  chips.forEach(([v, l], i) => {
    const x = MARGIN + i * 3.1;
    card(slide, x, 4.6, 2.8, 1.3, NAVY);
    slide.addText(v, { x: x + 0.1, y: 4.72, w: 2.6, h: 0.6, fontSize: 28, bold: true, color: AMBER, align: "center", margin: 0 });
    slide.addText(l, { x: x + 0.1, y: 5.32, w: 2.6, h: 0.45, fontSize: 11.5, color: ICE, align: "center", margin: 0 });
  });
  slide.addNotes(
    "Add team member names to this slide before presenting. Opening line: one dataset "
    + "about Ghana's power grid, taken all the way from raw CSVs to analysis, then two "
    + "working applications in two different domains. Everything shown is reproducible "
    + "from the repository.");
}

// ================================================================ 2 · at a glance
{
  const slide = contentSlide("One project, three connected components",
    "The connection matters: the cleaned substation data from component 1 becomes the "
    + "reference data GridCare-Lite validates outages against. ClinicCare-Lite reuses the "
    + "engineering approach - logic layer, role checks, tests - in a domain where privacy "
    + "is the point.");
  const cards = [
    ["1 · Grid analysis", "Ghana's grid as a graph", [
      "Clean, validate, merge three CSVs",
      "NetworkX: centrality, communities, bridges",
      "N-1 contingency: remove each substation",
      "Folium map + Streamlit dashboard",
    ], "pandas · NetworkX · Plotly"],
    ["2 · GridCare-Lite", "Outage & maintenance desktop app", [
      "Log outages against real substations",
      "Work orders: assign, schedule, complete",
      "4 roles, enforced in the service layer",
      "Audit trail + live reports",
    ], "Tkinter · SQLite · bcrypt"],
    ["3 · ClinicCare-Lite", "Clinic administration web app", [
      "Health tasks, uploads, categorical review",
      "Messaging, announcements, reminders",
      "Strictly administrative - never diagnostic",
      "Private engagement, aggregate analytics",
    ], "Flask · Bootstrap · JSON"],
  ];
  cards.forEach(([head, sub, items, stack], i) => {
    const x = MARGIN + i * 4.14;
    card(slide, x, 1.45, 3.9, 5.0, ICE_SOFT);
    slide.addText(head, { x: x + 0.25, y: 1.7, w: 3.4, h: 0.45, fontSize: 19, bold: true, color: NAVY, margin: 0 });
    slide.addText(sub, { x: x + 0.25, y: 2.15, w: 3.4, h: 0.4, fontSize: 13, italic: true, color: MUTED, margin: 0 });
    bullets(slide, items, { x: x + 0.25, y: 2.65, w: 3.45, h: 2.9, fontSize: 13 });
    slide.addText(stack, { x: x + 0.25, y: 5.85, w: 3.4, h: 0.35, fontSize: 11.5, bold: true, color: AMBER, margin: 0 });
  });
  slide.addText("Data flows left to right: the analysis output is the applications' reference data.",
    { x: MARGIN, y: 6.75, w: W - 2 * MARGIN, h: 0.35, fontSize: 12.5, italic: true, color: MUTED, margin: 0 });
}

// ================================================================ 3 · divider C1
darkSlide("COMPONENT 1", "National Electricity Grid Network Analysis",
  "44 substations, 55 lines, one question: which failures would split the country?",
  "Section handoff - whoever presents component 1 takes over here.");

// ================================================================ 4 · data
{
  const slide = contentSlide("The dataset: real geography, generated numbers",
    "Key caveat is a grading criterion: utility names and towns are real, every number "
    + "is synthetic from a seeded generator - so all teams work on identical data and "
    + "nothing here describes Ghana's actual grid. Totals: 6,946 MVA, 5,462 km of lines, "
    + "commissioning years 1967-2022.");
  statCallout(slide, MARGIN, 1.5, 2.6, "10", "utilities - ECG, NEDCo, GRIDCo, VRA + WAPP neighbours");
  statCallout(slide, MARGIN + 2.8, 1.5, 2.6, "44", "substations with region, voltage, capacity, age");
  statCallout(slide, MARGIN + 5.6, 1.5, 2.6, "55", "transmission & distribution lines");
  statCallout(slide, MARGIN + 8.4, 1.5, 2.6, "seed 42", "identical CSVs for every team, every run");
  card(slide, MARGIN, 3.4, 11.0, 1.15, ICE);
  slide.addText(
    [{ text: "Synthetic by design.  ", options: { bold: true, color: NAVY } },
     { text: "Real utility names and towns, generated capacities, connections and ages. "
       + "Findings are statements about this dataset - never about Ghana's actual grid.",
       options: { color: INK } }],
    { x: MARGIN + 0.25, y: 3.55, w: 10.5, h: 0.85, fontSize: 13.5, margin: 0 });
  bullets(slide, [
    "utilities.csv - who operates (like airlines.csv in the OpenFlights layout)",
    "substations.csv - the nodes: location, region, voltage tier, capacity, year, status",
    "lines.csv - the edges: endpoints, voltage, length, capacity, operational status",
  ], { x: MARGIN, y: 4.85, w: 11.5, h: 1.7 });
}

// ================================================================ 5 · cleaning
{
  const slide = contentSlide("Cleaning and validation: verified, not assumed",
    "The pipeline treats generated data like a real asset register export. Every check "
    + "logs a result even when it finds nothing - a step that found nothing is still a "
    + "step we checked. The planted-defect tests prove the validators actually catch "
    + "orphaned lines and swapped coordinates.");
  bullets(slide, [
    "Missing-value tokens normalised, whitespace stripped, numerics coerced, duplicates dropped",
    "Primary keys unique; every line endpoint resolves to a real substation",
    "Coordinates inside West Africa - a swapped lat/lon would wreck every map and distance",
    "Categorical fields against expected sets; no self-loops; no future commissioning years",
    "Validators proven by tests that plant defects and assert they are caught",
  ], { x: MARGIN, y: 1.55, w: 6.6, h: 3.6 });
  card(slide, 7.5, 1.55, 5.2, 4.6, ICE_SOFT);
  slide.addText("The finding hiding in the row count", {
    x: 7.75, y: 1.8, w: 4.7, h: 0.5, fontSize: 17, bold: true, color: NAVY, margin: 0 });
  slide.addText([
    { text: "44", options: { fontSize: 44, bold: true, color: NAVY } },
    { text: "  substations in the register\n", options: { fontSize: 14, color: MUTED } },
    { text: "42", options: { fontSize: 44, bold: true, color: AMBER } },
    { text: "  nodes if you build the graph naively", options: { fontSize: 14, color: MUTED } },
  ], { x: 7.75, y: 2.35, w: 4.7, h: 1.7, margin: 0 });
  slide.addText(
    "Two substations have no lines at all - Conakry Hub and Savelugu. Building from the "
    + "edge list silently drops them (the brief's sample does). We add nodes first, keep "
    + "the isolates visible, and report them as a coverage finding.",
    { x: 7.75, y: 4.15, w: 4.7, h: 1.8, fontSize: 13, color: INK, margin: 0 });
}

// ================================================================ 6 · EDA
{
  const slide = contentSlide("Exploring the grid: where the assets are",
    "Left: Greater Accra leads with 6 substations; the single-substation 'regions' at the "
    + "bottom are cross-border WAPP points. Right: Mallam, Kumasi Central and Cape Coast "
    + "tie at 5 connections - remember those three names for the N-1 slide.");
  slide.addImage({ path: assertExists(path.join(OUTPUTS, "q1_substations_by_region.png")),
    x: MARGIN, y: 1.6, w: 6.0, h: 3.33 });
  slide.addImage({ path: assertExists(path.join(OUTPUTS, "q7_most_connected.png")),
    x: 6.9, y: 1.6, w: 5.85, h: 3.58 });
  card(slide, MARGIN, 5.55, 12.13, 1.25, ICE_SOFT);
  bullets(slide, [
    "Greater Accra densest (6); the northern third thinnest - and Savelugu's missing lines make it worse than it looks",
    "Most-connected: Mallam, Kumasi Central, Cape Coast at 5 lines each - counted across both endpoints",
  ], { x: MARGIN + 0.25, y: 5.7, w: 11.6, h: 1.0, fontSize: 13 });
}

// ================================================================ 7 · network map
{
  const slide = contentSlide("The grid as a graph",
    "One figure, whole story: nodes at real coordinates, sized by betweenness, coloured "
    + "by detected community, red ring = articulation point. The red chain down the "
    + "middle is the backbone. Communities come out as unions of adjacent regions - the "
    + "graph rediscovers geography.");
  slide.addImage({ path: assertExists(path.join(OUTPUTS, "n2_network_map.png")),
    x: MARGIN, y: 1.45, w: 7.3, h: 5.62 });
  const stats = [
    ["density", "0.064"], ["diameter", "14 hops"], ["avg path", "5.41 hops"],
    ["modularity", "0.730"], ["bridges", "21 (16 inter-regional)"], ["articulation points", "17"],
  ];
  stats.forEach(([l, v], i) => {
    const y = 1.5 + i * 0.92;
    card(slide, 8.3, y, 4.4, 0.78, i % 2 ? ICE_SOFT : ICE);
    slide.addText(l, { x: 8.55, y: y + 0.08, w: 2.1, h: 0.6, fontSize: 13, color: MUTED, margin: 0, valign: "middle" });
    slide.addText(v, { x: 10.4, y: y + 0.08, w: 2.2, h: 0.6, fontSize: 15, bold: true, color: NAVY, margin: 0, valign: "middle", align: "right" });
  });
}

// ================================================================ 8 · N-1 headline
{
  const slide = contentSlide("N-1 contingency: same degree, opposite consequences",
    "The headline finding. We removed every substation in turn, not just the busiest. "
    + "Mallam and Cape Coast both have 5 connections - the joint maximum. Losing Mallam "
    + "strands nobody; its links are redundant local mesh. Losing Cape Coast strands 21 "
    + "of the remaining 41 - it is a link in the only west-east chain. Degree cannot "
    + "tell you which failures matter; articulation analysis can. Cross-checked "
    + "brute-force removal against nx.articulation_points - exact match.");
  card(slide, MARGIN, 1.5, 5.6, 2.6, ICE_SOFT);
  slide.addText("Mallam", { x: 0.85, y: 1.7, w: 2.5, h: 0.45, fontSize: 18, bold: true, color: NAVY, margin: 0 });
  slide.addText("degree 5", { x: 0.85, y: 2.12, w: 2.5, h: 0.35, fontSize: 12.5, color: MUTED, margin: 0 });
  slide.addText("0", { x: 0.85, y: 2.4, w: 2.2, h: 1.2, fontSize: 60, bold: true, color: GREEN, margin: 0 });
  slide.addText("substations cut off", { x: 0.85, y: 3.6, w: 2.4, h: 0.35, fontSize: 11.5, color: MUTED, margin: 0 });
  slide.addText("Cape Coast", { x: 3.6, y: 1.7, w: 2.5, h: 0.45, fontSize: 18, bold: true, color: NAVY, margin: 0 });
  slide.addText("degree 5", { x: 3.6, y: 2.12, w: 2.5, h: 0.35, fontSize: 12.5, color: MUTED, margin: 0 });
  slide.addText("21", { x: 3.6, y: 2.4, w: 2.4, h: 1.2, fontSize: 60, bold: true, color: RED, margin: 0 });
  slide.addText("of 41 remaining - half the country", { x: 3.6, y: 3.6, w: 2.6, h: 0.35, fontSize: 11.5, color: MUTED, margin: 0 });
  slide.addText(
    "Connection count is not criticality. What matters is whether a node's links are "
    + "redundant mesh or the only chain - which is what betweenness and articulation "
    + "points measure.",
    { x: MARGIN, y: 4.4, w: 5.6, h: 1.6, fontSize: 14, italic: true, color: INK, margin: 0 });
  slide.addChart(pres.ChartType.bar, [{
    name: "Substations cut off",
    labels: ["Cape Coast", "Takoradi", "Koforidua", "Kumasi Central", "Ho", "Sunyani", "Achimota"],
    values: [21, 19, 17, 15, 13, 9, 8],
  }], {
    x: 6.7, y: 1.5, w: 6.0, h: 5.3, barDir: "bar",
    chartColors: [NAVY], showLegend: false,
    showTitle: true, title: "Worst single-substation losses", titleFontSize: 14, titleColor: NAVY,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11,
    catAxisLabelColor: INK, catAxisLabelFontSize: 11,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10,
    valGridLine: { color: "DDDDDD", size: 1 }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 24,
  });
}

// ================================================================ 9 · corridors + dashboard
{
  const slide = contentSlide("Every inter-regional corridor is a bridge",
    "Merged-data analysis found each region pair joined by exactly one line; the bridge "
    + "analysis confirms all 16 inter-regional corridors are bridges - redundancy exists "
    + "inside regions and nowhere between them. That is the clearest investment signal "
    + "this analysis can produce. Everything lands in an interactive Folium map and a "
    + "four-tab Streamlit dashboard - live demo at the end.");
  slide.addImage({ path: assertExists(path.join(OUTPUTS, "m3_region_pairs.png")),
    x: MARGIN, y: 1.55, w: 6.3, h: 4.2 });
  bullets(slide, [
    "Each corridor = one line = one bridge: no alternative route between any two regions",
    "Interactive layers: substations by voltage, lines by status, lines by utility (Folium)",
    "Streamlit dashboard: overview, filterable network, capacity map, N-1 ranking",
    "Line lengths verified against coordinates - routing factor 1.05-1.30, none impossible",
  ], { x: 7.3, y: 1.7, w: 5.4, h: 3.6 });
  card(slide, 7.3, 5.35, 5.4, 1.0, ICE);
  slide.addText("Structural proxies on synthetic data - where a real power-flow study would look first, not operational findings.",
    { x: 7.55, y: 5.5, w: 4.9, h: 0.7, fontSize: 12.5, italic: true, color: NAVY, margin: 0 });
}

// ================================================================ 10 · divider C2
darkSlide("COMPONENT 2", "GridCare-Lite",
  "The outage-to-resolution workflow as a desktop application - four roles, one audit trail.",
  "Section handoff to the GridCare presenter.");

// ================================================================ 11 · gridcare overview
{
  const slide = contentSlide("Four roles, one workflow, rules in one place",
    "Design decision worth defending: the GUI never touches SQL. Every operation goes "
    + "through services.py, which re-checks the caller's role and the legal status "
    + "transitions - hiding a button is presentation, the service check is the security. "
    + "Substations come from the component-1 cleaned data, so an outage physically "
    + "cannot reference an asset that does not exist.");
  const roles = [
    ["Engineer", "logs outages against real substations, with severity"],
    ["Administrator", "creates work orders, assigns technician + date"],
    ["Technician", "sees only their own queue; starts and completes work"],
    ["Customer service", "logs complaints, links them to known outages"],
  ];
  roles.forEach(([r, d], i) => {
    const x = MARGIN + i * 3.1;
    card(slide, x, 1.55, 2.85, 1.7, ICE_SOFT);
    slide.addText(r, { x: x + 0.18, y: 1.72, w: 2.5, h: 0.4, fontSize: 15, bold: true, color: NAVY, margin: 0 });
    slide.addText(d, { x: x + 0.18, y: 2.14, w: 2.55, h: 1.0, fontSize: 11.5, color: INK, margin: 0 });
  });
  slide.addText("Outage lifecycle", { x: MARGIN, y: 3.6, w: 4, h: 0.4, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  flowStep(slide, MARGIN, 4.05, 2.2, 0.95, "Open", "engineer reports", NAVY, WHITE);
  arrow(slide, 2.9, 4.38, 0.5);
  flowStep(slide, 3.5, 4.05, 2.2, 0.95, "In Progress", "technician starts", NAVY, WHITE);
  arrow(slide, 5.8, 4.38, 0.5);
  flowStep(slide, 6.4, 4.05, 2.2, 0.95, "Resolved", "work completed", GREEN, WHITE);
  slide.addText("Work order", { x: MARGIN, y: 5.25, w: 4, h: 0.4, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  flowStep(slide, MARGIN, 5.7, 2.2, 0.95, "Pending", "admin creates", ICE, null);
  arrow(slide, 2.9, 6.03, 0.5);
  flowStep(slide, 3.5, 5.7, 2.2, 0.95, "Scheduled", "technician + date", ICE, null);
  arrow(slide, 5.8, 6.03, 0.5);
  flowStep(slide, 6.4, 5.7, 2.2, 0.95, "Completed", "resolves the outage", GREEN, WHITE);
  card(slide, 9.3, 4.05, 3.4, 2.6, ICE_SOFT);
  slide.addText("Enforced, not suggested", { x: 9.55, y: 4.25, w: 2.9, h: 0.4, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  slide.addText(
    "Illegal transitions are refused with the allowed states named. Completing a work "
    + "order resolves its outage in the same step - the two records can never disagree. "
    + "Every change lands in status_history: who, when, old, new.",
    { x: 9.55, y: 4.65, w: 2.95, h: 1.9, fontSize: 11.5, color: INK, margin: 0 });
}

// ================================================================ 12 · gridcare screenshots
{
  const slide = contentSlide("The same system, seen by two roles",
    "Left: the admin sees five tabs and every outage. Right: technician Ama sees three "
    + "tabs and only her own two work orders - the filtering is in the service layer "
    + "query, not the widget. Acting on someone else's order by id is refused too, and "
    + "there is a test for exactly that.");
  slide.addImage({ path: assertExists(path.join(ASSETS, "gridcare-admin.png")),
    x: MARGIN, y: 1.7, w: 6.0, h: 3.8 });
  slide.addText("Administrator - all outages, five tabs", {
    x: MARGIN, y: 5.6, w: 6.0, h: 0.35, fontSize: 12, color: MUTED, align: "center", margin: 0 });
  slide.addImage({ path: assertExists(path.join(ASSETS, "gridcare-technician.png")),
    x: 6.9, y: 1.7, w: 6.0, h: 3.8 });
  slide.addText("Technician - own queue only, three tabs", {
    x: 6.9, y: 5.6, w: 6.0, h: 0.35, fontSize: 12, color: MUTED, align: "center", margin: 0 });
}

// ================================================================ 13 · gridcare reports + errors
{
  const slide = contentSlide("Reports that move, errors that explain",
    "Reports recompute from the database every time the tab is shown - resolve an outage "
    + "and the numbers move. The error cases are demo material: duplicate outage warning "
    + "with an are-you-sure, invalid dates including 2026-13-45, completion without "
    + "notes refused, wrong technician refused.");
  slide.addImage({ path: assertExists(path.join(ASSETS, "gridcare-reports.png")),
    x: MARGIN, y: 1.6, w: 6.6, h: 4.18 });
  bullets(slide, [
    "Open / In Progress / Resolved counts, unresolved by severity and region",
    "Average resolution time from the audit timestamps (27.0 h on seeded data)",
    "Duplicate guard: second outage on a substation asks 'separate incident?'",
    "Dates validated properly - 2026-13-45 and yesterday both refused",
    "Every failure path shows a message; nothing crashes the app",
  ], { x: 7.55, y: 1.75, w: 5.2, h: 4.2 });
}

// ================================================================ 14 · divider C3
darkSlide("COMPONENT 3", "ClinicCare-Lite",
  "Clinic administration on the web - where the hardest requirement is what the system must never do.",
  "Section handoff to the ClinicCare presenter.");

// ================================================================ 15 · scope boundary
{
  const slide = contentSlide("Administrative by design - never diagnostic",
    "The brief makes this a hard requirement and the rubric enforces it: a system that "
    + "interprets health data loses the marks regardless of code quality. Our boundary "
    + "is testable: review outcomes are categorical and a numeric grade is rejected as "
    + "invalid; the completeness checker has no code path comparing a value to a "
    + "threshold - a test submits an alarming reading and asserts silence.");
  card(slide, MARGIN, 1.7, 5.9, 3.3, ICE_SOFT);
  slide.addText("The system says", { x: 0.85, y: 1.95, w: 5.3, h: 0.45, fontSize: 17, bold: true, color: GREEN, margin: 0 });
  bullets(slide, [
    `"The 'Systolic' column is missing."`,
    `"The date field is empty on row 4."`,
    `"Submission received - on time."`,
    `"Reviewed - Needs Follow-up. Notes from your clinician: ..."`,
  ], { x: 0.85, y: 2.5, w: 5.3, h: 2.3, fontSize: 13.5 });
  card(slide, 6.85, 1.7, 5.9, 3.3, ICE_SOFT);
  slide.addText("The system never says", { x: 7.1, y: 1.95, w: 5.3, h: 0.45, fontSize: 17, bold: true, color: RED, margin: 0 });
  bullets(slide, [
    `"Your blood pressure is dangerous."`,
    "Any interpretation of a submitted value",
    "Any score, grade or risk rating on health data",
    "Any comparison of one patient with another",
  ], { x: 7.1, y: 2.5, w: 5.3, h: 2.3, fontSize: 13.5 });
  card(slide, MARGIN, 5.4, 12.13, 1.1, ICE);
  slide.addText(
    "Categorical review outcomes - Pending · Reviewed-Normal · Needs Follow-up · Escalated - "
    + "set only by the clinician, never computed. A numeric grade is rejected as invalid (tested).",
    { x: MARGIN + 0.25, y: 5.55, w: 11.6, h: 0.8, fontSize: 13.5, color: NAVY, margin: 0 });
}

// ================================================================ 16 · architecture
{
  const slide = contentSlide("Architecture: access control lives in one file",
    "Three Flask blueprints; every data touch goes through guards.py - two role "
    + "decorators plus ownership helpers. Foreign records 404 rather than 403, so a "
    + "response never confirms a record exists. Storage is JSON per the spec, behind a "
    + "store module doing atomic temp-file-and-replace writes under a lock - covers the "
    + "truncation bug the brief warns about, plus crash safety.");
  flowStep(slide, MARGIN, 1.7, 2.6, 1.1, "Browser", "Bootstrap + client-side validation", ICE, null);
  arrow(slide, 3.3, 2.1, 0.5);
  flowStep(slide, 3.9, 1.7, 2.9, 1.1, "Routes", "auth · clinician · patient", NAVY, WHITE);
  arrow(slide, 6.9, 2.1, 0.5);
  flowStep(slide, 7.5, 1.7, 2.5, 1.1, "guards.py", "roles + ownership", AMBER, null);
  arrow(slide, 10.1, 2.1, 0.5);
  flowStep(slide, 10.7, 1.7, 2.0, 1.1, "Models", "entities", NAVY, WHITE);
  flowStep(slide, 3.9, 3.3, 2.9, 1.0, "utils/", "validators · files · completeness · analytics", ICE_SOFT, null);
  flowStep(slide, 7.5, 3.3, 2.5, 1.0, "email", "dry-run outbox / SMTP", ICE_SOFT, null);
  flowStep(slide, 10.7, 3.3, 2.0, 1.0, "JSON store", "atomic writes", ICE_SOFT, null);
  bullets(slide, [
    "Patient A requesting patient B's record: 404 - existence not confirmed (tested)",
    "Wrong role on a URL: 403; no session: redirect to login (tested)",
    "Uploads: .txt/.csv/.pdf only, 5 MB cap, renamed patientID_taskID.ext, path-traversal refused",
    "Secrets only from .env; the app refuses to start without a real secret key",
  ], { x: MARGIN, y: 4.75, w: 12.0, h: 2.2 });
}

// ================================================================ 17 · workflow
{
  const slide = contentSlide("Submit → check → review → notify",
    "The completeness check runs on the raw bytes before anything is stored - an "
    + "incomplete file is rejected with the exact problems named and nothing persists. "
    + "Every step notifies in-app, with email alongside (dry-run outbox in demos). "
    + "Resubmission allowed before review and flagged; locked after.");
  const steps = [
    ["1 · Assign", "clinician creates task, patients notified"],
    ["2 · Submit", "upload checked: type, size, structure"],
    ["3 · Review", "categorical outcome + notes"],
    ["4 · Notify", "dashboard, inbox and email"],
  ];
  steps.forEach(([t, d], i) => {
    const x = MARGIN + i * 3.15;
    flowStep(slide, x, 1.65, 2.75, 1.3, t, d, i === 2 ? AMBER : NAVY, i === 2 ? null : WHITE);
    if (i < 3) arrow(slide, x + 2.78, 2.15, 0.34);
  });
  card(slide, MARGIN, 3.4, 12.13, 1.3, ICE_SOFT);
  slide.addText([
    { text: "Rejected with reasons:  ", options: { bold: true, color: NAVY } },
    { text: `"The 'Systolic' column is missing. Fix the issues above and submit again - `
      + `nothing was stored."  Structure only, meaning never.`, options: { color: INK } },
  ], { x: MARGIN + 0.25, y: 3.6, w: 11.6, h: 0.9, fontSize: 13.5, margin: 0 });
  bullets(slide, [
    "Appointments: booked by the clinician, reminded once 24 h ahead (send_reminders.py), attendance drives analytics",
    "Messaging: pairwise threads, 5-second polling, permanent 'not monitored - not for emergencies' notice",
    "Announcements: publish/expiry dates, urgent ones also emailed to every patient",
  ], { x: MARGIN, y: 5.0, w: 12.0, h: 1.9 });
}

// ================================================================ 18 · privacy
{
  const slide = contentSlide("Privacy engineering, not privacy promises",
    "Three deliberate designs. Engagement: points and streaks are visible only to their "
    + "owner - the module has exactly one read function and a test asserts no "
    + "leaderboard-shaped API exists; the brief's rationale: ranking patients leaks who "
    + "is keeping up with their care. Analytics: clinic aggregates only, no patient "
    + "named - asserted in a route test. Access: ownership helpers make cross-patient "
    + "reads unreachable, and unknown records are indistinguishable from forbidden ones.");
  const cards2 = [
    ["Private engagement", [
      "+10 EP on-time submission, +5 attendance",
      "Streak resets on a late submission",
      "Owner-only page - no ranking API exists",
      "Test asserts no leaderboard function",
    ]],
    ["Aggregate analytics", [
      "Completion rate, pending reviews, turnaround",
      "No-show rate by week from attendance",
      "No patient id or name on the page (tested)",
      "Patients see their own history only",
    ]],
    ["Scoped access", [
      "Foreign records 404 - existence hidden",
      "Threads strictly pairwise",
      "Inbox returns recipient-only mail",
      "Clinician limited to own clinic's patients",
    ]],
  ];
  cards2.forEach(([head, items], i) => {
    const x = MARGIN + i * 4.14;
    card(slide, x, 1.6, 3.9, 4.4, ICE_SOFT);
    slide.addText(head, { x: x + 0.25, y: 1.85, w: 3.4, h: 0.45, fontSize: 16.5, bold: true, color: NAVY, margin: 0 });
    bullets(slide, items, { x: x + 0.25, y: 2.4, w: 3.45, h: 3.4, fontSize: 12.5 });
  });
}

// ================================================================ 19 · testing
{
  const slide = contentSlide("134 automated tests, negative cases first",
    "Strategy: rules live in a logic layer, so most tests hit that layer directly; "
    + "route tests then verify the web boundary - status codes and who can reach what. "
    + "More failure-path tests than happy-path throughout, because the rubric's test "
    + "lists are about invalid input and unauthorised access. Fresh state per test: "
    + "in-memory SQLite for GridCare, temp-dir JSON stores for ClinicCare.");
  slide.addChart(pres.ChartType.bar, [{
    name: "Tests",
    labels: ["Grid data pipeline", "GridCare services", "ClinicCare core", "ClinicCare routes"],
    values: [16, 35, 59, 24],
  }], {
    x: MARGIN, y: 1.6, w: 6.2, h: 4.4, barDir: "bar",
    chartColors: [NAVY], showLegend: false,
    showTitle: true, title: "Tests by suite (134 total)", titleFontSize: 14, titleColor: NAVY,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 12,
    catAxisLabelColor: INK, catAxisLabelFontSize: 12,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10,
    valGridLine: { color: "DDDDDD", size: 1 }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 70,
  });
  bullets(slide, [
    "Every item on the brief's test lists mapped to a named test",
    "Validators proven against planted defects - orphaned line, swapped coordinates",
    "Security as assertions: cross-patient 404, wrong-role 403, pairwise-only threads",
    "Boundary as a test: alarming health value passes the checker with zero comment",
    "Manual GUI pass on top - which is what caught the path-separator defect",
  ], { x: 7.3, y: 1.75, w: 5.4, h: 4.4 });
}

// ================================================================ 20 · defects
{
  const slide = contentSlide("Defects we found, and what found them",
    "Six defects logged with causes, fixes and retests. The point "
    + "of this slide: three different nets caught three different bugs - tests, walking "
    + "the real UI, and writing the report. Each catch is exactly the reflection "
    + "material the rubric asks for.");
  const defects = [
    ["Found by writing a test", "D1 - misleading error order",
     "Starting an unassigned work order said 'assigned to a different technician'. "
     + "Status check now runs before ownership; the message names the real problem."],
    ["Found by walking the UI", "D2 - Windows path separators",
     "Stored submission paths used backslashes - display broke, JSON non-portable. "
     + "Invisible to tests; obvious in the browser. Paths now stored POSIX-style."],
    ["Found by writing the report", "D5 - number typed from memory",
     "Prose said 13 inter-regional lines; computed value is 16. Every number in prose "
     + "must come from output - corrected and logged."],
  ];
  defects.forEach(([how, title, body], i) => {
    const x = MARGIN + i * 4.14;
    card(slide, x, 1.6, 3.9, 4.5, ICE_SOFT);
    slide.addText(how, { x: x + 0.25, y: 1.85, w: 3.4, h: 0.4, fontSize: 12, bold: true, color: AMBER, margin: 0 });
    slide.addText(title, { x: x + 0.25, y: 2.3, w: 3.4, h: 0.75, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
    slide.addText(body, { x: x + 0.25, y: 3.1, w: 3.45, h: 2.8, fontSize: 12.5, color: INK, margin: 0 });
  });
}

// ================================================================ 21 · process + limits
{
  const slide = contentSlide("How we worked, and what we'd say honestly",
    "Left: the working process - feature branches and PRs with one review, meaning "
    + "commits, the docs pack in the repo, everything reproducible from clone to demo. "
    + "Right: limitations stated plainly - the rubric rewards knowing them. Future "
    + "work: SQLite behind ClinicCare's store interface, real load data for the grid, "
    + "appointment self-scheduling.");
  slide.addText("Process", { x: MARGIN, y: 1.55, w: 5, h: 0.45, fontSize: 18, bold: true, color: NAVY, margin: 0 });
  bullets(slide, [
    "Branch per feature, pull requests, one review before merge",
    "Commit messages that explain the why - the history reads as a build log",
    "Reports, diagrams, test plan and user guides live in docs/, versioned with the code",
    "Seeded data + pinned requirements: identical setup on every machine",
  ], { x: MARGIN, y: 2.1, w: 5.9, h: 4.2 });
  slide.addText("Limitations", { x: 7.0, y: 1.55, w: 5, h: 0.45, fontSize: 18, bold: true, color: NAVY, margin: 0 });
  bullets(slide, [
    "All grid numbers synthetic - structural proxies, not operational findings",
    "JSON storage has no indexing; the store interface was designed for a SQLite swap",
    "Polling, not WebSockets, for messaging - the spec allowed either",
    "Email exercised in dry-run; live SMTP deliberately kept out of coursework",
  ], { x: 7.0, y: 2.1, w: 5.7, h: 4.2 });
}

// ================================================================ 22 · close
{
  const slide = darkSlide("LIVE DEMO", "From outage to resolution, from task to review",
    "GridCare-Lite: engineer → admin → technician → resolved · ClinicCare-Lite: assign → submit → review → notified",
    "Hand off to the live demo. "
    + "Good closing line before questions: three systems, one discipline - rules in "
    + "one place, tests before screens, and honesty about what synthetic data can and "
    + "cannot say.");
  const chips = [["134", "tests passing"], ["3", "working systems"], ["6", "defects logged & fixed"]];
  chips.forEach(([v, l], i) => {
    const x = MARGIN + i * 3.1;
    card(slide, x, 5.3, 2.8, 1.3, NAVY);
    slide.addText(v, { x: x + 0.1, y: 5.42, w: 2.6, h: 0.6, fontSize: 28, bold: true, color: AMBER, align: "center", margin: 0 });
    slide.addText(l, { x: x + 0.1, y: 6.02, w: 2.6, h: 0.45, fontSize: 11.5, color: ICE, align: "center", margin: 0 });
  });
}

pres.writeFile({ fileName: OUT_FILE }).then(() => {
  const kb = (fs.statSync(OUT_FILE).size / 1024).toFixed(0);
  console.log(`${path.relative(ROOT, OUT_FILE)}: ${kb} KB`);
});
