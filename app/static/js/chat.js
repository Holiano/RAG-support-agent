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
  const GREETING = "Hei, hva kan jeg hjelpe deg med?";
  const SUGGESTIONS = ["Hvor er pakken min?", "Hvordan returnerer jeg en vare?", "Hva koster frakt?"];
  let greeted = false;

  function toggle(open) {
    win.hidden = !open;
    fab.setAttribute("aria-expanded", String(open));
    if (open && !greeted) greet();
    if (open) input.focus();
  }

  // Hilsen og forslag vises første gang vinduet åpnes. Hilsenen sendes ikke med i historikken til agenten.
  function greet() {
    greeted = true;
    addMessage("assistant", GREETING);
    const box = document.createElement("div");
    box.id = "chat-suggestions";
    box.className = "flex flex-wrap gap-2 mr-8";
    for (const q of SUGGESTIONS) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = q;
      b.className = "text-left text-sm bg-white border border-brand-600 text-brand-700 hover:bg-brand-50 rounded-full px-3 py-1.5";
      b.addEventListener("click", () => send(q));
      box.appendChild(b);
    }
    messages.appendChild(box);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeSuggestions() {
    const box = document.getElementById("chat-suggestions");
    if (box) box.remove();
  }

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Gjengir et lite, trygt utvalg av Markdown fra agenten: avsnitt, linjeskift, **fet** og punktlister.
  // Teksten escapes først, så ingen HTML fra modellen slipper gjennom.
  function renderMarkdown(text) {
    const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    const isItem = (l) => /^\s*[-*•]\s+/.test(l);
    const html = [];
    let para = [], items = [];
    const flushPara = () => { if (para.length) html.push("<p>" + para.map(inline).join("<br>") + "</p>"); para = []; };
    const flushList = () => {
      if (items.length) html.push("<ul class=\"list-disc pl-5 space-y-0.5\">" +
        items.map((l) => "<li>" + inline(l.replace(/^\s*[-*•]\s+/, "")) + "</li>").join("") + "</ul>");
      items = [];
    };
    for (const line of text.trim().split("\n")) {
      if (!line.trim()) { flushPara(); flushList(); }
      else if (isItem(line)) { flushPara(); items.push(line); }
      else { flushList(); para.push(line); }
    }
    flushPara(); flushList();
    return html.join("");
  }

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = role === "user"
      ? "ml-8 bg-brand-600 text-white rounded-2xl rounded-br-sm px-3 py-2 w-fit max-w-full self-end"
      : "mr-8 bg-white border border-stone-200 rounded-2xl rounded-bl-sm px-3 py-2 w-fit max-w-full space-y-2";
    setMessage(el, role, text);
    el.dataset.role = role;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function setMessage(el, role, text) {
    if (role === "user") el.textContent = text;
    else el.innerHTML = renderMarkdown(text);
  }

  fab.addEventListener("click", () => toggle(win.hidden));
  document.getElementById("chat-close").addEventListener("click", () => toggle(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !win.hidden) toggle(false); });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    send(text);
  });

  async function send(text) {
    removeSuggestions();
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
      setMessage(pending, "assistant", data.reply);
      history.push({ role: "user", content: text }, { role: "assistant", content: data.reply });
    } catch (err) {
      setMessage(pending, "assistant", "Beklager, noe gikk galt. Prøv igjen senere.");
    }
  }
})();
