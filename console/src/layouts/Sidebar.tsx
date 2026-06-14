import {
  Layout,
  Menu,
  Button,
  Modal,
  Input,
  Form,
  Tooltip,
  type MenuProps,
} from "antd";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAppMessage } from "../hooks/useAppMessage";
import AgentSelector from "../components/AgentSelector";
import {
  SparkChatTabFill,
  SparkWifiLine,
  SparkUserGroupLine,
  SparkDateLine,
  SparkVoiceChat01Line,
  SparkMagicWandLine,
  SparkLocalFileLine,
  SparkModePlazaLine,
  SparkInternetLine,
  SparkModifyLine,
  SparkBrowseLine,
  SparkMcpMcpLine,
  SparkScanLine,
  SparkToolLine,
  SparkDataLine,
  SparkMicLine,
  SparkAgentLine,
  SparkSearchUserLine,
  SparkMenuExpandLine,
  SparkMenuFoldLine,
  SparkOtherLine,
  SparkBarChartLine,
  SparkDebugLine,
  SparkSaveLine,
  SparkCardLine,
} from "@agentscope-ai/icons";
import { CheckSquare, Package } from "lucide-react";
import { clearAuthToken } from "../api/config";
import { authApi } from "../api/modules/auth";
import { usersApi } from "../jotaduo/api/users";
import { usePlugins } from "../plugins/PluginContext";
import { useCodingMode } from "../stores/codingModeStore";
import styles from "./index.module.less";
import { useTheme } from "../contexts/ThemeContext";
import { KEY_TO_PATH, DEFAULT_OPEN_KEYS } from "./constants";

// ── Layout ────────────────────────────────────────────────────────────────

const { Sider } = Layout;
const MOBILE_SIDEBAR_QUERY = "(max-width: 768px)";
const NAV_PERMISSIONS: Record<string, string> = {
  inbox: "agents.use",
  channels: "agents.use",
  sessions: "system.admin",
  "cron-jobs": "agents.manage",
  heartbeat: "system.admin",
  workspace: "agents.use",
  skills: "tools.manage",
  "skill-pool": "tools.manage",
  market: "tools.manage",
  tools: "tools.manage",
  mcp: "mcp.manage",
  acp: "agents.use",
  "agent-config": "system.admin",
  "agent-stats": "audit.view",
  agents: "system.admin",
  users: "users.view",
  "approval-center": "approval.manage",
  "ops-governance": "governance.view",
  models: "models.manage",
  environments: "system.admin",
  security: "system.admin",
  "token-usage": "audit.view",
  "audit-logs": "audit.view",
  backups: "system.admin",
  "voice-transcription": "system.admin",
  debug: "system.admin",
  "plugin-manager": "system.admin",
};
const PERMISSION_IMPLICATIONS: Record<string, string[]> = {
  "users.view": ["users.manage"],
  "agents.use": ["agents.manage"],
  "tools.execute": ["tools.manage"],
};

function isMobileSidebarViewport() {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia(MOBILE_SIDEBAR_QUERY).matches
  );
}
const PERMISSION_GROUP_KEY = "permission-group";
const REPORT_GROUP_KEY = "report-group";
const SECURITY_GROUP_KEY = "security-group";

// ── Types ─────────────────────────────────────────────────────────────────

interface SidebarProps {
  selectedKey: string;
}

// ── Sidebar ───────────────────────────────────────────────────────────────

