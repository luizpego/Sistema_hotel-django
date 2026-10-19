"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".mobile-toggle");
  const nav = document.getElementById("navigation");
  if (toggle && nav) toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    nav.classList.toggle("open", open);
  });
  document.querySelectorAll("form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  const exportForm = document.getElementById("export-form");
  if (exportForm) exportForm.addEventListener("submit", event => {
    const kind = document.getElementById("report-kind").value;
    const button = document.getElementById("export-button");
    exportForm.action = button.dataset.base + "exportar/" + encodeURIComponent(kind) + "/";
  });
  document.querySelectorAll(".field-invalid input, .field-invalid select, .field-invalid textarea")
    .forEach(field => field.setAttribute("aria-invalid", "true"));
});
