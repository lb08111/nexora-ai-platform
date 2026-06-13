import { useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DownloadOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import { PageHeader } from "../../../components/PageHeader";
import { useAppMessage } from "../../../hooks/useAppMessage";
import { auditApi, type AuditEvent, type AuditQuery } from "../../api/audit";
import { buildAuthHeaders } from "../../../api/authHeaders";
import dayjs from "dayjs";
import styles from "../nexoraPages.module.less";

const { RangePicker } = DatePicker;

/* ---- 操作类型中文映射 ---- */
const actionLabels: Record<string, string> = {
  "auth.login": "登录",
  "auth.logout": "退出登录",
  "auth.register": "注册",
  "auth.profile.update": "修改账号",
  "auth.revoke_all_tokens": "注销全部会话",
  "page.view": "访问页面",
  "api.mutate": "平台操作",
  "api.denied": "权限拦截",
  "chat.create": "创建会话",
  "chat.update": "更新会话",
  "chat.delete": "删除会话",
  "chat.batch_delete": "批量删除会话",
  "chat.message.send": "发送消息",
  "chat.reconnect": "重连会话",
  "chat.stop": "停止会话",
  "chat.file.upload": "上传附件",
  "agent.tool.execute": "工具调用",
  "mcp.create.approved": "MCP 新增审批通过",
  "mcp.create.rejected": "MCP 新增审批驳回",
  "skill.create.approved": "技能新增审批通过",
  "skill.create.rejected": "技能新增审批驳回",
  "plugin.install.approved": "插件安装审批通过",
  "plugin.install.rejected": "插件安装审批驳回",
  "tool.create.approved": "工具新增审批通过",
  "tool.create.rejected": "工具新增审批驳回",
};

const statusLabels: Record<string, string> = {
  success: "成功",
  failure: "失败",
  denied: "拒绝",
  started: "执行中",
};

const statusColors: Record<string, string> = {
  success: "green",
  failure: "red",
  denied: "orange",
  started: "blue",
};

/* ---- 时间格式化 ---- */
function formatTime(timestamp: number) {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
}

/* ---- 按 action 类型结构化展示 detail ---- */
function DetailContent({ event }: { event: AuditEvent }) {
  const { action, detail, resource_id, resource_type } = event;
  const d = detail || {};

  const baseItems = [
    { label: "事件 ID", value: event.id },
    { label: "操作时间", value: formatTime(event.timestamp) },
    { label: "操作用户", value: event.actor },
    { label: "操作类型", value: actionLabels[action] || action },
    { label: "结果", value: statusLabels[event.status] || event.status },
    { label: "资源类型", value: resource_type || "-" },
    { label: "资源 ID", value: resource_id || "-" },
    { label: "来源 IP", value: event.ip || "-" },
  ];

  if (event.user_agent) {
    baseItems.push({ label: "浏览器", value: event.user_agent });
  }

  let contextItems: { label: string; value: string }[] = [];

  if (action === "chat.message.send") {
    contextItems = [
      { label: "智能体", value: String(d.agent_id || "-") },
      { label: "会话 ID", value: String(d.session_id || "-") },
      { label: "渠道", value: String(d.channel || "-") },
      { label: "目标用户", value: String(d.target_user || "-") },
      { label: "消息长度", value: String(d.message_length ?? "-") },
      { label: "消息内容", value: String(d.message_preview || "-") },
    ];
  } else if (action === "agent.tool.execute") {
    contextItems = [
      { label: "智能体", value: String(d.agent_id || "-") },
      { label: "调用 ID", value: String(d.tool_call_id || "-") },
      { label: "会话 ID", value: String(d.session_id || "-") },
      { label: "渠道", value: String(d.channel || "-") },
      { label: "触发原因", value: String(d.reason || "-") },
    ];
    if (d.input_preview) {
      contextItems.push({ label: "输入参数", value: String(d.input_preview) });
    }
    if (d.result_preview) {
      contextItems.push({ label: "执行结果", value: String(d.result_preview) });
    }
    if (d.error) {
      contextItems.push({ label: "错误信息", value: String(d.error) });
    }
  } else if (action === "api.mutate" || action === "api.denied") {
    contextItems = [
      { label: "HTTP 方法", value: String(d.method || "-") },
      { label: "请求路径", value: resource_id || "-" },
      { label: "所需权限", value: String(d.permission || "-") },
    ];
    if (d.status_code) {
      contextItems.push({ label: "状态码", value: String(d.status_code) });
    }
    if (d.query) {
      contextItems.push({ label: "查询参数", value: String(d.query) });
    }
  } else if (action === "auth.login") {
    contextItems = [
      {
        label: "角色",
        value: Array.isArray(d.roles)
          ? d.roles.join(", ")
          : String(d.roles || "-"),
      },
    ];
    if (d.reason) {
      contextItems.push({ label: "失败原因", value: String(d.reason) });
    }
  } else if (action === "auth.profile.update") {
    contextItems = [];
    if (d.username_changed !== undefined) {
      contextItems.push({
        label: "修改用户名",
        value: d.username_changed ? "是" : "否",
      });
    }
    if (d.password_changed !== undefined) {
      contextItems.push({
        label: "修改密码",
        value: d.password_changed ? "是" : "否",
      });
    }
    if (d.reason) {
      contextItems.push({ label: "失败原因", value: String(d.reason) });
    }
  } else if (action === "page.view") {
    contextItems = [
      { label: "页面标题", value: String(d.title || "-") },
      { label: "页面路径", value: resource_id || "-" },
    ];
  } else if (action === "chat.file.upload") {
    contextItems = [
      { label: "智能体", value: String(d.agent_id || "-") },
      {
        label: "文件大小",
        value: d.size ? `${Number(d.size).toLocaleString()} 字节` : "-",
      },
      { label: "存储名称", value: String(d.stored_name || "-") },
    ];
  } else if (action.includes(".approved") || action.includes(".rejected")) {
    contextItems = [
      { label: "审批请求 ID", value: String(d.approval_request_id || "-") },
    ];
    if (d.reason) {
      contextItems.push({ label: "驳回原因", value: String(d.reason) });
    }
    if (d.result) {
      contextItems.push({
        label: "审批结果",
        value:
          typeof d.result === "object"
            ? JSON.stringify(d.result, null, 2)
            : String(d.result),
      });
    }
  } else {
    const keys = Object.keys(d);
    if (keys.length > 0) {
      contextItems = keys.map((k) => ({
        label: k,
        value:
          typeof d[k] === "object"
            ? JSON.stringify(d[k], null, 2)
            : String(d[k] ?? "-"),
      }));
    }
  }

  return (
    <div>
      <Descriptions
        title="基本信息"
        column={2}
        bordered
        size="small"
        style={{ marginBottom: 16 }}
      >
        {baseItems.map((item) => (
          <Descriptions.Item
            key={item.label}
            label={item.label}
            span={item.label === "浏览器" ? 2 : 1}
          >
            <Typography.Text copyable={item.label === "事件 ID"}>
              {item.value}
            </Typography.Text>
          </Descriptions.Item>
        ))}
      </Descriptions>

      {contextItems.length > 0 && (
        <Descriptions title="操作详情" column={1} bordered size="small">
          {contextItems.map((item) => (
            <Descriptions.Item key={item.label} label={item.label}>
              {item.value.length > 200 ? (
                <Typography.Paragraph className={styles.drawerTextBlock}>
                  {item.value}
                </Typography.Paragraph>
              ) : (
                <Typography.Text>{item.value}</Typography.Text>
              )}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </div>
  );
}

/* ---- 主页面 ---- */
export default function AuditLogsPage() {
  const { message } = useAppMessage();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<
    AuditQuery & { timeRange?: [dayjs.Dayjs, dayjs.Dayjs] }
  >();
  const [drawerEvent, setDrawerEvent] = useState<AuditEvent | null>(null);

  const loadEvents = async (
    values: AuditQuery & { timeRange?: [dayjs.Dayjs, dayjs.Dayjs] } = {},
  ) => {
    setLoading(true);
    try {
      const params: AuditQuery = {
        limit: values.limit || 200,
        actor: values.actor,
        action: values.action,
        status: values.status,
      };
      if (values.timeRange && values.timeRange[0] && values.timeRange[1]) {
        params.start_time = values.timeRange[0].startOf("day").unix();
        params.end_time = values.timeRange[1].endOf("day").unix();
      }
      const data = await auditApi.listEvents(params);
      setEvents(data);
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : "加载审计日志失败",
      );
    } finally {
      setLoading(false);
    }
  };

  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const values = form.getFieldsValue();
      const params: AuditQuery = {
        limit: 5000,
        actor: values.actor,
        action: values.action,
        status: values.status,
      };
      if (values.timeRange && values.timeRange[0] && values.timeRange[1]) {
        params.start_time = values.timeRange[0].startOf("day").unix();
        params.end_time = values.timeRange[1].endOf("day").unix();
      }
      const url = auditApi.exportEventsUrl(params);
      const resp = await fetch(url, { headers: buildAuthHeaders() });
      if (!resp.ok) throw new Error(`导出失败: ${resp.status}`);
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] || "audit_logs.csv";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
      message.success(`已导出 ${events.length > 0 ? "审计日志" : "数据"}`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    void loadEvents({ limit: 200 });
  }, []);

  /* ---- detail 摘要（表格内简短展示） ---- */
  const detailSummary = (event: AuditEvent): string => {
    const { action, detail: d } = event;
    if (!d || Object.keys(d).length === 0) return "-";

    if (action === "chat.message.send") {
      return String(d.message_preview || "-");
    }
    if (action === "agent.tool.execute") {
      const parts: string[] = [];
      if (d.agent_id) parts.push(`智能体: ${d.agent_id}`);
      if (d.reason) parts.push(`原因: ${d.reason}`);
      if (d.error) parts.push(`错误: ${d.error}`);
      return parts.join(" | ") || "-";
    }
    if (action === "api.mutate") {
      return `${d.method || ""} ${event.resource_id || ""}`.trim() || "-";
    }
    if (action === "api.denied") {
      return `${d.method || ""} ${event.resource_id || ""} (需要 ${
        d.permission || "?"
      } 权限)`.trim();
    }
    if (action === "page.view") {
      return String(d.title || "-");
    }
    if (action === "auth.login") {
      if (d.reason) return `失败: ${d.reason}`;
      if (Array.isArray(d.roles)) return `角色: ${d.roles.join(", ")}`;
    }
    if (action === "chat.file.upload") {
      return `文件: ${d.stored_name || "-"} (${
        d.size ? Number(d.size).toLocaleString() + " B" : "-"
      })`;
    }
    if (action.includes(".approved")) return "审批通过";
    if (action.includes(".rejected"))
      return `审批驳回${d.reason ? ": " + d.reason : ""}`;

    const keys = Object.keys(d).slice(0, 3);
    return keys
      .map(
        (k) =>
          `${k}: ${typeof d[k] === "object" ? JSON.stringify(d[k]) : d[k]}`,
      )
      .join(" | ");
  };

  const columns: ColumnsType<AuditEvent> = [
    {
      title: "时间",
      dataIndex: "timestamp",
      key: "timestamp",
      width: 180,
      render: (value: number) => formatTime(value),
    },
    {
      title: "用户",
      dataIndex: "actor",
      key: "actor",
      width: 120,
      render: (value: string) => (
        <Typography.Text strong>{value}</Typography.Text>
      ),
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 150,
      render: (value: string) => actionLabels[value] || value,
    },
    {
      title: "结果",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (value: string) => (
        <Tag color={statusColors[value] || "default"}>
          {statusLabels[value] || value}
        </Tag>
      ),
    },
    {
      title: "对象",
      key: "resource",
      width: 180,
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text ellipsis>
            {record.resource_id || "-"}
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {record.resource_type || "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "摘要",
      key: "summary",
      ellipsis: true,
      render: (_, record) => (
        <Typography.Text ellipsis style={{ maxWidth: 300 }}>
          {detailSummary(record)}
        </Typography.Text>
      ),
    },
    {
      title: "IP",
      dataIndex: "ip",
      key: "ip",
      width: 120,
      render: (value: string) => value || "-",
    },
    {
      title: "",
      key: "actions",
      width: 50,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<InfoCircleOutlined />}
          onClick={() => setDrawerEvent(record)}
        />
      ),
    },
  ];

  return (
    <div className={styles.nexoraPage}>
      <PageHeader
        className={styles.pageHeader}
        parent="安全管理"
        current="日志审计"
        subRow={
          <Typography.Text type="secondary">
            记录用户登录、聊天消息、工具调用、平台操作和权限拦截，便于安全审计与问题追溯。
            {events.length > 0 && ` 当前显示 ${events.length} 条记录。`}
          </Typography.Text>
        }
        extra={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exporting}
            >
              导出 CSV
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadEvents(form.getFieldsValue())}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      />

      <div className={styles.content}>
        <div className={styles.stack}>
          <Card className={styles.panel}>
            <Form
              form={form}
              className={styles.filterForm}
              initialValues={{ limit: 200 }}
              onFinish={loadEvents}
            >
              <Form.Item name="actor" label="用户">
                <Input allowClear placeholder="用户名" style={{ width: 120 }} />
              </Form.Item>
              <Form.Item name="action" label="操作">
                <Select
                  allowClear
                  style={{ width: 180 }}
                  placeholder="全部"
                  options={Object.entries(actionLabels).map(
                    ([value, label]) => ({
                      value,
                      label,
                    }),
                  )}
                />
              </Form.Item>
              <Form.Item name="status" label="结果">
                <Select
                  allowClear
                  style={{ width: 100 }}
                  placeholder="全部"
                  options={[
                    { value: "success", label: "成功" },
                    { value: "failure", label: "失败" },
                    { value: "denied", label: "拒绝" },
                    { value: "started", label: "执行中" },
                  ]}
                />
              </Form.Item>
              <Form.Item name="timeRange" label="时间范围">
                <RangePicker />
              </Form.Item>
              <Form.Item name="limit" label="数量">
                <Select
                  style={{ width: 80 }}
                  options={[
                    { value: 100, label: "100" },
                    { value: 200, label: "200" },
                    { value: 500, label: "500" },
                    { value: 1000, label: "1000" },
                  ]}
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  查询
                </Button>
              </Form.Item>
            </Form>
          </Card>

          <Card className={styles.tablePanel}>
            <Table
              rowKey="id"
              columns={columns}
              dataSource={events}
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
              }}
              size="middle"
            />
          </Card>
        </div>
      </div>

      <Drawer
        title="审计事件详情"
        placement="right"
        width={640}
        open={!!drawerEvent}
        onClose={() => setDrawerEvent(null)}
        destroyOnClose
      >
        {drawerEvent && <DetailContent event={drawerEvent} />}
      </Drawer>
    </div>
  );
}
