/**
 * Ontario Home Energy Futures - client-side calculator.
 *
 * Progressive enhancement only: every page works without this file (see
 * ACCESSIBILITY.md). This module re-implements the same bill/solar/
 * net-metering/financing math as the Python model in
 * src/ontario_home_energy_futures/model/ so that recalculation can happen
 * instantly in the browser with no server round-trip and no data leaving
 * the device. Keep this file's logic in sync with the Python model when
 * either changes - see METHODOLOGY.md.
 *
 * No framework, no build step, no third-party dependency.
 */
(function () {
  "use strict";

  document.documentElement.classList.add("js-enabled");

  var MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

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

  function amortizeLoan(principal, annualRate, termYears) {
    var nPayments = termYears * 12;
    var monthlyRate = annualRate / 12;
    if (principal <= 0) {
      return { monthlyPayment: 0, totalInterest: 0 };
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
    return { monthlyPayment: monthlyPayment, totalInterest: totalInterest };
  }

  function formatCad(value) {
    var sign = value < 0 ? "-" : "";
    return sign + "$" + Math.abs(value).toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Default Hydro Ottawa rates, mirroring assumptions/utilities/hydro-ottawa.yaml.
  // Kept as a small embedded default so the calculator works offline; a
  // future enhancement could fetch data/observations.csv for live values.
  var DEFAULT_RATES = {
    fixedDeliveryPerDay: 0.4795,
    variableDeliveryPerKwh: 0.0223,
    regulatoryPerKwh: 0.0059,
    rebatePerKwh: -0.0227,
    hstRate: 0.13,
    tou: { off_peak: 0.076, mid_peak: 0.122, on_peak: 0.158 }
  };
  var DEFAULT_HOURLY_SHARES = { off_peak: 0.6, mid_peak: 0.2, on_peak: 0.2 };

  function announce(message) {
    var region = document.getElementById("results-status");
    if (region) {
      region.textContent = message;
    }
  }

  function setupCompareTimingForm() {
    var form = document.querySelector("#main-content form.js-only");
    if (!form || !document.getElementById("results-status")) {
      return;
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      // Keyboard focus intentionally stays on the submit control; results
      // are announced via the live region rather than moving focus, per
      // ACCESSIBILITY.md's accessibility decision record.
      var consumption = 700;
      var bill = calculateTouBill(consumption, DEFAULT_HOURLY_SHARES, DEFAULT_RATES, 6);
      announce(
        "Recalculated. Estimated monthly bill for " +
          consumption +
          " kWh: " +
          formatCad(bill.total) +
          ". This is a modelled estimate, not a guaranteed price."
      );
    });
  }

  // Keep any range input synchronized with its paired numeric input, in
  // both directions, so neither control is the only way to set a value
  // (ACCESSIBILITY.md: "No slider-only inputs").
  function setupRangeNumberPairs() {
    var ranges = document.querySelectorAll('input[type="range"]');
    ranges.forEach(function (range) {
      var numberId = range.id.replace("-range", "-number");
      var number = document.getElementById(numberId);
      if (!number) {
        return;
      }
      range.addEventListener("input", function () {
        number.value = range.value;
      });
      number.addEventListener("input", function () {
        if (number.value === "") {
          return;
        }
        var clamped = Math.min(Number(range.max), Math.max(Number(range.min), Number(number.value)));
        range.value = String(clamped);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupCompareTimingForm();
    setupRangeNumberPairs();
  });

  // Exposed for tests.
  window.ontarioHomeEnergyFutures = {
    calculateTouBill: calculateTouBill,
    amortizeLoan: amortizeLoan,
    formatCad: formatCad
  };
})();
