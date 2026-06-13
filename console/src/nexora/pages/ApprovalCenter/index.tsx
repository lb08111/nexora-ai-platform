import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { PageHeader } from "../../../components/PageHeader";
import { useAppMessage } from "../../../hooks/useAppMessage";
import { type PlatformRole, usersApi } from "../../api/users";
import {
  type ApprovalAction,
  type ApprovalRequest,
  type ApprovalRequestStatus,
  governanceApi,
} from "../../api/governance";
import {
  type CapabilityApprovalConfig,
  multiTenantApi,
} from "../../api/multiTenant";
import styles from "../nexoraPages.module.less";

const actionLabels: Record<string, string> = {
  "mcp.create": "新增 MCP",
  "mcp.delete": "删除 MCP",
  "skill.create": "新增 Skill",
  "skill.delete": "删除 Skill",
  "plugin.install": "安装插件",
  "plugin.uninstall": "卸载插件",
  "tool.create": "新增工具",
  "tool.delete": "删除工具",
  "acp.create": "新增 ACP",
  "acp.delete": "删除 ACP",
};

const statusLabels: Record<ApprovalRequestStatus, string> = {
  pending: "待审批",
  approved: "已通过",
  rejected: "已驳回",
  applied: "已生效",
  failed: "执行失败",
};

const statusColors: Record<ApprovalRequestStatus, string> = {
  pending: "orange",
  approved: "blue",
  rejected: "red",
  applied: "green",
  failed: "red",
};

const capTypeLabels: Record<string, string> = {
  skill: "Skill",
  mcp: "MCP",
  tool: "工具",
  acp: "ACP",
  plugin: "插件",
};

function formatTime(timestamp: number) {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
}

function compactJson(value: Record<string, unknown>) {
  if (!value || !Object.keys(value).length) return "-";
  return JSON.stringify(value);
}

