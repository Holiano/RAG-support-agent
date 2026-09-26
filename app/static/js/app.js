// Små forbedringer med vanilla JavaScript. Siden fungerer også uten.
(function () {
  const nok = (n) => n.toLocaleString("nb-NO").replace(/\s/g, " ") + " kr";

  // Send skjema automatisk når antall eller fraktvalg endres (handlekurv).
  document.querySelectorAll("form[data-autosubmit]").forEach((form) => {
    form.querySelectorAll("input").forEach((input) => {
      input.addEventListener("change", () => form.submit());
    });
  });

  // Fyll inn demobruker ved klikk på e-postadressen (innlogging).
  document.querySelectorAll("[data-fill-login]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("email").value = btn.dataset.fillLogin;
      document.getElementById("password").value = "demo123";
      document.getElementById("password").focus();
    });
  });

  // Kasse: oppdater frakt og totalsum når fraktmetode byttes.
  const total = document.getElementById("sum-total");
  if (total) {
    const goods = parseInt(total.dataset.goods, 10);
    document.querySelectorAll('input[name="method"]').forEach((radio) => {
      radio.addEventListener("change", () => {
        const price = parseInt(radio.dataset.price, 10);
        document.getElementById("sum-method").textContent = radio.dataset.name;
        document.getElementById("sum-shipping").textContent = price === 0 ? "Gratis" : nok(price);
        total.textContent = nok(goods + price);
      });
    });
  }

  // Produktside: hold antall innenfor lagerbeholdningen til valgt variant.
  const variants = document.getElementById("variants");
  const qty = document.getElementById("quantity");
  if (variants && qty) {
    const sync = () => {
      const chosen = variants.querySelector('input[name="sku"]:checked');
      if (!chosen) return;
      const max = Math.min(10, parseInt(chosen.dataset.stock, 10));
      qty.max = String(max);
      if (parseInt(qty.value, 10) > max) qty.value = String(max);
    };
    variants.addEventListener("change", sync);
    sync();
  }
})();
