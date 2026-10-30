import { useRef, useState } from "react";
import "./TicketPanel.css";

export default function TicketPanel({ token }) {
  const [orderId, setOrderId] = useState("");
  const [description, setDescription] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [ticketId, setTicketId] = useState("");
  const [ticketStatus, setTicketStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 请求失败后重试时，沿用同一幂等键
  const idempotencyKey = useRef(crypto.randomUUID());

  function changeForm(setter, value) {
    setter(value);
    idempotencyKey.current = crypto.randomUUID();
    setError("");
  }

  async function submitTicket(event) {
    event.preventDefault();

    if (!token.trim() || !confirmed || loading) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/tickets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token.trim()}`,
          "Idempotency-Key": idempotencyKey.current,
        },
        body: JSON.stringify({
          order_id: orderId.trim(),
          ticket_type: "refund_request",
          description: description.trim(),
          confirmed: true,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          response.status === 401
            ? "JWT 无效或已过期"
            : `创建失败 HTTP ${response.status}: ${JSON.stringify(data.detail ?? data)}`
        );
      }

      const createdId = data.ticket_id ?? data.ticket?.ticket_id;

      if (!createdId) {
        throw new Error("响应未包含 ticket_id，请检查后端返回格式");
      }

      setTicketId(createdId);
      setTicketStatus(data.status ?? data.ticket?.status ?? "");
      setConfirmed(false);
      idempotencyKey.current = crypto.randomUUID();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshStatus() {
    if (!ticketId || loading) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `/tickets/${encodeURIComponent(ticketId)}`,
        {
          headers: {
            Authorization: `Bearer ${token.trim()}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(`查询失败 HTTP ${response.status}`);
      }

      setTicketStatus(data.status ?? data.ticket?.status ?? "未知");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="ticket-panel">
      <h2>退款申请</h2>
      <p>提交后进入人工审核流程，不会自动退款。</p>

      <form onSubmit={submitTicket}>
        <label htmlFor="ticket-order">订单编号</label>
        <input
          id="ticket-order"
          value={orderId}
          onChange={(e) => changeForm(setOrderId, e.target.value)}
          placeholder="例如 ORD-1001"
          required
        />

        <label htmlFor="ticket-reason">申请原因</label>
        <textarea
          id="ticket-reason"
          value={description}
          onChange={(e) =>
            changeForm(setDescription, e.target.value)
          }
          placeholder="请描述退款原因"
          required
          rows={3}
        />

        <label className="ticket-confirm">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          我确认提交退款申请，等待人工审核
        </label>

        <button
          type="submit"
          disabled={loading || !confirmed || !token.trim() || Boolean(ticketId)}
        >
          {loading ? "处理中..." : "提交退款申请"}
        </button>
      </form>

      {ticketId && (
        <div className="ticket-result">
          <strong>申请已创建</strong>
          <p>工单编号：{ticketId}</p>
          <p>当前状态：{ticketStatus || "请查询状态"}</p>
          <button
            type="button"
            onClick={refreshStatus}
            disabled={loading}
          >
            刷新工单状态
          </button>
        </div>
      )}

      {error && <p className="ticket-error" role="alert">{error}</p>}

      <small>Demo 模拟售后系统 · 不涉及真实资金流转</small>
    </section>
  );
}
