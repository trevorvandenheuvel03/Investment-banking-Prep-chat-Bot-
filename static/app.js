/* global WebSocket, location */
(() => {
    const chat = document.getElementById("chat");
    const input = document.getElementById("input");
    const levelEl = document.getElementById("level");
    const answeredEl = document.getElementById("answered");
    const avgEl = document.getElementById("avg");
    const timerEl = document.getElementById("timer");

    const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") +
                  location.host + "/ws";
    const ws = new WebSocket(wsUrl);

    let countdownId = null;

    function append(text, cls = "") {
        const p = document.createElement("p");
        if (cls) p.className = cls;
        p.textContent = text;
        chat.appendChild(p);
        chat.scrollTop = chat.scrollHeight;
    }

    function startTimer(seconds) {
        clearInterval(countdownId);
        timerEl.textContent = seconds;
        countdownId = setInterval(() => {
            seconds -= 1;
            timerEl.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(countdownId);
                ws.send(JSON.stringify({type: "answer", answer: "Time’s up — please summarise"}));
            }
        }, 1000);
    }

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "question") {
            append(`🛈 (${msg.level}) ${msg.category.toUpperCase()} Q: ${msg.text}`, "q");
            startTimer(msg.time);
        }

        if (msg.type === "feedback") {
            append(`✓ Score ${msg.score}/5 — ${msg.explanation}`, "fb");
        }

        if (msg.stats) {
            levelEl.textContent = msg.stats.level;
            answeredEl.textContent = msg.stats.answered;
            const avg = msg.stats.answered ? (msg.stats.total_score / msg.stats.answered).toFixed(2) : 0;
            avgEl.textContent = avg;
        }
    };

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.value.trim() !== "") {
            append(`You: ${input.value}`, "you");
            ws.send(JSON.stringify({type: "answer", answer: input.value.trim()}));
            input.value = "";
            clearInterval(countdownId); // stop timer; server will start new one
        }
    });
})();
