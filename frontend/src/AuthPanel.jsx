
import { useState } from "react";

export default function AuthPanel({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`/auth/${mode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : `请求失败：HTTP ${response.status}`
        );
      }

      if (mode === "register") {
        setMode("login");
        setPassword("");
        setMessage("注册成功，请登录。");
        return;
      }

      if (!data.access_token) {
        throw new Error("登录响应缺少 access_token");
      }

      setPassword("");
      onLogin(data.access_token, data.customer_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode() {
    setMode(mode === "login" ? "register" : "login");
    setPassword("");
    setError("");
    setMessage("");
  }

  return (
    <section className="auth-panel">
      <h2>{mode === "login" ? "客户登录" : "客户注册"}</h2>

      <form onSubmit={handleSubmit}>
        <label>
          邮箱
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>

        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={mode === "register" ? 12 : undefined}
            autoComplete={
              mode === "login"
                ? "current-password"
                : "new-password"
            }
          />
        </label>

        <button type="submit" disabled={loading}>
          {loading
            ? "处理中..."
            : mode === "login"
              ? "登录"
              : "注册"}
        </button>
      </form>

      <button type="button" onClick={switchMode}>
        {mode === "login"
          ? "没有账户？立即注册"
          : "已有账户？返回登录"}
      </button>

      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
