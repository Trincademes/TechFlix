function handleEnter(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

function quickMessage(text) {
    document.getElementById("message").value = text;
    sendMessage();
}

function addUserMessage(text) {
    const chatBox = document.getElementById("chat-box");

    chatBox.innerHTML += `
        <div class="message-row user-row">
            <div class="message user">
                <span class="message-author">Você</span>
                ${text}
            </div>
        </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;
}

function addBotMessage(text, id = null) {
    const chatBox = document.getElementById("chat-box");
    const idAttribute = id ? `id="${id}"` : "";

    chatBox.innerHTML += `
        <div class="message-row bot-row">
            <div class="small-avatar">🤖</div>
            <div class="message bot" ${idAttribute}>
                <span class="message-author">TechFix AI</span>
                ${text}
            </div>
        </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("message");
    const msg = input.value.trim();

    if (msg === "") return;

    addUserMessage(msg);
    input.value = "";

    const typingId = "typing-" + Date.now();
    addBotMessage("Digitando...", typingId);

    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => {
        const typingMessage = document.getElementById(typingId);
        typingMessage.innerHTML = `
            <span class="message-author">TechFix AI</span>
            ${data.reply}
        `;

        const chatBox = document.getElementById("chat-box");
        chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(() => {
        const typingMessage = document.getElementById(typingId);
        typingMessage.innerHTML = `
            <span class="message-author">TechFix AI</span>
            Erro ao conectar com o agente.
        `;
    });
}