export default function Sidebar({ selectedKey }: SidebarProps) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const { isDark } = useTheme();
  const { pluginRoutes } = usePlugins();
  // When coding mode is on, the sidebar "Chat" entry should land on /coding
  // (FileTree + Editor + Chat panel) rather than the bare Chat page.
  const { codingMode } = useCodingMode();
  const chatPath = codingMode ? "/coding" : "/chat";
  const [authEnabled, setAuthEnabled] = useState(false);
  const [accountModalOpen, setAccountModalOpen] = useState(false);
  const [accountLoading, setAccountLoading] = useState(false);
  const [accountForm] = Form.useForm();
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(isMobileSidebarViewport);
  const [permissions, setPermissions] = useState<Set<string> | null>(null);
  const [settingsOpenKeys, setSettingsOpenKeys] = useState<string[]>([
    SECURITY_GROUP_KEY,
    PERMISSION_GROUP_KEY,
    REPORT_GROUP_KEY,
  ]);

  // ── Effects ──────────────────────────────────────────────────────────────

  useEffect(() => {
    authApi
      .getStatus()
      .then((res) => setAuthEnabled(res.enabled))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let mounted = true;
    usersApi
      .me()
      .then((res) => {
        if (mounted) {
          setPermissions(new Set(res.permissions));
        }
      })
      .catch(() => {
        if (mounted) {
          setPermissions(null);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return;
    }

    const mediaQuery = window.matchMedia(MOBILE_SIDEBAR_QUERY);
    const syncMobileSidebar = () => {
      setIsMobile(mediaQuery.matches);
      if (mediaQuery.matches) {
        setCollapsed(true);
      }
    };

    syncMobileSidebar();
    mediaQuery.addEventListener("change", syncMobileSidebar);

    return () => {
      mediaQuery.removeEventListener("change", syncMobileSidebar);
    };
  }, []);
  const canVisit = (key: string) => {
    const permission = NAV_PERMISSIONS[key];
    if (!permission || permissions === null) {
      return true;
    }
    return (
      permissions.has("system.admin") ||
      permissions.has(permission) ||
      (PERMISSION_IMPLICATIONS[permission] || []).some((impliedBy) =>
        permissions.has(impliedBy),
      )
    );
  };

  const filterMenuItems = (items: MenuProps["items"]): MenuProps["items"] =>
    (items || [])
      .map((item: any) => {
        if (!item) {
          return item;
        }
        const children = item.children
          ? filterMenuItems(item.children as MenuProps["items"])
          : undefined;
        if (children && children.length === 0) {
          return null;
        }
        if (!children && item.key && !canVisit(String(item.key))) {
          return null;
        }
        return {
          ...item,
          ...(children ? { children } : {}),
        };
      })
      .filter(Boolean) as MenuProps["items"];
  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleUpdateProfile = async (values: {
    currentPassword: string;
    newUsername?: string;
    newPassword?: string;
  }) => {
    const trimmedUsername = values.newUsername?.trim() || undefined;
    const trimmedPassword = values.newPassword?.trim() || undefined;

    if (values.newPassword && !trimmedPassword) {
      message.error(t("account.passwordEmpty"));
      return;
    }

    if (values.newUsername && !trimmedUsername) {
      message.error(t("account.usernameEmpty"));
      return;
    }

    if (!trimmedUsername && !trimmedPassword) {
      message.warning(t("account.nothingToUpdate"));
      return;
    }

    setAccountLoading(true);
    try {
      await authApi.updateProfile(
        values.currentPassword,
        trimmedUsername,
        trimmedPassword,
      );
      message.success(t("account.updateSuccess"));
      setAccountModalOpen(false);
      accountForm.resetFields();
      clearAuthToken();
      window.location.href = "/login";
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "";
      let msg = t("account.updateFailed");
      if (raw.includes("password is incorrect")) {
        msg = t("account.wrongPassword");
      } else if (raw.includes("Nothing to update")) {
        msg = t("account.nothingToUpdate");
      } else if (raw.includes("cannot be empty")) {
        msg = t("account.nothingToUpdate");
      } else if (raw) {
        msg = raw;
      }
      message.error(msg);
    } finally {
      setAccountLoading(false);
    }
  };

  // ── Collapsed nav items (all leaf pages) ──────────────────────────────

  const collapsedNavItems = [
    {
      key: "chat",
      icon: <SparkChatTabFill size={18} />,
      path: chatPath,
      label: t("nav.chat"),
    },
    {
      key: "channels",
      icon: <SparkWifiLine size={18} />,
      path: "/channels",
      label: t("nav.channels"),
    },
    {
      key: "sessions",
      icon: <SparkUserGroupLine size={18} />,
      path: "/sessions",
      label: t("nav.sessions"),
    },
    {
      key: "cron-jobs",
      icon: <SparkDateLine size={18} />,
      path: "/cron-jobs",
      label: t("nav.cronJobs"),
    },
    {
      key: "heartbeat",
      icon: <SparkVoiceChat01Line size={18} />,
      path: "/heartbeat",
      label: t("nav.heartbeat"),
    },
    {
      key: "workspace",
      icon: <SparkLocalFileLine size={18} />,
      path: "/workspace",
      label: t("nav.workspace"),
    },
    {
      key: "skills",
      icon: <SparkMagicWandLine size={18} />,
      path: "/skills",
      label: t("nav.skills"),
    },
    {
      key: "skill-pool",
      icon: <SparkOtherLine size={18} />,
      path: "/skill-pool",
      label: t("nav.skillPool", "Skill Pool"),
    },
    {
      key: "tools",
      icon: <SparkToolLine size={18} />,
      path: "/tools",
      label: t("nav.tools"),
    },
    {
      key: "ops-governance",
      icon: <SparkScanLine size={18} />,
      path: "/ops-governance",
      label: t("nav.opsGovernance", "智能体授权"),
    },
    {
      key: "approval-center",
      icon: <CheckSquare size={18} />,
      path: "/approval-center",
      label: t("nav.approvalCenter", "审批中心"),
    },
    {
      key: "mcp",
      icon: <SparkMcpMcpLine size={18} />,
      path: "/mcp",
      label: t("nav.mcp"),
    },
    {
      key: "acp",
      icon: <SparkScanLine size={18} />,
      path: "/acp",
      label: t("nav.acp"),
    },
    {
      key: "agent-config",
      icon: <SparkModifyLine size={18} />,
      path: "/agent-config",
      label: t("nav.agentConfig"),
    },
    {
      key: "agent-stats",
      icon: <SparkBarChartLine size={18} />,
      path: "/agent-stats",
      label: t("nav.agentStats"),
    },
    {
      key: "agents",
      icon: <SparkAgentLine size={18} />,
      path: "/agents",
      label: t("nav.agents"),
    },
    {
      key: "models",
      icon: <SparkModePlazaLine size={18} />,
      path: "/models",
      label: t("nav.models"),
    },
    {
      key: "environments",
      icon: <SparkInternetLine size={18} />,
      path: "/environments",
      label: t("nav.environments"),
    },
    {
      key: "security",
      icon: <SparkBrowseLine size={18} />,
      path: "/security",
      label: t("nav.securityManagement", "安全管理"),
    },
    {
      key: "audit-logs",
      icon: <SparkDataLine size={18} />,
      path: "/audit-logs",
      label: t("nav.auditLogs", "日志审计"),
    },
    {
      key: "token-usage",
      icon: <SparkDataLine size={18} />,
      path: "/token-usage",
      label: t("nav.tokenUsage"),
    },
    {
      key: "backups",
      icon: <SparkSaveLine size={18} />,
      path: "/backups",
      label: t("nav.backups"),
    },
    {
      key: "voice-transcription",
      icon: <SparkMicLine size={18} />,
      path: "/voice-transcription",
      label: t("nav.voiceTranscription"),
    },
    {
      key: "debug",
      icon: <SparkDebugLine size={18} />,
      path: "/debug",
      label: t("nav.debug", "Debug"),
    },
    {
      key: "plugin-manager",
      icon: <Package size={18} />,
      path: "/plugin-manager",
      label: t("nav.pluginManager", "Plugin Manager"),
    },
    // Append plugin nav items dynamically
    ...pluginRoutes.map((route) => ({
      key: route.path.replace(/^\//, ""),
      icon: <span style={{ fontSize: 18 }}>{route.icon}</span>,
      path: route.path,
      label: route.label,
    })),
  ].filter((item) => canVisit(item.key));

  // ── Menu items — agent-scoped (Chat + Control + Workspace) ──────────────

  const agentMenuItems: MenuProps["items"] = [
    {
      key: "agent-group",
      label: collapsed ? null : t("nav.agent"),
      children: [
        {
          key: "chat",
          label: collapsed ? null : t("nav.chat"),
          icon: <SparkChatTabFill size={16} />,
        },
        {
          key: "workspace",
          label: collapsed ? null : t("nav.workspace"),
          icon: <SparkLocalFileLine size={16} />,
        },
        {
          key: "channels",
          label: collapsed ? null : t("nav.channels"),
          icon: <SparkWifiLine size={16} />,
        },
        {
          key: "cron-jobs",
          label: collapsed ? null : t("nav.cronJobs"),
          icon: <SparkDateLine size={16} />,
        },
        {
          key: "skills",
          label: collapsed ? null : t("nav.skills"),
          icon: <SparkMagicWandLine size={16} />,
        },
        {
          key: "skill-pool",
          label: collapsed ? null : t("nav.skillPool", "Skill Pool"),
          icon: <SparkOtherLine size={16} />,
        },
        {
          key: "market",
          label: collapsed ? null : t("nav.market", "Skill Market"),
          icon: <SparkCardLine size={16} />,
        },
        {
          key: "tools",
          label: collapsed ? null : t("nav.tools"),
          icon: <SparkToolLine size={16} />,
        },
        {
          key: "mcp",
          label: collapsed ? null : t("nav.mcp"),
          icon: <SparkMcpMcpLine size={16} />,
        },
        {
          key: "acp",
          label: collapsed ? null : t("nav.acp"),
          icon: <SparkScanLine size={16} />,
        },
        {
          key: "plugin-manager",
          label: collapsed ? null : t("nav.pluginManager", "Plugin Manager"),
          icon: <Package size={16} />,
        },
        {
          key: "agent-config",
          label: collapsed ? null : t("nav.agentConfig"),
          icon: <SparkModifyLine size={16} />,
        },
      ],
    },
  ];

  // ── Menu items — global settings ──────────────────────────────────────

  const settingsMenuItems: MenuProps["items"] = [
    {
      key: SECURITY_GROUP_KEY,
      label: collapsed ? null : t("nav.securityManagement", "安全管理"),
      children: [
        {
          key: "security",
          label: collapsed ? null : t("nav.security", "安全设置"),
          icon: <SparkBrowseLine size={16} />,
        },
        {
          key: "approval-center",
          label: collapsed ? null : t("nav.approvalCenter", "审批中心"),
          icon: <CheckSquare size={16} />,
        },
        {
          key: "audit-logs",
          label: collapsed ? null : t("nav.auditLogs", "日志审计"),
          icon: <SparkDataLine size={16} />,
        },
      ],
    },
    {
      key: PERMISSION_GROUP_KEY,
      label: collapsed ? null : t("nav.permissionManagement", "权限管理"),
      children: [
        {
          key: "users",
          label: collapsed ? null : t("nav.users", "用户权限"),
          icon: <SparkSearchUserLine size={16} />,
        },
        {
          key: "ops-governance",
          label: collapsed ? null : t("nav.opsGovernance", "智能体授权"),
          icon: <SparkScanLine size={16} />,
        },
      ],
    },
    {
      key: REPORT_GROUP_KEY,
      label: collapsed ? null : t("nav.intelligentReports", "智能报表"),
      children: [
        {
          key: "agent-stats",
          label: collapsed ? null : t("nav.agentStats"),
          icon: <SparkBarChartLine size={16} />,
        },
        {
          key: "token-usage",
          label: collapsed ? null : t("nav.tokenUsage"),
          icon: <SparkDataLine size={16} />,
        },
      ],
    },
    {
      key: "control-group",
      label: collapsed ? null : t("nav.control"),
      children: [
        {
          key: "sessions",
          label: collapsed ? null : t("nav.sessions"),
          icon: <SparkUserGroupLine size={16} />,
        },
        {
          key: "heartbeat",
          label: collapsed ? null : t("nav.heartbeat"),
          icon: <SparkVoiceChat01Line size={16} />,
        },
      ],
    },
    {
      key: "settings-group",
      label: collapsed ? null : t("nav.settings"),
      children: [
        ...(authEnabled
          ? [
              {
                key: "account-settings",
                label: collapsed ? null : t("account.title"),
                icon: <SparkSearchUserLine size={16} />,
              },
            ]
          : []),
        {
          key: "agents",
          label: collapsed ? null : t("nav.agents"),
          icon: <SparkAgentLine size={16} />,
        },
        {
          key: "models",
          label: collapsed ? null : t("nav.models"),
          icon: <SparkModePlazaLine size={16} />,
        },
        {
          key: "environments",
          label: collapsed ? null : t("nav.environments"),
          icon: <SparkInternetLine size={16} />,
        },
        {
          key: "backups",
          label: collapsed ? null : t("nav.backups"),
          icon: <SparkSaveLine size={16} />,
        },
        {
          key: "voice-transcription",
          label: collapsed ? null : t("nav.voiceTranscription"),
          icon: <SparkMicLine size={16} />,
        },
        {
          key: "debug",
          label: collapsed ? null : t("nav.debug", "Debug"),
          icon: <SparkDebugLine size={16} />,
        },
      ],
    },
  ];

  // Append plugin menu items as a group (only when there are plugins)
  if (pluginRoutes.length > 0) {
    settingsMenuItems.push({
      key: "plugins-group",
      label: collapsed ? null : t("nav.plugins"),
      children: pluginRoutes.map((route) => ({
        key: route.path.replace(/^\//, ""),
        label: collapsed ? null : route.label,
        icon: <span style={{ fontSize: 16 }}>{route.icon}</span>,
      })),
    } as any);
  }
  const visibleAgentMenuItems = filterMenuItems(agentMenuItems);
  const visibleSettingsMenuItems = filterMenuItems(settingsMenuItems);

  // ── Render ────────────────────────────────────────────────────────────────

  const siderWidth = collapsed ? (isMobile ? 56 : 72) : 240;

  return (
    <Sider
      width={siderWidth}
      className={`${styles.sider}${
        collapsed ? ` ${styles.siderCollapsed}` : ""
      }${isDark ? ` ${styles.siderDark}` : ""}`}
    >
      {collapsed ? (
        <nav className={styles.collapsedNav}>
          {collapsedNavItems.map((item) => {
            const isActive = selectedKey === item.key;
            return (
              <Tooltip
                key={item.key}
                title={item.label}
                placement="right"
                overlayInnerStyle={{
                  background: "rgba(0,0,0,0.75)",
                  color: "#fff",
                }}
              >
                <button
                  className={`${styles.collapsedNavItem} ${
                    isActive ? styles.collapsedNavItemActive : ""
                  }`}
                  onClick={() => navigate(item.path)}
                >
                  {item.icon}
                </button>
              </Tooltip>
            );
          })}
        </nav>
      ) : (
        <>
          {/* Agent-scoped section: selector + Chat + Control + Workspace */}
          <div className={styles.agentScopedSection}>
            <div className={styles.agentSelectorContainer}>
              <AgentSelector collapsed={collapsed} />
            </div>
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
              openKeys={DEFAULT_OPEN_KEYS}
              onClick={({ key }) => {
                const k = String(key);
                const path = k === "chat" ? chatPath : KEY_TO_PATH[k];
                if (path) navigate(path);
              }}
              items={visibleAgentMenuItems}
              theme={isDark ? "dark" : "light"}
              className={styles.sideMenu}
            />
          </div>

          {/* Global settings section */}
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            openKeys={settingsOpenKeys}
            onOpenChange={(keys) => setSettingsOpenKeys(keys as string[])}
            onClick={({ key }) => {
              if (String(key) === "account-settings") {
                accountForm.resetFields();
                setAccountModalOpen(true);
                return;
              }
              const path = KEY_TO_PATH[String(key)] ?? `/${String(key)}`;
              navigate(path);
            }}
            items={visibleSettingsMenuItems}
            theme={isDark ? "dark" : "light"}
            className={`${styles.sideMenu} ${styles.settingsMenu}`}
          />
        </>
      )}

      <div className={styles.collapseToggleContainer}>
        <Button
          type="text"
          icon={
            collapsed ? (
              <SparkMenuExpandLine size={20} />
            ) : (
              <SparkMenuFoldLine size={20} />
            )
          }
          onClick={() => setCollapsed(!collapsed)}
          className={styles.collapseToggle}
        />
      </div>

      <Modal
        open={accountModalOpen}
        onCancel={() => setAccountModalOpen(false)}
        title={t("account.title")}
        footer={null}
        destroyOnHidden
        centered
      >
        <Form
          form={accountForm}
          layout="vertical"
          onFinish={handleUpdateProfile}
        >
          <Form.Item
            name="currentPassword"
            label={t("account.currentPassword")}
            rules={[
              { required: true, message: t("account.currentPasswordRequired") },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item name="newUsername" label={t("account.newUsername")}>
            <Input placeholder={t("account.newUsernamePlaceholder")} />
          </Form.Item>
          <Form.Item name="newPassword" label={t("account.newPassword")}>
            <Input.Password placeholder={t("account.newPasswordPlaceholder")} />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label={t("account.confirmPassword")}
            dependencies={["newPassword"]}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value && !getFieldValue("newPassword")) {
                    return Promise.resolve();
                  }
                  if (value === getFieldValue("newPassword")) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error(t("account.passwordMismatch")),
                  );
                },
              }),
            ]}
          >
            <Input.Password
              placeholder={t("account.confirmPasswordPlaceholder")}
            />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={accountLoading}
              block
            >
              {t("account.save")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Sider>
  );
}
