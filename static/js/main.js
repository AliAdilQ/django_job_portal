"use strict";
document.querySelectorAll(".dashboard-sidebar nav a, .navbar-nav a").forEach((link) => {
  if (new URL(link.href).pathname === window.location.pathname) {
    link.classList.add("active");
    link.setAttribute("aria-current", "page");
  }
});
document.querySelectorAll("[data-submit-change]").forEach((select) => {
  select.addEventListener("change", () => select.form.requestSubmit());
});
document.querySelectorAll(".form-field").forEach((group) => {
  const control = group.querySelector("input, select, textarea");
  const error = group.querySelector(".field-error");
  if (control && error) {
    control.setAttribute("aria-invalid", "true");
    error.id = `${control.id}_error`;
    control.setAttribute("aria-describedby", [control.getAttribute("aria-describedby"), error.id].filter(Boolean).join(" "));
  }
});