export default function ApprovalCenterPage() {
  const { message } = useAppMessage();
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [approvalConfigs, setApprovalConfigs] = useState<
    CapabilityApprovalConfig[]
  >([]);
  const [roles, setRoles] = useState<PlatformRole[]>([]);
  const [loading, setLoading] = useState(false);
  const [approvalSaving, setApprovalSaving] = useState<string | null>(null);
  const [filterForm] = Form.useForm<{
    status?: ApprovalRequestStatus;
    action?: ApprovalAction;
  }>();

  const pendingCount = useMemo(
    () => requests.filter((item) => item.status === "pending").length,
    [requests],
  );

  const loadAll = async () => {
    setLoading(true);
    try {
      const filters = filterForm.getFieldsValue();
      const [requestList, configList, roleList] = await Promise.all([
        governanceApi.listApprovalRequests(filters),
        multiTenantApi.listApprovalConfigs().catch(() => []),
        usersApi.listRoles(),
      ]);
      setRequests(requestList);
      setApprovalConfigs(configList);
      setRoles(roleList);
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : "加载审批中心失败",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  const handleApprove = (record: ApprovalRequest) => {
    Modal.confirm({
      title: "通过申请",
      content: `确认通过「${record.summary || record.resource_name}」？`,
      okText: "通过",
      cancelText: "取消",
      onOk: async () => {
        try {
          await governanceApi.approveApprovalRequest(record.id);
          message.success("审批已通过");
          await loadAll();
        } catch (error) {
          message.error(error instanceof Error ? error.message : "审批失败");
        }
      },
    });
  };

  const handleReject = (record: ApprovalRequest) => {
    let reason = "";
    Modal.confirm({
      title: "驳回申请",
      content: (
        <Input.TextArea
          rows={3}
          placeholder="填写驳回原因"
          onChange={(event) => {
            reason = event.target.value;
          }}
        />
      ),
      okText: "驳回",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await governanceApi.rejectApprovalRequest(record.id, reason);
          message.success("申请已驳回");
          await loadAll();
        } catch (error) {
          message.error(error instanceof Error ? error.message : "驳回失败");
        }
      },
    });
  };

  // ── Capability approval config handlers ──────────────────────────────────

  const handlePolicyChange = async (
    capType: string,
    field: "add_policy" | "remove_policy",
    value: string,
  ) => {
    setApprovalSaving(capType);
    try {
      const updated = await multiTenantApi.updateApprovalConfig(capType, {
        [field]: value,
      });
      setApprovalConfigs((prev) =>
        prev.map((c) => (c.capability_type === capType ? updated : c)),
      );
      message.success("配置已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setApprovalSaving(null);
    }
  };

  const handleApproverRolesChange = async (
    capType: string,
    approverRoles: string[],
  ) => {
    setApprovalSaving(capType);
    try {
      const updated = await multiTenantApi.updateApprovalConfig(capType, {
        approver_roles: approverRoles,
      });
      setApprovalConfigs((prev) =>
        prev.map((c) => (c.capability_type === capType ? updated : c)),
      );
      message.success("配置已更新");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setApprovalSaving(null);
    }
  };

  // ── Columns ──────────────────────────────────────────────────────────────

  const requestColumns: ColumnsType<ApprovalRequest> = [
    {
      title: "申请内容",
      key: "summary",
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong>
            {record.summary || record.resource_name || record.resource_id}
          </Typography.Text>
          <Typography.Text type="secondary">
            {record.resource_type || "-"} / {record.resource_id || "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "action",
      key: "action",
      width: 120,
      render: (value: string) => <Tag>{actionLabels[value] || value}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (value: ApprovalRequestStatus) => (
        <Tag color={statusColors[value] || "default"}>
          {statusLabels[value] || value}
        </Tag>
      ),
    },
    {
      title: "申请人",
      dataIndex: "requester",
      key: "requester",
      width: 130,
      render: (value: string) => value || "-",
    },
    {
      title: "审批人",
      dataIndex: "approver",
      key: "approver",
      width: 130,
      render: (value: string) => value || "-",
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (value: number) => formatTime(value),
    },
    {
      title: "结果",
      dataIndex: "result",
      key: "result",
      ellipsis: true,
      render: (value: Record<string, unknown>, record) => (
        <Typography.Text
          type={record.status === "failed" ? "danger" : undefined}
        >
          {record.reason || compactJson(value)}
        </Typography.Text>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 160,
      render: (_, record) =>
        record.status === "pending" ? (
          <Space>
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => handleApprove(record)}
            >
              通过
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => handleReject(record)}
            >
              驳回
            </Button>
          </Space>
        ) : (
          <Typography.Text type="secondary">已处理</Typography.Text>
        ),
    },
  ];

  const configColumns: ColumnsType<CapabilityApprovalConfig> = [
    {
      title: "能力类型",
      dataIndex: "capability_type",
      key: "capability_type",
      width: 120,
      render: (value: string) => (
        <Typography.Text strong>
          {capTypeLabels[value] || value}
        </Typography.Text>
      ),
    },
    {
      title: "新增策略",
      dataIndex: "add_policy",
      key: "add_policy",
      width: 150,
      render: (value: string, record) => (
        <Select
          value={value || "approval"}
          style={{ width: 130 }}
          loading={approvalSaving === record.capability_type}
          onChange={(v) =>
            handlePolicyChange(record.capability_type, "add_policy", v)
          }
          options={[
            { value: "none", label: "无需审批" },
            { value: "approval", label: "需要审批" },
          ]}
        />
      ),
    },
    {
      title: "删除策略",
      dataIndex: "remove_policy",
      key: "remove_policy",
      width: 160,
      render: (value: string, record) => (
        <Select
          value={value || "log"}
          style={{ width: 140 }}
          loading={approvalSaving === record.capability_type}
          onChange={(v) =>
            handlePolicyChange(record.capability_type, "remove_policy", v)
          }
          options={[
            { value: "none", label: "无需审批" },
            { value: "log", label: "自动审批" },
            { value: "approval", label: "需要审批" },
          ]}
        />
      ),
    },
    {
      title: "审批角色",
      dataIndex: "approver_roles",
      key: "approver_roles",
      render: (value: string[], record) => (
        <Select
          mode="multiple"
          value={value || []}
          style={{ minWidth: 160 }}
          loading={approvalSaving === record.capability_type}
          options={roles.map((role) => ({
            value: role.id,
            label: role.name,
          }))}
          onChange={(selected) =>
            handleApproverRolesChange(record.capability_type, selected)
          }
        />
      ),
    },
  ];

  const enabledConfigCount = approvalConfigs.filter(
    (c) => c.add_policy !== "none" || c.remove_policy !== "none",
  ).length;

  return (
    <div className={styles.nexoraPage}>
      <PageHeader
        className={styles.pageHeader}
        parent="安全管理"
        current="审批中心"
        subRow={
          <Typography.Text type="secondary">
            处理能力变更的审批申请；按能力类型配置新增/删除的审批开关。
          </Typography.Text>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
            刷新
          </Button>
        }
      />

      <div className={styles.content}>
        <div className={styles.stack}>
          <div className={styles.metricGrid}>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                待处理申请
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {pendingCount}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                申请总数
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {requests.length}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                审批规则启用
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {enabledConfigCount}/{approvalConfigs.length}
              </Typography.Title>
            </Card>
          </div>

          <Tabs
            className={styles.tabs}
            items={[
              {
                key: "requests",
                label: "审批申请",
                children: (
                  <>
                    <Card className={styles.panel} style={{ marginBottom: 16 }}>
                      <Form
                        form={filterForm}
                        className={styles.filterForm}
                        onFinish={loadAll}
                      >
                        <Form.Item name="status" label="状态">
                          <Select
                            allowClear
                            style={{ width: 140 }}
                            options={Object.entries(statusLabels).map(
                              ([value, label]) => ({ value, label }),
                            )}
                          />
                        </Form.Item>
                        <Form.Item name="action" label="类型">
                          <Select
                            allowClear
                            style={{ width: 150 }}
                            options={Object.entries(actionLabels).map(
                              ([value, label]) => ({ value, label }),
                            )}
                          />
                        </Form.Item>
                        <Form.Item>
                          <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                          >
                            查询
                          </Button>
                        </Form.Item>
                      </Form>
                    </Card>
                    <Card className={styles.tablePanel}>
                      <Table
                        rowKey="id"
                        columns={requestColumns}
                        dataSource={requests}
                        loading={loading}
                        pagination={{ pageSize: 10, showSizeChanger: true }}
                      />
                    </Card>
                  </>
                ),
              },
              {
                key: "config",
                label: "审批规则配置",
                children: (
                  <Card className={styles.tablePanel}>
                    <Table
                      rowKey="capability_type"
                      columns={configColumns}
                      dataSource={approvalConfigs}
                      loading={loading}
                      pagination={false}
                    />
                  </Card>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
