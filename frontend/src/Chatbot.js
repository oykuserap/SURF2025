import React, { useState } from "react";

function Chatbot() {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! Ask me anything about your documents." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg = { sender: "user", text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    setLoading(true);

    // Call your backend API
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: input })
    });
    const data = await res.json();
    setMessages((msgs) => [...msgs, { sender: "bot", text: data.answer }]);
    setInput("");
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 500, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h2>Chatbot</h2>
      <div style={{ border: "1px solid #ccc", padding: 16, minHeight: 200, marginBottom: 8 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ textAlign: msg.sender === "user" ? "right" : "left" }}>
            <b>{msg.sender === "user" ? "You" : "Bot"}:</b> {msg.text}
          </div>
        ))}
        {loading && <div>Bot is typing…</div>}
      </div>
      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          style={{ width: "80%", padding: 8 }}
          placeholder="Type your question..."
        />
        <button type="submit" style={{ padding: 8 }}>Send</button>
      </form>
    </div>
  );
}

export default Chatbot;