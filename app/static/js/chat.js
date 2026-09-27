// Chatknapp og chatvindu. Sender meldinger til POST /api/chat (stubb inntil kundeservice-agenten er koblet til).
(function () {
  const root = document.getElementById("chat-root");
  if (!root) return;

  root.innerHTML = `
    <button id="chat-fab" type="button" aria-expanded="false" aria-controls="chat-window"
            class="bg-brand-700 hover:bg-brand-800 text-white rounded-full shadow-lg px-5 py-3 font-medium flex items-center gap-2">
      <span aria-hidden="true">💬</span> Chat med oss
    </button>
    <section id="chat-window" hidden aria-label="Chat med kundeservice"
             class="bg-white border border-stone-200 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      <header class="bg-brand-700 text-white px-4 py-3 flex items-center justify-between">
        <span class="font-semibold">Kundeservice</span>
        <button type="button" id="chat-close" class="text-white/80 hover:text-white text-xl leading-none" aria-label="Lukk chat">×</button>
      </header>
      <div id="chat-messages" class="flex-1 overflow-y-auto p-3 space-y-2 text-sm bg-stone-50" aria-live="polite"></div>
      <form id="chat-form" class="border-t border-stone-200 p-2 flex gap-2">
        <input id="chat-input" type="text" autocomplete="off" placeholder="Skriv en melding …" aria-label="Melding"
               class="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm">
        <button class="bg-brand-700 hover:bg-brand-800 text-white rounded-lg px-4 text-sm font-medium">Send</button>
      </form>
    </section>`;

  const fab = document.getElementById("chat-fab");
  const win = document.getElementById("chat-window");
  const messages = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const history = [];

  function toggle(open) {
    win.hidden = !open;
    fab.setAttribute("aria-expanded", String(open));
    if (open) input.focus();
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function inlineFormat(s) {
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`([^`]+?)`/g, '<code class="bg-stone-100 rounded px-1 py-0.5 text-xs">$1</code>');
    return s;
  }

  // Enkel, trygg markdown-tolkning av svar fra agenten: fet skrift, kode, lister og avsnitt.
  // All tekst rømmes (escapeHtml) før noen tagger legges til, så innhold fra agenten kan aldri
  // injisere HTML.
  function renderMarkdownLite(raw) {
    const lines = escapeHtml(raw).split("\n");
    const out = [];
    let para = [];
    let i = 0;

    function flushPara() {
      if (para.length) {
        out.push('<p class="mb-1 last:mb-0">' + para.map(inlineFormat).join("<br>") + "</p>");
        para = [];
      }
    }

    while (i < lines.length) {
      const trimmed = lines[i].trim();

      if (trimmed === "") { flushPara(); i++; continue; }

      const heading = trimmed.match(/^#{1,6}\s+(.*)$/);
      if (heading) {
        flushPara();
        out.push('<p class="font-semibold mt-2 mb-1">' + inlineFormat(heading[1]) + "</p>");
        i++; continue;
      }

      if (/^[-*]\s+/.test(trimmed)) {
        flushPara();
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
          i++;
        }
        out.push('<ul class="list-disc pl-4 my-1 space-y-0.5">'
          + items.map((t) => "<li>" + inlineFormat(t) + "</li>").join("") + "</ul>");
        continue;
      }

      if (/^\d+\.\s+/.test(trimmed)) {
        flushPara();
        const items = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
          i++;
        }
        out.push('<ol class="list-decimal pl-4 my-1 space-y-0.5">'
          + items.map((t) => "<li>" + inlineFormat(t) + "</li>").join("") + "</ol>");
        continue;
      }

      para.push(lines[i]);
      i++;
    }
    flushPara();
    return out.join("");
  }

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = role === "user"
      ? "ml-8 bg-brand-600 text-white rounded-2xl rounded-br-sm px-3 py-2 w-fit max-w-full self-end"
      : "mr-8 bg-white border border-stone-200 rounded-2xl rounded-bl-sm px-3 py-2 w-fit max-w-full";
    el.dataset.role = role;
    setMessageText(el, text);
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function setMessageText(el, text) {
    if (el.dataset.role === "assistant") {
      el.innerHTML = renderMarkdownLite(text);
    } else {
      el.textContent = text;
    }
  }

  fab.addEventListener("click", () => toggle(win.hidden));
  document.getElementById("chat-close").addEventListener("click", () => toggle(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !win.hidden) toggle(false); });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMessage("user", text);
    const pending = addMessage("assistant", "…");
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setMessageText(pending, data.reply);
      history.push({ role: "user", content: text }, { role: "assistant", content: data.reply });
    } catch (err) {
      setMessageText(pending, "Beklager, noe gikk galt. Prøv igjen senere.");
    }
  });
})();
