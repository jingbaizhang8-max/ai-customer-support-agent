import { useState } from "react";
import "./App.css";
import Markdown from "react-markdown";
import TicketPanel from "./TicketPanel";
import AuthPanel from "./AuthPanel";

const welcomeMessage = {
  id: "welcome",
  role: "assistant",
  content: "你好！我是 AI 客服助手，请问有什么可以帮助你？",
};

function App() {
  const [messages, setMessages] = useState([welcomeMessage]);
  const [input, setInput] = useState("");
  const [token, setToken] = useState("");
  const [conversationId, setConversationId] = useState(
    () => crypto.randomUUID()
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function newConversation() {
    setConversationId(crypto.randomUUID());
    setMessages([welcomeMessage]);
    setError("");
    setInput("");
  }

//   function updateToken(value) {
//     setToken(value);
//     newConversation();
//   }

  async function handleSend(event) {
    event.preventDefault();

    const text = input.trim();

    if (!text || loading) return;

    if (!token.trim()) {
      setError("请先输入本地开发测试 JWT。");
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token.trim()}`,
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("JWT 无效或已过期，请生成新 Token。");
        }

        throw new Error(
          `Agent 请求失败：HTTP ${response.status}`
        );
      }

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.content || "Agent 没有返回内容。",
        },
      ]);
    } catch (err) {
      setError(err.message || "网络请求失败，请检查后端服务。");
    } finally {
      setLoading(false);
    }
  }


return (
  <div className="chat-container">
    <header className="chat-header">
      <h1>AI Customer Support</h1>
      <p>智能客服 · 订单查询 · 退款申请</p>

      {token && (
        <button
          className="new-chat-button"
          type="button"
          onClick={newConversation}
        >
          新建会话
        </button>
      )}
    </header>

    <div className="dev-auth">
      {!token ? (
        <AuthPanel
          onLogin={(accessToken) => {
            setMessages([]);
            setConversationId(crypto.randomUUID());
            setInput("");
            setError("");
            setToken(accessToken);
          }}
        />
      ) : (
        <div className="login-status">
          <span>客户已登录</span>

          <button
            type="button"
            onClick={() => {
              setToken("");
              setMessages([]);
              setConversationId(crypto.randomUUID());
              setInput("");
              setError("");
            }}
          >
            退出登录
          </button>
        </div>
      )}
    </div>

    {token && (
      <>
        <main className="chat-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.role}`}
            >
              <Markdown>{message.content}</Markdown>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              AI 正在处理，请稍候...
            </div>
          )}
        </main>

        {error && (
          <p className="chat-error" role="alert">
            {error}
          </p>
        )}

        <form
          className="chat-input"
          onSubmit={handleSend}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="请输入你的问题..."
            disabled={loading}
          />

          <button
            type="submit"
            disabled={loading}
          >
            {loading ? "处理中..." : "发送"}
          </button>
        </form>

        <TicketPanel
          key={conversationId}
          token={token}
        />
      </>
    )}

    <footer className="chat-footer">
      本地开发环境 · 模拟退款不涉及真实资金
    </footer>
  </div>
);
}

export default App;
