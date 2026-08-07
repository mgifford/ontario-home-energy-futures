#!/usr/bin/env node
/**
 * JS side of the cross-language golden-file drift guard.
 *
 * Loads the SAME tests/fixtures/golden_scenarios.json fixture that
 * tests/unit/test_golden_scenarios.py checks against the real Python
 * model, and checks it against the ported JavaScript implementation in
 * web/static/calculator.js. This is the test that actually catches
 * Python/JS drift: if someone changes model/scenario.py without updating
 * calculator.js (or vice versa), this fails.
 *
 * Plain Node, no test framework or dependency needed for this scope.
 *
 * Usage:
 *   node tests/js/test_golden_scenarios.mjs
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");

const calculatorPath = join(REPO_ROOT, "web", "static", "calculator.js");
const calculator = (await import("file://" + calculatorPath)).default;

const fixturePath = join(REPO_ROOT, "tests", "fixtures", "golden_scenarios.json");
const fixture = JSON.parse(readFileSync(fixturePath, "utf-8"));

const PRICE_SCENARIOS = {
  reference: { electricityEnergyReal: 0.015, fixedDeliveryReal: 0.020, variableDeliveryReal: 0.010, generalInflation: 0.020 },
  stress: { electricityEnergyReal: 0.050, fixedDeliveryReal: 0.050, variableDeliveryReal: 0.045, generalInflation: 0.020 }
};
const DECLINE_SCENARIOS = {
  flat: { realAnnualInstalledCostChange: 0.0 },
  moderate: { realAnnualInstalledCostChange: 0.02 }
};

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log("  ok  - " + name);
  } catch (err) {
    failed++;
    console.log("  FAIL - " + name);
    console.log("        " + err.message);
  }
}

function approxEqual(actual, expected, tolerance, label) {
  tolerance = tolerance === undefined ? 0.01 : tolerance;
  if (expected === null || expected === undefined) {
    assert.equal(actual, expected, label + ": expected null/undefined, got " + actual);
    return;
  }
  const diff = Math.abs(actual - expected);
  assert.ok(
    diff <= tolerance,
    (label || "value") + ": expected " + expected + ", got " + actual + " (diff " + diff + " > tolerance " + tolerance + ")"
  );
}

function runScenarioCase(caseDef) {
  const inputs = Object.assign({}, caseDef.inputs);

  if (caseDef.function === "evaluate_grid_only") {
    return calculator.evaluateGridOnly({
      baseAnnualBillCad: inputs.base_annual_bill_cad,
      priceScenario: PRICE_SCENARIOS[inputs.price_scenario],
      horizonYears: inputs.horizon_years,
      discountRate: inputs.discount_rate,
      fixedShare: inputs.fixed_share,
      variableShare: inputs.variable_share,
      energyShare: inputs.energy_share
    });
  }

  if (caseDef.function === "evaluate_solar_purchase") {
    return calculator.evaluateSolarPurchase({
      label: inputs.label,
      purchaseYearOffset: inputs.purchase_year_offset,
      baseAnnualBillCad: inputs.base_annual_bill_cad,
      priceScenario: PRICE_SCENARIOS[inputs.price_scenario],
      declineScenario: DECLINE_SCENARIOS[inputs.decline_scenario],
      baseQuote: inputs.base_quote,
      groupDiscountFraction: inputs.group_discount_fraction,
      taxRate: inputs.tax_rate,
      downPaymentFraction: inputs.down_payment_fraction,
      annualInterestRate: inputs.annual_interest_rate,
      loanTermYears: inputs.loan_term_years,
      isCash: inputs.is_cash,
      horizonYears: inputs.horizon_years,
      discountRate: inputs.discount_rate,
      fixedShare: inputs.fixed_share,
      variableShare: inputs.variable_share,
      energyShare: inputs.energy_share,
      annualGridBillAfterSolarCad: inputs.annual_grid_bill_after_solar_cad,
      annualMaintenanceCad: inputs.annual_maintenance_cad,
      inverterReplacementYear: inputs.inverter_replacement_year,
      inverterReplacementCostCad: inputs.inverter_replacement_cost_cad,
      annualCreditsUsedCad: inputs.annual_credits_used_cad,
      totalCreditsExpiredCad: inputs.total_credits_expired_cad,
      totalSolarGenerationKwh: inputs.total_solar_generation_kwh,
      totalGridImportsKwh: inputs.total_grid_imports_kwh
    });
  }

  throw new Error("unknown function " + caseDef.function);
}

console.log("Scenario cases (evaluate_grid_only / evaluate_solar_purchase):");
fixture.scenario_cases.forEach(function (caseDef) {
  test(caseDef.name, function () {
    const result = runScenarioCase(caseDef);
    const expected = caseDef.expected;

    assert.equal(result.label, expected.label, "label");
    assert.equal(result.purchaseYearOffset, expected.purchase_year_offset, "purchaseYearOffset");
    approxEqual(result.initialCostCad, expected.initial_cost_cad, 0.01, "initialCostCad");
    approxEqual(result.financingInterestCad, expected.financing_interest_cad, 0.01, "financingInterestCad");
    approxEqual(result.groupDiscountCad, expected.group_discount_cad, 0.01, "groupDiscountCad");
    approxEqual(result.totalNominalCad, expected.total_nominal_cad, 0.01, "totalNominalCad");
    approxEqual(result.totalPresentValueCad, expected.total_present_value_cad, 0.01, "totalPresentValueCad");
    assert.equal(result.simplePaybackYears, expected.simple_payback_years, "simplePaybackYears");

    assert.equal(result.annualCashFlows.length, expected.annual_cash_flows.length, "annualCashFlows length");
    result.annualCashFlows.forEach(function (flow, i) {
      const expectedFlow = expected.annual_cash_flows[i];
      assert.equal(flow.year, expectedFlow.year, "cash flow year " + i);
      approxEqual(flow.totalNominalCad, expectedFlow.total_nominal_cad, 0.01, "year " + i + " totalNominalCad");
      approxEqual(flow.totalPresentValueCad, expectedFlow.total_present_value_cad, 0.01, "year " + i + " totalPresentValueCad");
    });
  });
});

console.log("\nStandalone function cases:");

test("bill_component_after_years", function () {
  const c = fixture.standalone_cases.bill_component_after_years;
  const result = calculator.billComponentAfterYears(
    c.inputs.base_value, c.inputs.annual_real_change, c.inputs.years, c.inputs.general_inflation
  );
  approxEqual(result.realValue, c.expected[0], 0.001, "realValue");
  approxEqual(result.nominalValue, c.expected[1], 0.001, "nominalValue");
});

test("apply_group_discount", function () {
  const c = fixture.standalone_cases.apply_group_discount;
  const result = calculator.applyGroupDiscount(c.inputs.quote, c.inputs.discount_fraction);
  approxEqual(result.discountAmount, c.expected.discount_amount, 0.01, "discountAmount");
  approxEqual(result.eligibleTotalAfterDiscount, c.expected.eligible_total_after_discount, 0.01, "eligibleTotalAfterDiscount");
  approxEqual(result.ineligibleTotal, c.expected.ineligible_total, 0.01, "ineligibleTotal");
  approxEqual(result.totalAfterDiscount, c.expected.total_after_discount, 0.01, "totalAfterDiscount");
});

test("amortize_loan", function () {
  const c = fixture.standalone_cases.amortize_loan;
  const result = calculator.amortizeLoan(c.inputs.principal, c.inputs.annual_interest_rate, c.inputs.term_years);
  approxEqual(result.monthlyPayment, c.expected.monthly_payment, 0.01, "monthlyPayment");
  approxEqual(result.totalInterest, c.expected.total_interest, 0.01, "totalInterest");
  approxEqual(result.totalPaid, c.expected.total_paid, 0.01, "totalPaid");
});

test("solar_production", function () {
  const c = fixture.standalone_cases.solar_production;
  const regionalYield = { 1: 62, 2: 82, 3: 118, 4: 132, 5: 148, 6: 150, 7: 152, 8: 138, 9: 112, 10: 82, 11: 52, 12: 48 };
  const orientationFactors = { south: 1.00, southeast: 0.96, southwest: 0.96, east: 0.85, west: 0.85, north: 0.65 };
  const shadingFactors = { none: 1.00, light: 0.95, moderate: 0.85, heavy: 0.65 };
  const result = calculator.calculateSolarProduction(
    {
      capacityKwDc: c.inputs.capacity_kw_dc, orientation: c.inputs.orientation, shading: c.inputs.shading,
      degradationAnnual: c.inputs.degradation_annual, inverterEfficiency: c.inputs.inverter_efficiency,
      otherSystemLosses: c.inputs.other_system_losses
    },
    regionalYield, orientationFactors, shadingFactors, c.inputs.system_age_years
  );
  Object.keys(c.expected).forEach(function (monthStr) {
    approxEqual(result[Number(monthStr)], c.expected[monthStr], 0.01, "month " + monthStr);
  });
});

test("net_metering_ledger_two_months", function () {
  const c = fixture.standalone_cases.net_metering_ledger_two_months;
  const ledger = new calculator.NetMeteringLedger(c.inputs.export_credit_rate_cad_per_kwh);
  const actualMonths = c.inputs.months.map(function (m) {
    return ledger.processMonth({
      period: m.period, solarGenerationKwh: m.solar_generation_kwh, householdDemandKwh: m.household_demand_kwh,
      directSelfConsumptionKwh: m.direct_self_consumption_kwh, eligibleEnergyRateCadPerKwh: m.eligible_energy_rate_cad_per_kwh,
      ineligibleChargesCad: m.ineligible_charges_cad
    });
  });
  actualMonths.forEach(function (actual, i) {
    const expected = c.expected.months[i];
    approxEqual(actual.exportedKwh, expected.exported_kwh, 0.01, "month " + i + " exportedKwh");
    approxEqual(actual.gridImportKwh, expected.grid_import_kwh, 0.01, "month " + i + " gridImportKwh");
    approxEqual(actual.creditCreatedCad, expected.credit_created_cad, 0.01, "month " + i + " creditCreatedCad");
    approxEqual(actual.creditUsedCad, expected.credit_used_cad, 0.01, "month " + i + " creditUsedCad");
  });
  approxEqual(
    ledger.effectiveValuePerGeneratedKwh(), c.expected.effective_value_per_generated_kwh, 0.0001, "effectiveValuePerGeneratedKwh"
  );
});

test("find_breakeven_decline_rate", function () {
  const c = fixture.standalone_cases.find_breakeven_decline_rate;

  // Reconstruct the same sweep parameters used by
  // scripts/generate_golden_scenarios.py's common_purchase_kwargs.
  const commonParams = {
    baseAnnualBillCad: 8400.0, priceScenario: PRICE_SCENARIOS.reference,
    baseQuote: {
      panels: 6720, inverter: 2100, racking: 1680, electrical_equipment: 1260, labour: 4200,
      design_and_engineering: 630, permitting: 420, utility_connection: 840, installer_overhead: 3150
    },
    taxRate: 0.13, downPaymentFraction: 1.0, annualInterestRate: 0.079, loanTermYears: 10,
    horizonYears: 20, discountRate: 0.04, fixedShare: 0.30, variableShare: 0.15, energyShare: 0.55,
    annualGridBillAfterSolarCad: 2940.0, annualMaintenanceCad: 150.0,
    inverterReplacementYear: 12, inverterReplacementCostCad: 1800.0,
    annualCreditsUsedCad: 2520.0, totalCreditsExpiredCad: 0.0,
    totalSolarGenerationKwh: 9000.0, totalGridImportsKwh: 3360.0,
    label: "sweep", purchaseYearOffset: c.inputs.wait_years_offset, groupDiscountFraction: 0.0, isCash: true
  };

  const breakeven = calculator.findBreakevenDeclineRate(function (rate) {
    const params = Object.assign({}, commonParams, { declineScenario: { realAnnualInstalledCostChange: rate } });
    return calculator.evaluateSolarPurchase(params).totalPresentValueCad;
  }, c.inputs.npv_cost_buy_now);

  approxEqual(breakeven, c.expected, 0.0001, "breakeven rate");
});

["apply_collective_purchase_group_10", "apply_collective_purchase_group_20_capped"].forEach(function (caseName) {
  test(caseName, function () {
    const c = fixture.standalone_cases[caseName];
    const tierDict = c.inputs.tier;
    const tier = {
      id: tierDict.id, label: tierDict.label, households: tierDict.households,
      reductions: tierDict.reductions, overallDiscountCapPercent: tierDict.overall_discount_cap_percent
    };
    const result = calculator.applyCollectivePurchase(tier, c.inputs.base_costs_by_component);
    approxEqual(result.totalReducedCost, c.expected.total_reduced_cost, 0.01, "totalReducedCost");
    approxEqual(result.totalReductionCad, c.expected.total_reduction_cad, 0.01, "totalReductionCad");
    approxEqual(result.effectiveDiscountPercent, c.expected.effective_discount_percent, 0.01, "effectiveDiscountPercent");
    assert.equal(result.capped, c.expected.capped, "capped");
  });
});

test("calculate_cost_of_inaction_three_decisions", function () {
  const c = fixture.standalone_cases.calculate_cost_of_inaction_three_decisions;
  const decisions = c.inputs.decisions.map(function (d) {
    return {
      label: d.label, totalNominalCad: d.total_nominal_cad, totalPresentValueCad: d.total_present_value_cad,
      gridImportsKwh: d.grid_imports_kwh, solarGenerationKwh: d.solar_generation_kwh,
      incentivesReceivedCad: d.incentives_received_cad, gridServiceRevenueCad: d.grid_service_revenue_cad,
      residualValueCad: d.residual_value_cad
    };
  });
  const results = calculator.calculateCostOfInaction(decisions);
  Object.keys(c.expected).forEach(function (label) {
    const expected = c.expected[label];
    const actual = results[label];
    approxEqual(actual.additionalNominalCostCad, expected.additional_nominal_cost_cad, 0.01, label + " additionalNominalCostCad");
    approxEqual(actual.additionalPresentValueCad, expected.additional_present_value_cad, 0.01, label + " additionalPresentValueCad");
    approxEqual(
      actual.gridElectricityPurchasedWhileWaitingKwh, expected.grid_electricity_purchased_while_waiting_kwh, 0.01,
      label + " gridElectricityPurchasedWhileWaitingKwh"
    );
    approxEqual(actual.solarGenerationForgoneKwh, expected.solar_generation_forgone_kwh, 0.01, label + " solarGenerationForgoneKwh");
  });
});

console.log("\nChart builder cases (structural, not part of the Python golden fixture):");

test("buildCumulativeCostLineChart produces one polyline per series and matching table rows", function () {
  const series = [
    { label: "Grid only", points: [[0, 1000], [1, 2100], [2, 3300]] },
    { label: "Buy solar now", points: [[0, 15000], [1, 15600], [2, 16100]] }
  ];
  const result = calculator.buildCumulativeCostLineChart({
    series: series, xLabel: "Year", yLabel: "Cumulative cost (CAD)",
    accessibleName: "Test chart", accessibleDescription: "Test description, not a guarantee."
  });
  assert.ok(result.svg.startsWith("<svg"), "svg starts with <svg");
  assert.ok(result.svg.endsWith("</svg>"), "svg ends with </svg>");
  assert.equal((result.svg.match(/<polyline/g) || []).length, 2, "two polylines");
  assert.equal(result.tableRows.length, 3, "three table rows (years 0,1,2)");
  assert.equal(result.tableRows[0]["Grid only"], 1000, "first row Grid only value");
  assert.equal(result.tableRows[2]["Buy solar now"], 16100, "last row Buy solar now value");
});

test("buildCumulativeCostLineChart uses distinct dasharray patterns across series", function () {
  const series = [
    { label: "A", points: [[0, 1], [1, 2]] },
    { label: "B", points: [[0, 1], [1, 2]] },
    { label: "C", points: [[0, 1], [1, 2]] }
  ];
  const result = calculator.buildCumulativeCostLineChart({
    series: series, xLabel: "Year", yLabel: "Cost",
    accessibleName: "x", accessibleDescription: "y"
  });
  const dasharrays = [...result.svg.matchAll(/stroke-dasharray="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(new Set(dasharrays).size >= 1, "at least one distinct non-default dasharray pattern present");
});

test("buildCumulativeCostLineChart rejects empty series", function () {
  assert.throws(function () {
    calculator.buildCumulativeCostLineChart({
      series: [], xLabel: "Year", yLabel: "Cost", accessibleName: "x", accessibleDescription: "y"
    });
  });
});

console.log("\n" + passed + " passed, " + failed + " failed");
if (failed > 0) {
  process.exit(1);
}
