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
  "mcp.create": "Adicionar MCP",
  "mcp.delete": "Excluir MCP",
  "skill.create": "Adicionar Skill",
  "skill.delete": "Excluir Skill",
  "plugin.install": "Instalar plugin",
  "plugin.uninstall": "Desinstalar plugin",
  "tool.create": "Adicionar ferramenta",
  "tool.delete": "Excluir ferramenta",
  "acp.create": "Adicionar ACP",
  "acp.delete": "Excluir ACP",
};

const statusLabels: Record<ApprovalRequestStatus, string> = {
  pending: "Pendente",
  approved: "Aprovado",
  rejected: "Rejeitado",
  applied: "Aplicado",
  failed: "Falha na execução",
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
  tool: "Ferramenta",
  acp: "ACP",
  plugin: "Plugin",
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
        error instanceof Error
          ? error.message
          : "Falha ao carregar a Central de Aprovação",
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
      title: "Aprovar solicitação",
      content: `Confirmar aprovação de "${
        record.summary || record.resource_name
      }"?`,
      okText: "Aprovar",
      cancelText: "Cancelar",
      onOk: async () => {
        try {
          await governanceApi.approveApprovalRequest(record.id);
          message.success("Solicitação aprovada");
          await loadAll();
        } catch (error) {
          message.error(
            error instanceof Error ? error.message : "Falha ao aprovar",
          );
        }
      },
    });
  };

  const handleReject = (record: ApprovalRequest) => {
    let reason = "";
    Modal.confirm({
      title: "Rejeitar solicitação",
      content: (
        <Input.TextArea
          rows={3}
          placeholder="Informe o motivo da rejeição"
          onChange={(event) => {
            reason = event.target.value;
          }}
        />
      ),
      okText: "Rejeitar",
      okButtonProps: { danger: true },
      cancelText: "Cancelar",
      onOk: async () => {
        try {
          await governanceApi.rejectApprovalRequest(record.id, reason);
          message.success("Solicitação rejeitada");
          await loadAll();
        } catch (error) {
          message.error(
            error instanceof Error ? error.message : "Falha ao rejeitar",
          );
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
      message.success("Configuração atualizada");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
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
      message.success("Configuração atualizada");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setApprovalSaving(null);
    }
  };

  // ── Columns ──────────────────────────────────────────────────────────────

  const requestColumns: ColumnsType<ApprovalRequest> = [
    {
      title: "Conteúdo da Solicitação",
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
      title: "Tipo",
      dataIndex: "action",
      key: "action",
      width: 120,
      render: (value: string) => <Tag>{actionLabels[value] || value}</Tag>,
    },
    {
      title: "Status",
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
      title: "Solicitante",
      dataIndex: "requester",
      key: "requester",
      width: 130,
      render: (value: string) => value || "-",
    },
    {
      title: "Aprovador",
      dataIndex: "approver",
      key: "approver",
      width: 130,
      render: (value: string) => value || "-",
    },
    {
      title: "Data/Hora",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (value: number) => formatTime(value),
    },
    {
      title: "Resultado",
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
      title: "Ações",
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
              Aprovar
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => handleReject(record)}
            >
              Rejeitar
            </Button>
          </Space>
        ) : (
          <Typography.Text type="secondary">Processado</Typography.Text>
        ),
    },
  ];

  const configColumns: ColumnsType<CapabilityApprovalConfig> = [
    {
      title: "Tipo de capacidade",
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
      title: "Política de adição",
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
            { value: "none", label: "Não requer aprovação" },
            { value: "approval", label: "Requer aprovação" },
          ]}
        />
      ),
    },
    {
      title: "Política de remoção",
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
            { value: "none", label: "Não requer aprovação" },
            { value: "log", label: "Aprovação automática" },
            { value: "approval", label: "Requer aprovação" },
          ]}
        />
      ),
    },
    {
      title: "Função do aprovador",
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
        parent="Gerenciamento de Segurança"
        current="Central de Aprovação"
        subRow={
          <Typography.Text type="secondary">
            Processe solicitações de aprovação de mudanças de capacidade;
            configure os controles de aprovação de adição/remoção por tipo de
            capacidade.
          </Typography.Text>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
            Atualizar
          </Button>
        }
      />

      <div className={styles.content}>
        <div className={styles.stack}>
          <div className={styles.metricGrid}>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Solicitações Pendentes
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {pendingCount}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Total de Solicitações
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {requests.length}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Regras de Aprovação Ativas
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
                label: "Solicitações de Aprovação",
                children: (
                  <>
                    <Card className={styles.panel} style={{ marginBottom: 16 }}>
                      <Form
                        form={filterForm}
                        className={styles.filterForm}
                        onFinish={loadAll}
                      >
                        <Form.Item name="status" label="Status">
                          <Select
                            allowClear
                            style={{ width: 140 }}
                            options={Object.entries(statusLabels).map(
                              ([value, label]) => ({ value, label }),
                            )}
                          />
                        </Form.Item>
                        <Form.Item name="action" label="Tipo">
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
                            Consultar
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
                label: "Configuração de Regras de Aprovação",
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
