import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Form, Input } from "antd";
import { useAppMessage } from "../../hooks/useAppMessage";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { authApi } from "../../api/modules/auth";
import { setAuthToken } from "../../api/config";
import { useTheme } from "../../contexts/ThemeContext";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isDark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const { message } = useAppMessage();

  useEffect(() => {
    authApi
      .getStatus()
      .then((res) => {
        if (!res.enabled) {
          navigate("/chat", { replace: true });
          return;
        }
        setHasUsers(res.has_users);
        if (!res.has_users) {
          setIsRegister(true);
        }
      })
      .catch(() => {});
  }, [navigate]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const raw = searchParams.get("redirect") || "/chat";
      const redirect =
        raw.startsWith("/") && !raw.startsWith("//") ? raw : "/chat";

      if (isRegister) {
        const res = await authApi.register(values.username, values.password);
        if (res.token) {
          setAuthToken(res.token);
          message.success(t("login.registerSuccess"));
          navigate(redirect, { replace: true });
        }
      } else {
        const res = await authApi.login(values.username, values.password);
        if (res.token) {
          setAuthToken(res.token);
          navigate(redirect, { replace: true });
        } else {
          message.info(t("login.authNotEnabled"));
          navigate(redirect, { replace: true });
        }
      }
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : "";
      message.error(
        rawMessage ||
          (isRegister ? t("login.registerFailed") : t("login.failed")),
      );
    } finally {
      setLoading(false);
    }
  };

  const bg = isDark ? "#111110" : "#F7F6F2";
  const cardBg = isDark ? "#1A1917" : "#FAFAF8";
  const border = isDark ? "rgba(255,255,255,0.072)" : "rgba(0,0,0,0.072)";
  const text = isDark ? "#F2F1ED" : "#1A1917";
  const textMuted = isDark ? "rgba(242,241,237,0.50)" : "rgba(26,25,23,0.45)";
  const accent = isDark ? "#FF8C2A" : "#E8650A";
  const inputBg = isDark ? "#222120" : "#fff";
  const shadow = isDark
    ? "0 8px 32px rgba(0,0,0,0.55), 0 2px 8px rgba(0,0,0,0.35)"
    : "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)";

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: bg,
        fontFamily: "'DM Sans', system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Subtle background pattern */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage: isDark
            ? "radial-gradient(circle at 30% 20%, rgba(255,140,42,0.06) 0%, transparent 60%), radial-gradient(circle at 70% 80%, rgba(255,140,42,0.04) 0%, transparent 50%)"
            : "radial-gradient(circle at 30% 20%, rgba(232,101,10,0.06) 0%, transparent 60%), radial-gradient(circle at 70% 80%, rgba(232,101,10,0.04) 0%, transparent 50%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          width: 380,
          padding: "36px 32px 32px",
          borderRadius: 16,
          background: cardBg,
          border: `1px solid ${border}`,
          boxShadow: shadow,
          position: "relative",
        }}
      >
        {/* Logo area */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <img
            src="/logo.png"
            alt="Nexora"
            style={{
              height: 64,
              width: "auto",
              marginBottom: 20,
              display: "block",
              margin: "0 auto 20px",
            }}
          />
          <h1
            style={{
              margin: "0 0 6px",
              fontSize: 20,
              fontWeight: 600,
              color: text,
              letterSpacing: "-0.4px",
              fontFamily: "'DM Sans', system-ui, sans-serif",
            }}
          >
            {isRegister ? t("login.registerTitle") : t("login.title")}
          </h1>
          {!hasUsers && (
            <p
              style={{
                margin: "8px 0 0",
                color: textMuted,
                fontSize: 13,
                lineHeight: 1.5,
                fontFamily: "'DM Sans', system-ui, sans-serif",
              }}
            >
              {t("login.firstUserHint")}
            </p>
          )}
        </div>

        <Form
          layout="vertical"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: t("login.usernameRequired") }]}
            style={{ marginBottom: 12 }}
          >
            <Input
              prefix={
                <UserOutlined style={{ color: textMuted, fontSize: 14 }} />
              }
              placeholder={t("login.usernamePlaceholder")}
              autoFocus
              style={{
                background: inputBg,
                borderColor: border,
                color: text,
                borderRadius: 8,
                fontFamily: "'DM Sans', system-ui, sans-serif",
                fontSize: 14,
                height: 42,
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: t("login.passwordRequired") }]}
            style={{ marginBottom: 20 }}
          >
            <Input.Password
              prefix={
                <LockOutlined style={{ color: textMuted, fontSize: 14 }} />
              }
              placeholder={t("login.passwordPlaceholder")}
              style={{
                background: inputBg,
                borderColor: border,
                color: text,
                borderRadius: 8,
                fontFamily: "'DM Sans', system-ui, sans-serif",
                fontSize: 14,
                height: 42,
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                height: 42,
                borderRadius: 9,
                background: loading
                  ? isDark ? "rgba(255,140,42,0.6)" : "rgba(232,101,10,0.6)"
                  : accent,
                border: "none",
                color: "#fff",
                fontSize: 14,
                fontWeight: 550,
                fontFamily: "'DM Sans', system-ui, sans-serif",
                cursor: loading ? "not-allowed" : "pointer",
                letterSpacing: "0.01em",
                transition: "all 0.15s cubic-bezier(0.4,0,0.2,1)",
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    isDark ? "#FF9F47" : "#CF5A09";
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  (e.currentTarget as HTMLButtonElement).style.background = accent;
                }
              }}
            >
              {loading
                ? "..."
                : isRegister
                ? t("login.register")
                : t("login.submit")}
            </button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}