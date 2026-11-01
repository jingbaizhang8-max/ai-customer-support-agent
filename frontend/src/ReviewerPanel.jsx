
import { useState } from "react";

export default function ReviewerPanel() {
  const [token, setToken] = useState("");
  const [tickets, setTickets] = useState([]);
  const [reasons, setReasons] = useState({});
  const [loading, setLoading] = useState(false);
  const [busyTicketId, setBusyTicketId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [readyTickets, setReadyTickets] = useState([]);



    async function loadTickets() {
      if (!token.trim()) {
        setError("请先输入审核员 JWT");
        return;
      }

      setLoading(true);
      setError("");

      try {
        const headers = {
          Authorization: `Bearer ${token.trim()}`,
        };

        const [pendingResponse, readyResponse] = await Promise.all([
          fetch("/reviews/pending?limit=50", {
            headers,
            cache: "no-store",
          }),
          fetch("/reviews/ready-for-refund?limit=50", {
            headers,
            cache: "no-store",
          }),
        ]);

        if (!pendingResponse.ok) {
          throw new Error(
            `获取待审核工单失败：HTTP ${pendingResponse.status}`
          );
        }

        if (!readyResponse.ok) {
          throw new Error(
            `获取待退款队列失败：HTTP ${readyResponse.status}`
          );
        }

        const [pendingData, readyData] = await Promise.all([
          pendingResponse.json(),
          readyResponse.json(),
        ]);

        if (!Array.isArray(pendingData) || !Array.isArray(readyData)) {
          throw new Error("服务器返回的工单格式不正确");
        }

        setTickets(pendingData);
        setReadyTickets(readyData);
        setLoaded(true);
      } catch (err) {
        setTickets([]);
        setReadyTickets([]);
        setLoaded(false);
        setError(err.message || "查询失败");
      } finally {
        setLoading(false);
      }
    }


  async function handleReview(ticket, decision) {
    if (busyTicketId !== null) return;

    const reason = (reasons[ticket.ticket_id] || "").trim();

    if (!reason) {
      setError("请先填写审核理由");
      return;
    }

    if (reason.length > 2000) {
      setError("审核理由不能超过 2000 字");
      return;
    }

    const label = decision === "approved" ? "批准" : "拒绝";

    const confirmed = window.confirm(
      `确认${label}工单 ${ticket.ticket_id} 吗？\n` +
      "审核结果提交后不能直接撤销。"
    );

    if (!confirmed) return;

    setBusyTicketId(ticket.ticket_id);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `/reviews/${encodeURIComponent(ticket.ticket_id)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token.trim()}`,
          },
          body: JSON.stringify({
            decision,
            reason,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new Error(
          `审核失败：HTTP ${response.status} - ` +
          `${data.detail || "服务器错误"}`
        );
      }

      setNotice(`工单 ${ticket.ticket_id} 已${label}，审核记录已提交。`);

      setReasons((previous) => ({
        ...previous,
        [ticket.ticket_id]: "",
      }));

      await loadTickets();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyTicketId(null);
    }
  }


    async function handleSimulateRefund(ticket) {
      if (busyTicketId !== null || loading) return;

      const confirmed = window.confirm(
        `确定要为订单 ${ticket.order_id} 执行模拟退款吗？\n` +
        "该操作会写入数据库，但不会发生真实资金转移。"
      );

      if (!confirmed) return;

      setBusyTicketId(ticket.ticket_id);
      setError("");
      setNotice("");

      try {
        const response = await fetch(
          `/refunds/simulate/${encodeURIComponent(ticket.ticket_id)}`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token.trim()}`,
            },
          }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            `模拟退款失败：HTTP ${response.status} - ` +
            `${data.detail || "服务器错误"}`
          );
        }

        if (data.status !== "simulated_refund_completed") {
          throw new Error("服务器未确认模拟退款完成");
        }

        await loadTickets();

        setNotice(
          `订单 ${ticket.order_id} 模拟退款已完成。` +
          `退款编号：${data.refund_id}。无真实资金流转。`
        );
      } catch (err) {
        setError(err.message || "模拟退款失败");
      } finally {
        setBusyTicketId(null);
      }
    }


  return (
    <div
      style={{
        maxWidth: 1000,
        margin: "40px auto",
        padding: 24,
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1>人工审核后台</h1>
      <p>AI Customer Support · Reviewer Console</p>
      <p>本地开发测试环境 · 不涉及真实资金退款</p>

      <hr />

      <h2>审核员身份验证</h2>

      <label htmlFor="reviewer-token">
        审核员 JWT
      </label>

      <input
        id="reviewer-token"
        type="password"
        value={token}
        disabled={busyTicketId !== null}
        onChange={(e) => {
          setToken(e.target.value);
          setTickets([]);
          setReadyTickets([]);
          setLoaded(false);
          setError("");
          setNotice("");
        }}
        placeholder="粘贴审核员 JWT"
        autoComplete="off"
        style={{
          display: "block",
          width: "100%",
          boxSizing: "border-box",
          padding: 12,
          margin: "12px 0",
        }}
      />

      <button
        type="button"
        onClick={loadTickets}
        disabled={loading || busyTicketId !== null}
      >
        {loading ? "加载中..." : "刷新审核及退款队列"}
      </button>

      {error && (
        <p role="alert" style={{ color: "crimson" }}>
          {error}
        </p>
      )}

      {notice && (
        <p role="status" style={{ color: "green" }}>
          {notice}
        </p>
      )}

      <hr />

      <h2>待审核退款申请</h2>

      {loaded && tickets.length === 0 && (
        <p>当前没有待审核退款工单。</p>
      )}

      {tickets.map((ticket) => (
        <article
          key={ticket.ticket_id}
          style={{
            border: "1px solid #cbd5e1",
            borderRadius: 10,
            padding: 20,
            marginBottom: 16,
          }}
        >
          <h3>订单：{ticket.order_id}</h3>

          <p>
            <strong>工单编号：</strong>
            {ticket.ticket_id}
          </p>

          <p>
            <strong>客户编号：</strong>
            {ticket.customer_id}
          </p>

          <p>
            <strong>状态：</strong>
            {ticket.status}
          </p>

          <p>
            <strong>申请原因：</strong>
            {ticket.description}
          </p>

          <p>
            <strong>提交时间：</strong>
            {ticket.created_at}
          </p>

          <label
            htmlFor={`reason-${ticket.ticket_id}`}
            style={{ display: "block", marginTop: 16 }}
          >
            <strong>人工审核理由</strong>
          </label>

          <textarea
            id={`reason-${ticket.ticket_id}`}
            value={reasons[ticket.ticket_id] || ""}
            onChange={(e) => {
              setReasons((previous) => ({
                ...previous,
                [ticket.ticket_id]: e.target.value,
              }));
            }}
            placeholder="填写批准或拒绝的理由"
            maxLength={2000}
            rows={3}
            disabled={busyTicketId !== null}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: 12,
              marginTop: 8,
              marginBottom: 12,
            }}
          />

          <div style={{ display: "flex", gap: 12 }}>
            <button
              type="button"
              disabled={busyTicketId !== null || loading}
              onClick={() => handleReview(ticket, "approved")}
              style={{
                padding: "10px 20px",
                background: "#16a34a",
                color: "white",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              批准申请
            </button>

            <button
              type="button"
              disabled={busyTicketId !== null || loading}
              onClick={() => handleReview(ticket, "rejected")}
              style={{
                padding: "10px 20px",
                background: "#dc2626",
                color: "white",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              拒绝申请
            </button>
          </div>
        </article>
      ))}

      <hr />

      <h2>待执行模拟退款</h2>

      <p>
        仅显示人工审核已批准、尚未完成模拟退款的订单。
      </p>

      {loaded && readyTickets.length === 0 && (
        <p>当前没有待执行的模拟退款申请。</p>
      )}

      {readyTickets.map((ticket) => (
        <article
          key={ticket.ticket_id}
          style={{
            border: "1px solid #cbd5e1",
            borderRadius: 10,
            padding: 20,
            marginBottom: 16,
          }}
        >
          <h3>订单：{ticket.order_id}</h3>

          <p>工单编号：{ticket.ticket_id}</p>
          <p>客户编号：{ticket.customer_id}</p>
          <p>人工审核状态：{ticket.status}</p>
          <p>申请原因：{ticket.description}</p>

          <button
            type="button"
            disabled={busyTicketId !== null || loading}
            onClick={() => handleSimulateRefund(ticket)}
            style={{
              padding: "10px 20px",
              background: "#2563eb",
              color: "white",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {busyTicketId === ticket.ticket_id
              ? "执行中..."
              : "执行模拟退款"}
          </button>

          <p style={{ fontSize: 13, color: "#64748b" }}>
            本地模拟退款，不涉及真实资金。
          </p>
        </article>
      ))}

    </div>
  );
}
