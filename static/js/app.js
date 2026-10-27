/* Small progressive enhancements. Nothing here is required for the app to
   work: every action is a normal form post or link. */
(function () {
  "use strict";

  // Confirm irreversible or state-changing actions before submitting.
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  // Toggle the sidebar on narrow screens.
  var toggle = document.querySelector("[data-nav-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
    });
  }

  // Auto-submit filter selects (period comparison on the trends page).
  document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form) { select.form.submit(); }
    });
  });
})();
