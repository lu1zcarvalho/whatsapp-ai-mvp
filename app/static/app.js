const sessionId = "demo";
const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const resetButton = document.querySelector("#resetButton");
const quickButtons = document.querySelectorAll("[data-message]");

function currentTime() {
  return new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function scrollToLatest() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(text, sender) {
  const article = document.createElement("article");
  article.className = `message ${sender === "customer" ? "customer-message" : "assistant-message"}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  const time = document.createElement("time");
  time.textContent = currentTime();
  article.append(paragraph, time);
  messages.append(article);
  scrollToLatest();
  return article;
}

function showTyping() {
  const article = document.createElement("article");
  article.className = "message assistant-message typing";
  article.setAttribute("aria-label", "Atendente digitando");
  article.innerHTML = "<span></span><span></span><span></span>";
  messages.append(article);
  scrollToLatest();
  return article;
}

async function sendMessage(value) {
  const text = value.trim();
  if (!text || sendButton.disabled) return;

  addMessage(text, "customer");
  input.value = "";
  input.focus();
  sendButton.disabled = true;
  const typing = showTyping();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    await new Promise(resolve => setTimeout(resolve, 650));
    typing.remove();
    addMessage(data.reply, "assistant");
  } catch (error) {
    typing.remove();
    addMessage("Não consegui responder agora. Verifique se a API está rodando e tente novamente.", "assistant");
    console.error(error);
  } finally {
    sendButton.disabled = false;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});

quickButtons.forEach(button => {
  button.addEventListener("click", () => sendMessage(button.dataset.message));
});

resetButton.addEventListener("click", async () => {
  resetButton.disabled = true;
  try {
    await fetch("/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
    messages.replaceChildren();
    const day = document.createElement("div");
    day.className = "day-pill";
    day.textContent = "Hoje";
    messages.append(day);
    addMessage("Olá! 😊 Bem-vindo à WD iPhones. Qual modelo você está procurando?", "assistant");
  } catch (error) {
    addMessage("Não foi possível iniciar uma nova conversa.", "assistant");
  } finally {
    resetButton.disabled = false;
    input.focus();
  }
});

document.querySelectorAll(".message time").forEach(time => { time.textContent = currentTime(); });
input.focus();
