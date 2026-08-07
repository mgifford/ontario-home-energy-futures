/**
 * Ontario Home Energy Futures - client-side calculator.
 *
 * Progressive enhancement only: every page works without this file (see
 * ACCESSIBILITY.md). This module re-implements the same bill/solar/
 * net-metering/financing math as the Python model in
 * src/ontario_home_energy_futures/model/ so that recalculation can happen
 * instantly in the browser with no server round-trip and no data leaving
 * the device.
 *
 * KEEPING THIS IN SYNC WITH PYTHON: this file mirrors
 * model/bill.py, model/solar.py, model/net_metering.py,
 * model/financing.py, model/decline.py, model/scenario.py, and
 * model/waiting.py. tests/fixtures/golden_scenarios.json is generated
 * FROM the real Python model's output (see
 * scripts/generate_golden_scenarios.py), and
 * tests/js/test_golden_scenarios.mjs checks the functions in this file
 * against that same fixture - if this file's math ever drifts from
 * Python's, that test fails. Run it after changing anything below:
 *   node tests/js/test_golden_scenarios.mjs
 *
 * No framework, no build step, no third-party dependency.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    // Node (used by tests/js/test_golden_scenarios.mjs).
    module.exports = factory();
  } else {
    // Browser.
    factory(root);
  }
})(typeof self !== "undefined" ? self : this, function (browserGlobal) {
  "use strict";

  var MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  // ---------------------------------------------------------------------
  // model/bill.py
  // ---------------------------------------------------------------------

  function calculateTouBill(consumptionKwh, hourlyShares, rates, monthIndex) {
    var energyCharge = 0;
    Object.keys(hourlyShares).forEach(function (period) {
      energyCharge += consumptionKwh * hourlyShares[period] * rates.tou[period];
    });
    var days = MONTH_DAYS[monthIndex];
    var fixedDelivery = rates.fixedDeliveryPerDay * days;
    var variableDelivery = consumptionKwh * rates.variableDeliveryPerKwh;
    var regulatory = consumptionKwh * rates.regulatoryPerKwh;
    var rebate = consumptionKwh * rates.rebatePerKwh;

    var preTax = energyCharge + fixedDelivery + variableDelivery + regulatory + rebate;
    var tax = preTax * rates.hstRate;
    var total = preTax + tax;

    return {
      energyCharge: energyCharge,
      fixedDelivery: fixedDelivery,
      variableDelivery: variableDelivery,
      regulatory: regulatory,
      rebate: rebate,
      tax: tax,
      total: total,
      effectiveCentsPerKwh: consumptionKwh ? (total / consumptionKwh) * 100 : 0
    };
  }

  var DEFAULT_TOU_HOURLY_SHARES = { off_peak: 0.6, mid_peak: 0.2, on_peak: 0.2 };

  // ---------------------------------------------------------------------
  // model/decline.py
  // ---------------------------------------------------------------------

  // mirrors model/decline.py::installed_cost_after_years
  function installedCostAfterYears(baseCost, annualRealDecline, years, generalInflation) {
    generalInflation = generalInflation || 0;
    var realCost = baseCost * Math.pow(1 - annualRealDecline, years);
    var nominalCost = realCost * Math.pow(1 + generalInflation, years);
    return { realCost: round2(realCost), nominalCost: round2(nominalCost) };
  }

  // mirrors model/decline.py::bill_component_after_years
  function billComponentAfterYears(baseValue, annualRealChange, years, generalInflation) {
    generalInflation = generalInflation || 0;
    var realValue = baseValue * Math.pow(1 + annualRealChange, years);
    var nominalValue = realValue * Math.pow(1 + generalInflation, years);
    return { realValue: round6(realValue), nominalValue: round6(nominalValue) };
  }

  // mirrors model/decline.py::discount_to_present_value
  function discountToPresentValue(cashFlow, discountRate, years) {
    return round2(cashFlow / Math.pow(1 + discountRate, years));
  }

  // ---------------------------------------------------------------------
  // model/solar.py
  // ---------------------------------------------------------------------

  // mirrors model/solar.py::_derate_factor + calculate_annual_monthly_production_kwh
  function calculateSolarProduction(inputs, regionalMonthlyYieldKwhPerKw, orientationFactors, shadingFactors, systemAgeYears) {
    if (!(inputs.orientation in orientationFactors)) {
      throw new Error("unknown orientation " + inputs.orientation);
    }
    if (!(inputs.shading in shadingFactors)) {
      throw new Error("unknown shading level " + inputs.shading);
    }
    var derate =
      orientationFactors[inputs.orientation] *
      shadingFactors[inputs.shading] *
      (inputs.pitchFactor || 1.0) *
      inputs.inverterEfficiency *
      (1.0 - inputs.otherSystemLosses);
    var degradationMultiplier = Math.pow(1.0 - inputs.degradationAnnual, systemAgeYears);

    var production = {};
    for (var month = 1; month <= 12; month++) {
      production[month] = inputs.capacityKwDc * regionalMonthlyYieldKwhPerKw[month] * derate * degradationMultiplier;
    }
    return production;
  }

  // ---------------------------------------------------------------------
  // model/net_metering.py
  // ---------------------------------------------------------------------

  function periodAddMonths(period, months) {
    var parts = period.split("-");
    var year = parseInt(parts[0], 10);
    var month = parseInt(parts[1], 10);
    var total = year * 12 + (month - 1) + months;
    var newYear = Math.floor(total / 12);
    var newMonth = total % 12;
    return String(newYear).padStart(4, "0") + "-" + String(newMonth + 1).padStart(2, "0");
  }

  var CREDIT_EXPIRY_MONTHS = 12;

  // mirrors model/net_metering.py::NetMeteringLedger
  function NetMeteringLedger(exportCreditRateCadPerKwh) {
    this._exportCreditRate = exportCreditRateCadPerKwh;
    this._tranches = []; // [{ createdPeriod, amountCad }]
    this.totalGenerationKwh = 0;
    this.totalDirectSelfConsumptionKwh = 0;
    this.totalExportedKwh = 0;
    this.totalGridImportKwh = 0;
    this.totalCreditCreatedCad = 0;
    this.totalCreditUsedCad = 0;
    this.totalCreditExpiredCad = 0;
  }

  NetMeteringLedger.prototype._expireTranches = function (currentPeriod) {
    var expired = 0;
    var remaining = [];
    for (var i = 0; i < this._tranches.length; i++) {
      var tranche = this._tranches[i];
      var expiryPeriod = periodAddMonths(tranche.createdPeriod, CREDIT_EXPIRY_MONTHS);
      if (expiryPeriod <= currentPeriod) {
        expired += tranche.amountCad;
      } else {
        remaining.push(tranche);
      }
    }
    this._tranches = remaining;
    return expired;
  };

  NetMeteringLedger.prototype._balance = function () {
    return this._tranches.reduce(function (sum, t) {
      return sum + t.amountCad;
    }, 0);
  };

  NetMeteringLedger.prototype._consume = function (amountNeeded) {
    var consumed = 0;
    var remaining = [];
    for (var i = 0; i < this._tranches.length; i++) {
      var tranche = this._tranches[i];
      if (consumed >= amountNeeded) {
        remaining.push(tranche);
        continue;
      }
      var take = Math.min(tranche.amountCad, amountNeeded - consumed);
      consumed += take;
      var leftover = tranche.amountCad - take;
      if (leftover > 1e-9) {
        remaining.push({ createdPeriod: tranche.createdPeriod, amountCad: leftover });
      }
    }
    this._tranches = remaining;
    return consumed;
  };

  NetMeteringLedger.prototype.processMonth = function (params) {
    var exportedKwh = Math.max(0, params.solarGenerationKwh - params.directSelfConsumptionKwh);
    var gridImportKwh = Math.max(0, params.householdDemandKwh - params.directSelfConsumptionKwh);

    var openingBalance = this._balance();
    var expiredThisMonth = this._expireTranches(params.period);

    var eligibleChargeBefore = gridImportKwh * params.eligibleEnergyRateCadPerKwh;

    var newCredit = exportedKwh * this._exportCreditRate;
    if (newCredit > 0) {
      this._tranches.push({ createdPeriod: params.period, amountCad: newCredit });
    }

    var used = this._consume(eligibleChargeBefore);
    var eligibleChargeAfter = eligibleChargeBefore - used;
    var closingBalance = this._balance();

    this.totalGenerationKwh += params.solarGenerationKwh;
    this.totalDirectSelfConsumptionKwh += params.directSelfConsumptionKwh;
    this.totalExportedKwh += exportedKwh;
    this.totalGridImportKwh += gridImportKwh;
    this.totalCreditCreatedCad += newCredit;
    this.totalCreditUsedCad += used;
    this.totalCreditExpiredCad += expiredThisMonth;

    return {
      period: params.period,
      solarGenerationKwh: round4(params.solarGenerationKwh),
      directSelfConsumptionKwh: round4(params.directSelfConsumptionKwh),
      exportedKwh: round4(exportedKwh),
      gridImportKwh: round4(gridImportKwh),
      eligibleChargeBeforeCreditsCad: round4(eligibleChargeBefore),
      creditOpeningBalanceCad: round4(openingBalance),
      creditCreatedCad: round4(newCredit),
      creditUsedCad: round4(used),
      creditExpiredCad: round4(expiredThisMonth),
      creditClosingBalanceCad: round4(closingBalance),
      eligibleChargeAfterCreditsCad: round4(eligibleChargeAfter),
      ineligibleChargesCad: round4(params.ineligibleChargesCad)
    };
  };

  NetMeteringLedger.prototype.effectiveValuePerGeneratedKwh = function () {
    if (this.totalGenerationKwh <= 0) {
      return 0;
    }
    return round6(this.totalCreditUsedCad / this.totalGenerationKwh);
  };

  // ---------------------------------------------------------------------
  // model/financing.py
  // ---------------------------------------------------------------------

  var ELIGIBLE_FIELDS = ["panels", "inverter", "racking", "electrical_equipment", "labour", "installer_overhead"];
  var INELIGIBLE_FIELDS = ["design_and_engineering", "permitting", "utility_connection", "battery", "other"];

  // mirrors model/financing.py::QuoteComponents.total/eligible_total/ineligible_total
  function quoteTotal(quote) {
    return sumFields(quote, ELIGIBLE_FIELDS.concat(INELIGIBLE_FIELDS));
  }
  function quoteEligibleTotal(quote) {
    return sumFields(quote, ELIGIBLE_FIELDS);
  }
  function quoteIneligibleTotal(quote) {
    return sumFields(quote, INELIGIBLE_FIELDS);
  }
  function sumFields(obj, fields) {
    return fields.reduce(function (sum, f) {
      return sum + (obj[f] || 0);
    }, 0);
  }

  // mirrors model/financing.py::quote_from_total
  function quoteFromTotal(totalBeforeTax, costComponentShares) {
    var quote = {};
    ELIGIBLE_FIELDS.concat(INELIGIBLE_FIELDS).forEach(function (field) {
      if (field in costComponentShares) {
        quote[field] = totalBeforeTax * costComponentShares[field];
      }
    });
    return quote;
  }

  // mirrors model/financing.py::apply_group_discount
  function applyGroupDiscount(quote, discountFraction) {
    if (!(discountFraction >= 0 && discountFraction < 1)) {
      throw new Error("discount_fraction must be in [0, 1), got " + discountFraction);
    }
    var eligibleBefore = quoteEligibleTotal(quote);
    var eligibleAfter = eligibleBefore * (1.0 - discountFraction);
    var discountAmount = eligibleBefore - eligibleAfter;
    var ineligible = quoteIneligibleTotal(quote);

    return {
      discountFraction: discountFraction,
      eligibleTotalBeforeDiscount: round2(eligibleBefore),
      eligibleTotalAfterDiscount: round2(eligibleAfter),
      discountAmount: round2(discountAmount),
      ineligibleTotal: round2(ineligible),
      totalAfterDiscount: round2(eligibleAfter + ineligible)
    };
  }

  // mirrors model/financing.py::amortize_loan
  function amortizeLoan(principal, annualRate, termYears) {
    if (principal < 0) {
      throw new Error("principal must be non-negative");
    }
    if (termYears <= 0) {
      throw new Error("term_years must be positive");
    }
    var nPayments = termYears * 12;
    var monthlyRate = annualRate / 12;

    if (principal === 0) {
      return { principal: 0, monthlyPayment: 0, totalInterest: 0, totalPaid: 0 };
    }

    var monthlyPayment;
    if (monthlyRate === 0) {
      monthlyPayment = principal / nPayments;
    } else {
      monthlyPayment =
        (principal * monthlyRate * Math.pow(1 + monthlyRate, nPayments)) /
        (Math.pow(1 + monthlyRate, nPayments) - 1);
    }
    var balance = principal;
    var totalInterest = 0;
    for (var m = 1; m <= nPayments; m++) {
      var interestPayment = balance * monthlyRate;
      var principalPayment = monthlyPayment - interestPayment;
      balance = Math.max(0, balance - principalPayment);
      totalInterest += interestPayment;
    }
    return {
      principal: round2(principal),
      monthlyPayment: round2(monthlyPayment),
      totalInterest: round2(totalInterest),
      totalPaid: round2(principal + totalInterest)
    };
  }

  // ---------------------------------------------------------------------
  // model/scenario.py
  // ---------------------------------------------------------------------

  // mirrors model/scenario.py::project_annual_grid_bill
  function projectAnnualGridBill(baseAnnualBillCad, priceScenario, year, fixedShare, variableShare, energyShare) {
    var energy = billComponentAfterYears(
      baseAnnualBillCad * energyShare, priceScenario.electricityEnergyReal, year, priceScenario.generalInflation
    );
    var fixed = billComponentAfterYears(
      baseAnnualBillCad * fixedShare, priceScenario.fixedDeliveryReal, year, priceScenario.generalInflation
    );
    var variable = billComponentAfterYears(
      baseAnnualBillCad * variableShare, priceScenario.variableDeliveryReal, year, priceScenario.generalInflation
    );
    var nominalTotal = energy.nominalValue + fixed.nominalValue + variable.nominalValue;
    var realTotal = energy.realValue + fixed.realValue + variable.realValue;
    return { nominal: round2(nominalTotal), real: round2(realTotal) };
  }

  // mirrors model/scenario.py::evaluate_grid_only
  function evaluateGridOnly(params) {
    var flows = [];
    var totalNominal = 0;
    var totalPv = 0;

    for (var year = 0; year < params.horizonYears; year++) {
      var bill = projectAnnualGridBill(
        params.baseAnnualBillCad, params.priceScenario, year, params.fixedShare, params.variableShare, params.energyShare
      );
      var pv = discountToPresentValue(bill.nominal, params.discountRate, year);
      flows.push({
        year: year,
        gridBillNominalCad: bill.nominal,
        solarMaintenanceNominalCad: 0,
        financingPaymentNominalCad: 0,
        creditsUsedNominalCad: 0,
        totalNominalCad: bill.nominal,
        totalPresentValueCad: pv
      });
      totalNominal += bill.nominal;
      totalPv += pv;
    }

    return {
      label: "Grid only",
      purchaseYearOffset: -1,
      initialCostCad: 0,
      financingInterestCad: 0,
      groupDiscountCad: 0,
      annualCashFlows: flows,
      totalNominalCad: round2(totalNominal),
      totalPresentValueCad: round2(totalPv),
      simplePaybackYears: null,
      totalGridImportsKwh: 0,
      totalSolarGenerationKwh: 0,
      creditsExpiredCad: 0
    };
  }

  // mirrors model/scenario.py::evaluate_solar_purchase
  function evaluateSolarPurchase(params) {
    var baseTotal = quoteTotal(params.baseQuote);
    var costResult = installedCostAfterYears(
      baseTotal, params.declineScenario.realAnnualInstalledCostChange, params.purchaseYearOffset, params.priceScenario.generalInflation
    );
    var scale = baseTotal ? costResult.realCost / baseTotal : 1.0;
    var scaledQuote = {};
    ELIGIBLE_FIELDS.concat(INELIGIBLE_FIELDS).forEach(function (field) {
      scaledQuote[field] = (params.baseQuote[field] || 0) * scale;
    });

    var discount = applyGroupDiscount(scaledQuote, params.groupDiscountFraction);
    var totalBeforeTax = discount.totalAfterDiscount;
    var totalWithTax = totalBeforeTax * (1 + params.taxRate);

    var downPayment = totalWithTax * params.downPaymentFraction;
    var principal = totalWithTax - downPayment;

    var loan, initialCost;
    if (params.isCash) {
      loan = amortizeLoan(0, params.annualInterestRate, params.loanTermYears);
      initialCost = totalWithTax;
    } else {
      loan = amortizeLoan(principal, params.annualInterestRate, params.loanTermYears);
      initialCost = downPayment;
    }

    var flows = [];
    var totalNominal = 0;
    var totalPv = 0;
    var cumulativeNominal = 0;
    var simplePaybackYears = null;
    var gridOnlyCumulative = 0;

    for (var year = 0; year < params.horizonYears; year++) {
      var billNominal, maintenance, financingPayment, creditsUsed;

      if (year < params.purchaseYearOffset) {
        var bill = projectAnnualGridBill(
          params.baseAnnualBillCad, params.priceScenario, year, params.fixedShare, params.variableShare, params.energyShare
        );
        billNominal = bill.nominal;
        maintenance = 0;
        financingPayment = 0;
        creditsUsed = 0;
      } else {
        var yearsSincePurchase = year - params.purchaseYearOffset;
        var bill2 = projectAnnualGridBill(
          params.annualGridBillAfterSolarCad, params.priceScenario, yearsSincePurchase,
          params.fixedShare, params.variableShare, params.energyShare
        );
        billNominal = bill2.nominal;
        maintenance = params.annualMaintenanceCad;
        if (params.inverterReplacementYear !== null && yearsSincePurchase === params.inverterReplacementYear) {
          maintenance += params.inverterReplacementCostCad;
        }
        financingPayment = params.isCash ? 0 : loan.monthlyPayment * 12;
        creditsUsed = params.annualCreditsUsedCad;
      }

      var billAfterCredits = Math.max(0, billNominal - creditsUsed);
      var yearTotalNominal = billAfterCredits + maintenance + financingPayment;
      if (year === params.purchaseYearOffset) {
        yearTotalNominal += initialCost;
      }

      var pv = discountToPresentValue(yearTotalNominal, params.discountRate, year);

      flows.push({
        year: year,
        gridBillNominalCad: round2(billAfterCredits),
        solarMaintenanceNominalCad: round2(maintenance),
        financingPaymentNominalCad: round2(financingPayment),
        creditsUsedNominalCad: round2(creditsUsed),
        totalNominalCad: round2(yearTotalNominal),
        totalPresentValueCad: pv
      });
      totalNominal += yearTotalNominal;
      totalPv += pv;
      cumulativeNominal += yearTotalNominal;

      var gridOnlyBill = projectAnnualGridBill(
        params.baseAnnualBillCad, params.priceScenario, year, params.fixedShare, params.variableShare, params.energyShare
      );
      gridOnlyCumulative += gridOnlyBill.nominal;

      if (simplePaybackYears === null && year >= params.purchaseYearOffset) {
        if (cumulativeNominal <= gridOnlyCumulative) {
          simplePaybackYears = year - params.purchaseYearOffset + 1;
        }
      }
    }

    return {
      label: params.label,
      purchaseYearOffset: params.purchaseYearOffset,
      initialCostCad: round2(initialCost),
      financingInterestCad: loan.totalInterest,
      groupDiscountCad: discount.discountAmount,
      annualCashFlows: flows,
      totalNominalCad: round2(totalNominal),
      totalPresentValueCad: round2(totalPv),
      simplePaybackYears: simplePaybackYears,
      totalGridImportsKwh: params.totalGridImportsKwh,
      totalSolarGenerationKwh: params.totalSolarGenerationKwh,
      creditsExpiredCad: params.totalCreditsExpiredCad
    };
  }

  // ---------------------------------------------------------------------
  // model/collective_purchasing.py
  // ---------------------------------------------------------------------

  var NEVER_DISCOUNTABLE = { taxes: true, government_fees: true, utility_charges: true, interest_rate: true };

  // mirrors model/collective_purchasing.py::apply_collective_purchase
  function applyCollectivePurchase(tier, baseCostsByComponent) {
    var componentIds = Object.keys(baseCostsByComponent);
    var totalBase = componentIds.reduce(function (sum, id) { return sum + baseCostsByComponent[id]; }, 0);

    if (totalBase <= 0) {
      return { totalBaseCost: 0, totalReducedCost: 0, totalReductionCad: 0, effectiveDiscountPercent: 0, capped: false };
    }

    var uncappedReductions = {};
    componentIds.forEach(function (id) {
      if (NEVER_DISCOUNTABLE[id]) {
        uncappedReductions[id] = 0;
        return;
      }
      var pct = tier.reductions[id] || 0;
      uncappedReductions[id] = baseCostsByComponent[id] * (pct / 100);
    });

    var uncappedTotalReduction = componentIds.reduce(function (sum, id) { return sum + uncappedReductions[id]; }, 0);
    var uncappedDiscountPercent = (uncappedTotalReduction / totalBase) * 100;

    var capped = uncappedDiscountPercent > tier.overallDiscountCapPercent;
    var scale = 1.0;
    if (capped && uncappedTotalReduction > 0) {
      scale = ((tier.overallDiscountCapPercent / 100) * totalBase) / uncappedTotalReduction;
    }

    var totalReduction = 0;
    componentIds.forEach(function (id) {
      totalReduction += uncappedReductions[id] * scale;
    });

    var totalReduced = totalBase - totalReduction;
    var effectiveDiscountPercent = totalBase ? (totalReduction / totalBase) * 100 : 0;

    return {
      totalBaseCost: round2(totalBase),
      totalReducedCost: round2(totalReduced),
      totalReductionCad: round2(totalReduction),
      effectiveDiscountPercent: round4(effectiveDiscountPercent),
      capped: capped
    };
  }

  // ---------------------------------------------------------------------
  // model/cost_of_inaction.py
  // ---------------------------------------------------------------------

  var EMISSIONS_CONSEQUENCE_NOTE =
    "Delayed or foregone solar generation has an emissions consequence; " +
    "this tool reports the forgone generation in kWh above but does not " +
    "assign it a default dollar value.";

  // mirrors model/cost_of_inaction.py::calculate_cost_of_inaction - never
  // assumes "buy now" (or decisions[0]) is cheapest; finds the minimum
  // present-value decision empirically, same as the Python model.
  function calculateCostOfInaction(decisions) {
    if (!decisions.length) {
      return {};
    }

    var best = decisions[0];
    decisions.forEach(function (d) {
      if (d.totalPresentValueCad < best.totalPresentValueCad) {
        best = d;
      }
    });

    var results = {};
    decisions.forEach(function (decision) {
      var additionalNominal = decision.totalNominalCad - best.totalNominalCad;
      var additionalPv = decision.totalPresentValueCad - best.totalPresentValueCad;
      var gridPurchasedExtra = Math.max(0, decision.gridImportsKwh - best.gridImportsKwh);
      var solarForgone = Math.max(0, best.solarGenerationKwh - decision.solarGenerationKwh);
      var incentivesForgone = Math.max(0, (best.incentivesReceivedCad || 0) - (decision.incentivesReceivedCad || 0));
      var revenueForgone = Math.max(0, (best.gridServiceRevenueCad || 0) - (decision.gridServiceRevenueCad || 0));
      var residualDiff = (decision.residualValueCad || 0) - (best.residualValueCad || 0);

      results[decision.label] = {
        decisionLabel: decision.label,
        additionalNominalCostCad: round2(additionalNominal),
        additionalPresentValueCad: round2(additionalPv),
        gridElectricityPurchasedWhileWaitingKwh: round2(gridPurchasedExtra),
        solarGenerationForgoneKwh: round2(solarForgone),
        currentIncentivesForgoneCad: round2(incentivesForgone),
        currentlyAvailableRevenueForgoneCad: round2(revenueForgone),
        residualValueDifferenceCad: round2(residualDiff),
        emissionsConsequenceNote: EMISSIONS_CONSEQUENCE_NOTE
      };
    });
    return results;
  }

  // ---------------------------------------------------------------------
  // model/waiting.py
  // ---------------------------------------------------------------------

  // mirrors model/waiting.py::find_breakeven_decline_rate
  function findBreakevenDeclineRate(npvCostForDeclineRate, npvCostBuyNow, low, high, tolerance, maxIterations) {
    low = low === undefined ? 0.0 : low;
    high = high === undefined ? 0.30 : high;
    tolerance = tolerance === undefined ? 1e-5 : tolerance;
    maxIterations = maxIterations === undefined ? 100 : maxIterations;

    var costAtLow = npvCostForDeclineRate(low);
    var costAtHigh = npvCostForDeclineRate(high);

    if (costAtLow <= npvCostBuyNow) {
      return low;
    }
    if (costAtHigh > npvCostBuyNow) {
      return null;
    }

    var lo = low, hi = high, mid;
    for (var i = 0; i < maxIterations; i++) {
      mid = (lo + hi) / 2;
      var costAtMid = npvCostForDeclineRate(mid);
      if (Math.abs(costAtMid - npvCostBuyNow) < tolerance * Math.max(1.0, npvCostBuyNow)) {
        return round5(mid);
      }
      if (costAtMid > npvCostBuyNow) {
        lo = mid;
      } else {
        hi = mid;
      }
    }
    return round5((lo + hi) / 2);
  }

  // mirrors model/waiting.py::format_breakeven_statement
  function formatBreakevenStatement(breakevenRate, waitYears, waitUntilYear, buyNowYear) {
    if (breakevenRate === null) {
      return (
        "Under the selected assumptions, no plausible solar-cost decline " +
        "rate makes waiting until " + waitUntilYear + " cost less than buying " +
        "in " + buyNowYear + "."
      );
    }
    return (
      "Under the selected assumptions, installed solar prices would need " +
      "to fall by at least " + (breakevenRate * 100).toFixed(1) + "% per year for " +
      waitYears + (waitYears !== 1 ? " years" : " year") + " for waiting until " +
      waitUntilYear + " to cost less than buying in " + buyNowYear + "."
    );
  }

  // ---------------------------------------------------------------------
  // Rounding helpers (match Python's round() banker's-rounding-adjacent
  // behaviour closely enough for currency display; both sides are also
  // cross-checked against real Python output by the golden-file test, so
  // any meaningful divergence is caught there rather than relied on to be
  // theoretically perfect here).
  // ---------------------------------------------------------------------

  function round2(x) { return Math.round((x + Number.EPSILON) * 100) / 100; }
  function round4(x) { return Math.round((x + Number.EPSILON) * 10000) / 10000; }
  function round5(x) { return Math.round((x + Number.EPSILON) * 100000) / 100000; }
  function round6(x) { return Math.round((x + Number.EPSILON) * 1000000) / 1000000; }

  function formatCad(value) {
    var sign = value < 0 ? "-" : "";
    return sign + "$" + Math.abs(value).toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  var api = {
    calculateTouBill: calculateTouBill,
    DEFAULT_TOU_HOURLY_SHARES: DEFAULT_TOU_HOURLY_SHARES,
    installedCostAfterYears: installedCostAfterYears,
    billComponentAfterYears: billComponentAfterYears,
    discountToPresentValue: discountToPresentValue,
    calculateSolarProduction: calculateSolarProduction,
    NetMeteringLedger: NetMeteringLedger,
    quoteTotal: quoteTotal,
    quoteEligibleTotal: quoteEligibleTotal,
    quoteIneligibleTotal: quoteIneligibleTotal,
    quoteFromTotal: quoteFromTotal,
    applyGroupDiscount: applyGroupDiscount,
    amortizeLoan: amortizeLoan,
    projectAnnualGridBill: projectAnnualGridBill,
    evaluateGridOnly: evaluateGridOnly,
    evaluateSolarPurchase: evaluateSolarPurchase,
    applyCollectivePurchase: applyCollectivePurchase,
    calculateCostOfInaction: calculateCostOfInaction,
    findBreakevenDeclineRate: findBreakevenDeclineRate,
    formatBreakevenStatement: formatBreakevenStatement,
    formatCad: formatCad
  };

  // ---------------------------------------------------------------------
  // Browser wiring (skipped entirely under Node/tests).
  // ---------------------------------------------------------------------

  if (browserGlobal && typeof browserGlobal.document !== "undefined") {
    wireUpBrowser(browserGlobal, api);
  }

  return api;

  function wireUpBrowser(win, api) {
    var document = win.document;
    document.documentElement.classList.add("js-enabled");

    // Default Hydro Ottawa rates/assumptions, used only as a fallback if
    // dist/data/*.json cannot be fetched (e.g. opened via file://).
    // Mirrors assumptions/utilities/hydro-ottawa.yaml; kept in sync via
    // the golden-file test's rate values.
    var FALLBACK_RATES = {
      fixedDeliveryPerDay: 0.4795, variableDeliveryPerKwh: 0.0223, regulatoryPerKwh: 0.0059,
      rebatePerKwh: -0.0227, hstRate: 0.13,
      tou: { off_peak: 0.076, mid_peak: 0.122, on_peak: 0.158 }
    };
    var FALLBACK_SCENARIOS = {
      price: {
        low: { electricityEnergyReal: 0.0, fixedDeliveryReal: 0.005, variableDeliveryReal: 0.0, generalInflation: 0.02 },
        reference: { electricityEnergyReal: 0.015, fixedDeliveryReal: 0.02, variableDeliveryReal: 0.01, generalInflation: 0.02 },
        high: { electricityEnergyReal: 0.03, fixedDeliveryReal: 0.035, variableDeliveryReal: 0.025, generalInflation: 0.02 },
        stress: { electricityEnergyReal: 0.05, fixedDeliveryReal: 0.05, variableDeliveryReal: 0.045, generalInflation: 0.02 }
      },
      decline: {
        flat: { realAnnualInstalledCostChange: 0.0 },
        "moderate-decline": { realAnnualInstalledCostChange: -0.02 },
        "faster-decline": { realAnnualInstalledCostChange: -0.04 }
      }
    };
    var FALLBACK_DEFAULTS = {
      solar: {
        referenceQuoteCad: 21000, referenceSystemKwDc: 7.2,
        costComponentShares: {
          panels: 0.32, inverter: 0.10, racking: 0.08, electrical_equipment: 0.06, labour: 0.20,
          design_and_engineering: 0.03, permitting: 0.02, utility_connection: 0.04, installer_overhead: 0.15
        },
        degradationAnnual: 0.005, annualMaintenanceCad: 150,
        inverterReplacementYear: 12, inverterReplacementCostCad: 1800
      },
      financing: { defaultDownPaymentFraction: 0.10, defaultAnnualInterestRate: 0.079, defaultTermYears: 10 },
      ontario: { hstRate: 0.13, discountRateDefault: 0.04, planningHorizonsYears: [10, 20, 25, 30], defaultPlanningHorizonYears: 20 },
      billShares: { fixedShare: 0.30, variableShare: 0.15, energyShare: 0.55 }
    };

    var assumptionData = { rates: FALLBACK_RATES, scenarios: FALLBACK_SCENARIOS, defaults: FALLBACK_DEFAULTS };

    function loadAssumptionData() {
      var base = document.querySelector('link[rel="calculator-data-base"]');
      var prefix = base ? base.getAttribute("href") : "data/";
      return Promise.all([
        fetchJsonOrNull(prefix + "rates.json"),
        fetchJsonOrNull(prefix + "scenarios-full.json"),
        fetchJsonOrNull(prefix + "assumption-defaults.json")
      ]).then(function (results) {
        if (results[0]) assumptionData.rates = results[0];
        if (results[1]) assumptionData.scenarios = results[1];
        if (results[2]) assumptionData.defaults = results[2];
      });
    }

    function fetchJsonOrNull(url) {
      if (typeof win.fetch !== "function") {
        return Promise.resolve(null);
      }
      return win.fetch(url).then(
        function (response) { return response.ok ? response.json() : null; },
        function () { return null; }
      );
    }

    function announce(message) {
      var region = document.getElementById("results-status");
      if (region) {
        region.textContent = message;
      }
    }

    // Keep any range input synchronized with its paired numeric input, in
    // both directions, so neither control is the only way to set a value
    // (ACCESSIBILITY.md: "No slider-only inputs").
    function setupRangeNumberPairs() {
      var ranges = document.querySelectorAll('input[type="range"]');
      ranges.forEach(function (range) {
        var numberId = range.id.replace("-range", "-number");
        var number = document.getElementById(numberId);
        if (!number) return;
        range.addEventListener("input", function () { number.value = range.value; });
        number.addEventListener("input", function () {
          if (number.value === "") return;
          var clamped = Math.min(Number(range.max), Math.max(Number(range.min), Number(number.value)));
          range.value = String(clamped);
        });
      });
    }

    function buildDecisionRows(form) {
      var monthlyKwh = Number(form.querySelector("#calc-monthly-kwh").value) || 700;
      var annualBillCad = calculateTouBill(monthlyKwh, DEFAULT_TOU_HOURLY_SHARES, assumptionData.rates, 6).total * 12;

      var priceScenarioId = form.querySelector('input[name="price-scenario"]:checked').value;
      var declineScenarioId = form.querySelector('input[name="decline-scenario"]:checked').value;
      var priceScenario = assumptionData.scenarios.price[priceScenarioId];
      var declineScenario = assumptionData.scenarios.decline[declineScenarioId];

      var quoteTotalCad = Number(form.querySelector("#calc-quote-total").value) || assumptionData.defaults.solar.referenceQuoteCad;
      var baseQuote = quoteFromTotal(quoteTotalCad, assumptionData.defaults.solar.costComponentShares);

      var discountPct = Number(form.querySelector("#discount-number").value) || 0;
      var financeType = form.querySelector('input[name="finance-type"]:checked').value;
      var horizonYears = Number(form.querySelector("#horizon-select").value) || assumptionData.defaults.ontario.defaultPlanningHorizonYears;
      var waitYears = Number(form.querySelector("#calc-wait-years") ? form.querySelector("#calc-wait-years").value : 3) || 3;

      var d = assumptionData.defaults;
      var commonParams = {
        baseAnnualBillCad: annualBillCad,
        priceScenario: priceScenario,
        declineScenario: declineScenario,
        baseQuote: baseQuote,
        taxRate: d.ontario.hstRate,
        downPaymentFraction: financeType === "cash" ? 1.0 : d.financing.defaultDownPaymentFraction,
        annualInterestRate: d.financing.defaultAnnualInterestRate,
        loanTermYears: d.financing.defaultTermYears,
        horizonYears: horizonYears,
        discountRate: d.ontario.discountRateDefault,
        fixedShare: d.billShares.fixedShare,
        variableShare: d.billShares.variableShare,
        energyShare: d.billShares.energyShare,
        annualGridBillAfterSolarCad: annualBillCad * 0.35,
        annualMaintenanceCad: d.solar.annualMaintenanceCad,
        inverterReplacementYear: d.solar.inverterReplacementYear,
        inverterReplacementCostCad: d.solar.inverterReplacementCostCad,
        annualCreditsUsedCad: annualBillCad * 0.30,
        totalCreditsExpiredCad: 0,
        totalSolarGenerationKwh: 9000,
        totalGridImportsKwh: monthlyKwh * 12 * 0.4
      };

      var gridOnly = evaluateGridOnly({
        baseAnnualBillCad: annualBillCad, priceScenario: priceScenario, horizonYears: horizonYears,
        discountRate: d.ontario.discountRateDefault, fixedShare: d.billShares.fixedShare,
        variableShare: d.billShares.variableShare, energyShare: d.billShares.energyShare
      });
      var buyNow = evaluateSolarPurchase(mergeParams(commonParams, {
        label: "Buy solar now", purchaseYearOffset: 0, groupDiscountFraction: 0, isCash: financeType === "cash"
      }));
      var buyNowDiscount = evaluateSolarPurchase(mergeParams(commonParams, {
        label: "Buy now, " + discountPct + "% group discount", purchaseYearOffset: 0,
        groupDiscountFraction: discountPct / 100, isCash: financeType === "cash"
      }));
      var waitN = evaluateSolarPurchase(mergeParams(commonParams, {
        label: "Wait " + waitYears + " year" + (waitYears !== 1 ? "s" : ""), purchaseYearOffset: waitYears,
        groupDiscountFraction: 0, isCash: financeType === "cash"
      }));

      return { gridOnly: gridOnly, buyNow: buyNow, buyNowDiscount: buyNowDiscount, waitN: waitN, waitYears: waitYears, horizonYears: horizonYears };
    }

    function mergeParams(base, overrides) {
      var out = {};
      Object.keys(base).forEach(function (k) { out[k] = base[k]; });
      Object.keys(overrides).forEach(function (k) { out[k] = overrides[k]; });
      return out;
    }

    function renderDecisionRow(tbody, decision, cost10yrCad) {
      var row = document.createElement("tr");
      function cell(text, isHeader) {
        var el = document.createElement(isHeader ? "th" : "td");
        if (isHeader) el.setAttribute("scope", "row");
        el.textContent = text;
        return el;
      }
      row.appendChild(cell(decision.label, true));
      row.appendChild(cell(formatCad(decision.initialCostCad)));
      row.appendChild(cell(formatCad(decision.financingInterestCad)));
      row.appendChild(cell(formatCad(cost10yrCad)));
      row.appendChild(cell(formatCad(decision.totalNominalCad)));
      row.appendChild(cell((decision.totalGridImportsKwh || 0).toLocaleString("en-CA", { maximumFractionDigits: 0 })));
      row.appendChild(cell("See sensitivity table below"));
      tbody.appendChild(row);
    }

    function sumFirstNYears(decision, n) {
      var sum = 0;
      for (var i = 0; i < Math.min(n, decision.annualCashFlows.length); i++) {
        sum += decision.annualCashFlows[i].totalNominalCad;
      }
      return sum;
    }

    // Maps a QuoteComponents-shaped quote to the six collective-purchasing
    // cost categories (hardware/labour/design/permitting/customer
    // acquisition/financing fees), mirroring
    // build_site.py::_build_collective_purchasing_rows's server-side
    // mapping exactly so client and server agree on what "hardware" etc.
    // means for a given quote.
    function collectivePurchasingBaseCosts(quote) {
      return {
        hardware: (quote.panels || 0) + (quote.inverter || 0) + (quote.racking || 0) + (quote.electrical_equipment || 0),
        labour: quote.labour || 0,
        design: quote.design_and_engineering || 0,
        permitting: quote.permitting || 0,
        customer_acquisition: quote.installer_overhead || 0,
        financing_fees: 0
      };
    }

    function renderCollectivePurchasingRows(baseQuote, taxRate) {
      var tbody = document.getElementById("collective-purchasing-tbody");
      if (!tbody) return;
      var baseCosts = collectivePurchasingBaseCosts(baseQuote);
      tbody.innerHTML = "";
      assumptionData.defaults.collectiveTiers.forEach(function (tier) {
        var result = applyCollectivePurchase(tier, baseCosts);
        var totalWithTax = result.totalReducedCost * (1 + taxRate);
        var row = document.createElement("tr");
        function cell(text, isHeader) {
          var el = document.createElement(isHeader ? "th" : "td");
          if (isHeader) el.setAttribute("scope", "row");
          el.textContent = text;
          return el;
        }
        row.appendChild(cell(tier.label, true));
        row.appendChild(cell(String(tier.households)));
        row.appendChild(cell(formatCad(totalWithTax)));
        row.appendChild(cell(formatCad(result.totalReductionCad)));
        row.appendChild(cell(result.effectiveDiscountPercent.toFixed(1) + "%" + (result.capped ? " (capped)" : "")));
        tbody.appendChild(row);
      });
    }

    function renderCostOfInactionRows(gridOnly, buyNow, waitN) {
      var tbody = document.getElementById("cost-of-inaction-tbody");
      var noteEl = document.getElementById("cost-of-inaction-emissions-note");
      if (!tbody) return;

      var decisions = [
        { label: "Grid only", totalNominalCad: gridOnly.totalNominalCad, totalPresentValueCad: gridOnly.totalPresentValueCad, gridImportsKwh: gridOnly.totalGridImportsKwh || 0, solarGenerationKwh: gridOnly.totalSolarGenerationKwh || 0 },
        { label: "Buy solar now", totalNominalCad: buyNow.totalNominalCad, totalPresentValueCad: buyNow.totalPresentValueCad, gridImportsKwh: buyNow.totalGridImportsKwh || 0, solarGenerationKwh: buyNow.totalSolarGenerationKwh || 0 },
        { label: waitN.label, totalNominalCad: waitN.totalNominalCad, totalPresentValueCad: waitN.totalPresentValueCad, gridImportsKwh: waitN.totalGridImportsKwh || 0, solarGenerationKwh: waitN.totalSolarGenerationKwh || 0 }
      ];
      var breakdowns = calculateCostOfInaction(decisions);

      tbody.innerHTML = "";
      decisions.forEach(function (decision) {
        var b = breakdowns[decision.label];
        var row = document.createElement("tr");
        function cell(text, isHeader) {
          var el = document.createElement(isHeader ? "th" : "td");
          if (isHeader) el.setAttribute("scope", "row");
          el.textContent = text;
          return el;
        }
        row.appendChild(cell(b.decisionLabel, true));
        row.appendChild(cell(formatCad(b.additionalNominalCostCad)));
        row.appendChild(cell(formatCad(b.additionalPresentValueCad)));
        row.appendChild(cell(b.gridElectricityPurchasedWhileWaitingKwh.toLocaleString("en-CA", { maximumFractionDigits: 0 }) + " kWh"));
        row.appendChild(cell(b.solarGenerationForgoneKwh.toLocaleString("en-CA", { maximumFractionDigits: 0 }) + " kWh"));
        row.appendChild(cell(formatCad(b.currentIncentivesForgoneCad)));
        tbody.appendChild(row);
        if (noteEl) noteEl.textContent = b.emissionsConsequenceNote;
      });
    }

    function recalculate(form) {
      var result = buildDecisionRows(form);
      var tbody = document.querySelector("#compare-timing-tbody");
      if (tbody) {
        tbody.innerHTML = "";
        renderDecisionRow(tbody, result.gridOnly, sumFirstNYears(result.gridOnly, 10));
        renderDecisionRow(tbody, result.buyNow, sumFirstNYears(result.buyNow, 10));
        renderDecisionRow(tbody, result.buyNowDiscount, sumFirstNYears(result.buyNowDiscount, 10));
        renderDecisionRow(tbody, result.waitN, sumFirstNYears(result.waitN, 10));
      }

      renderCostOfInactionRows(result.gridOnly, result.buyNow, result.waitN);
      {
        var quoteTotalForTiers = Number(form.querySelector("#calc-quote-total").value) || assumptionData.defaults.solar.referenceQuoteCad;
        var baseQuoteForTiers = quoteFromTotal(quoteTotalForTiers, assumptionData.defaults.solar.costComponentShares);
        renderCollectivePurchasingRows(baseQuoteForTiers, assumptionData.defaults.ontario.hstRate);
      }

      var totals = [result.buyNow.totalNominalCad, result.buyNowDiscount.totalNominalCad, result.waitN.totalNominalCad];
      var rangeLow = Math.min.apply(null, totals);
      var rangeHigh = Math.max.apply(null, totals);
      var rangeEl = document.getElementById("compare-timing-range");
      if (rangeEl) {
        rangeEl.textContent =
          "Across the selected scenarios, estimated " + result.horizonYears + "-year totals range from " +
          formatCad(rangeLow) + " to " + formatCad(rangeHigh) + ". Electricity-price growth, installation cost, " +
          "and financing explain most of the difference. This is a modelled range under stated assumptions, " +
          "not a prediction and not a guarantee.";
      }

      var waitingEl = document.getElementById("compare-timing-waiting-statement");
      if (waitingEl) {
        var baseYear = new Date().getFullYear();
        var declineScenarioId = form.querySelector('input[name="decline-scenario"]:checked').value;
        var priceScenarioId = form.querySelector('input[name="price-scenario"]:checked').value;
        var priceScenario = assumptionData.scenarios.price[priceScenarioId];
        var quoteTotalCad = Number(form.querySelector("#calc-quote-total").value) || assumptionData.defaults.solar.referenceQuoteCad;
        var baseQuote = quoteFromTotal(quoteTotalCad, assumptionData.defaults.solar.costComponentShares);
        var monthlyKwh = Number(form.querySelector("#calc-monthly-kwh").value) || 700;
        var annualBillCad = calculateTouBill(monthlyKwh, DEFAULT_TOU_HOURLY_SHARES, assumptionData.rates, 6).total * 12;
        var d = assumptionData.defaults;
        var financeType = form.querySelector('input[name="finance-type"]:checked').value;
        var horizonYears = Number(form.querySelector("#horizon-select").value) || d.ontario.defaultPlanningHorizonYears;

        var sweepBase = {
          baseAnnualBillCad: annualBillCad, priceScenario: priceScenario, baseQuote: baseQuote,
          taxRate: d.ontario.hstRate, downPaymentFraction: financeType === "cash" ? 1.0 : d.financing.defaultDownPaymentFraction,
          annualInterestRate: d.financing.defaultAnnualInterestRate, loanTermYears: d.financing.defaultTermYears,
          horizonYears: horizonYears, discountRate: d.ontario.discountRateDefault, fixedShare: d.billShares.fixedShare,
          variableShare: d.billShares.variableShare, energyShare: d.billShares.energyShare,
          annualGridBillAfterSolarCad: annualBillCad * 0.35, annualMaintenanceCad: d.solar.annualMaintenanceCad,
          inverterReplacementYear: d.solar.inverterReplacementYear, inverterReplacementCostCad: d.solar.inverterReplacementCostCad,
          annualCreditsUsedCad: annualBillCad * 0.30, totalCreditsExpiredCad: 0, totalSolarGenerationKwh: 9000,
          totalGridImportsKwh: monthlyKwh * 12 * 0.4, label: "sweep", purchaseYearOffset: result.waitYears,
          groupDiscountFraction: 0, isCash: financeType === "cash"
        };
        var breakeven = findBreakevenDeclineRate(
          function (rate) {
            return evaluateSolarPurchase(mergeParams(sweepBase, { declineScenario: { realAnnualInstalledCostChange: rate } })).totalPresentValueCad;
          },
          result.buyNow.totalPresentValueCad
        );
        waitingEl.textContent = formatBreakevenStatement(breakeven, result.waitYears, baseYear + result.waitYears, baseYear);
      }

      announce("Recalculated. Estimated " + result.horizonYears + "-year cost for buying solar now: " +
        formatCad(result.buyNow.totalNominalCad) + ". This is a modelled estimate, not a guaranteed price.");
    }

    var debounceTimer = null;
    function debouncedRecalculate(form) {
      if (debounceTimer) win.clearTimeout(debounceTimer);
      debounceTimer = win.setTimeout(function () { recalculate(form); }, 150);
    }

    // ---------------------------------------------------------------------
    // Local-storage persistence for compare-timing.html's form inputs.
    //
    // Nothing here is sent anywhere - localStorage is entirely on-device,
    // consistent with this project's no-server-storage privacy commitment
    // (see README.md, MODEL_CARD.md "Privacy"). Only the form field values
    // themselves are stored (consumption, quote, scenario choices,
    // discount, financing, wait years, horizon) - no address, no account
    // number, no bill data. A visible "Reset to defaults" control (added
    // to the form by build_site.py/compare_timing.html) clears it, and
    // saved values are only ever restored into the SAME named fields they
    // came from, never rendered as raw HTML.
    // ---------------------------------------------------------------------

    var STORAGE_KEY = "ontario-home-energy-futures:compare-timing-inputs:v1";

    function getStoredFormValues() {
      try {
        var raw = win.localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        // Private browsing / storage disabled / quota exceeded / corrupt
        // JSON - fail silently back to defaults rather than breaking the
        // page.
        return null;
      }
    }

    function saveFormValues(form) {
      try {
        var values = {};
        Array.prototype.forEach.call(form.elements, function (el) {
          if (!el.name) return;
          if (el.type === "radio" || el.type === "checkbox") {
            if (el.checked) values[el.name] = el.value;
          } else {
            values[el.name] = el.value;
          }
        });
        win.localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
      } catch (e) {
        // Storage unavailable or full - the form still works for this
        // session, it just won't persist. Not fatal.
      }
    }

    function restoreFormValues(form, values) {
      if (!values) return;
      Object.keys(values).forEach(function (name) {
        var stored = values[name];
        var elements = form.querySelectorAll('[name="' + cssEscape(name) + '"]');
        elements.forEach(function (el) {
          if (el.type === "radio" || el.type === "checkbox") {
            el.checked = el.value === stored;
          } else {
            el.value = stored;
          }
        });
      });
      // Keep the group-discount range/number pair in sync after a
      // restored value, same as a live user edit would.
      var discountRange = form.querySelector("#discount-range");
      var discountNumber = form.querySelector("#discount-number");
      if (discountRange && discountNumber) {
        discountRange.value = discountNumber.value;
      }
    }

    function cssEscape(value) {
      if (win.CSS && win.CSS.escape) return win.CSS.escape(value);
      return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
    }

    function clearStoredFormValues() {
      try {
        win.localStorage.removeItem(STORAGE_KEY);
      } catch (e) {
        // ignore
      }
    }

    function setupCompareTimingForm() {
      var form = document.querySelector("#compare-timing-form");
      if (!form) return;
      loadAssumptionData().then(function () {
        var stored = getStoredFormValues();
        if (stored) {
          restoreFormValues(form, stored);
          announce("Your previously entered values were restored from this browser. Use “Reset to defaults” to clear them.");
        }

        form.addEventListener("input", function () {
          saveFormValues(form);
          debouncedRecalculate(form);
        });
        form.addEventListener("change", function () {
          saveFormValues(form);
          debouncedRecalculate(form);
        });
        form.addEventListener("submit", function (event) {
          event.preventDefault();
          saveFormValues(form);
          recalculate(form);
        });

        var resetButton = document.getElementById("reset-to-defaults");
        if (resetButton) {
          resetButton.addEventListener("click", function () {
            clearStoredFormValues();
            form.reset();
            // Native form.reset() does not fire "change" reliably across
            // browsers for our purposes, and the group-discount pair needs
            // an explicit resync.
            var discountRange = form.querySelector("#discount-range");
            var discountNumber = form.querySelector("#discount-number");
            if (discountRange && discountNumber) {
              discountNumber.value = discountRange.value;
            }
            recalculate(form);
            announce("Reset to default values.");
          });
        }

        // Recalculate immediately on load if any values were restored,
        // so the tables reflect the restored inputs rather than the
        // server-rendered defaults until the user next interacts.
        if (stored) {
          recalculate(form);
        }
      });
    }

    document.addEventListener("DOMContentLoaded", function () {
      setupCompareTimingForm();
      setupRangeNumberPairs();
    });

    win.ontarioHomeEnergyFutures = api;
  }
});
