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
  Transfer,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import type { AgentSummary } from "../../../api/types/agents";
import { agentsApi } from "../../../api/modules/agents";
import { PageHeader } from "../../../components/PageHeader";
import { useAppMessage } from "../../../hooks/useAppMessage";
import {
  type PlatformRole,
  type PlatformUser,
  usersApi,
} from "../../api/users";
import {
  type AgentGrant,
  type AgentTemplate,
  type CapabilityApprovalConfig,
  multiTenantApi,
} from "../../api/multiTenant";
import styles from "../nexoraPages.module.less";

// ── Helpers ──────────────────────────────────────────────────────────────

const capTypeLabels: Record<string, string> = {
  skill: "Skill",
  mcp: "MCP",
  tool: "Ferramenta",
  acp: "ACP",
  plugin: "Plugin",
};

// ── Component ────────────────────────────────────────────────────────────

export default function OpsGovernancePage() {
  const { message } = useAppMessage();

  // shared data
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [roles, setRoles] = useState<PlatformRole[]>([]);
  const [loading, setLoading] = useState(false);

  // agent grants
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [grants, setGrants] = useState<AgentGrant[]>([]);
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [grantTargetKeys, setGrantTargetKeys] = useState<string[]>([]);
  const [grantSaving, setGrantSaving] = useState(false);

  // capability approval config
  const [approvalConfigs, setApprovalConfigs] = useState<
    CapabilityApprovalConfig[]
  >([]);
  const [approvalSaving, setApprovalSaving] = useState<string | null>(null);

  // templates
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AgentTemplate | null>(
    null,
  );
  const [templateForm] = Form.useForm();
  const [templateSaving, setTemplateSaving] = useState(false);

  // ── Data loading ─────────────────────────────────────────────────────────

  const loadAll = async () => {
    setLoading(true);
    try {
      const [agentList, userList, roleList, configList, templateList] =
        await Promise.all([
          agentsApi.listAgents().catch(() => ({ agents: [] })),
          usersApi.listUsers().catch(() => []),
          usersApi.listRoles().catch(() => []),
          multiTenantApi.listApprovalConfigs().catch(() => []),
          multiTenantApi.listTemplates().catch(() => []),
        ]);
      setAgents(agentList.agents || []);
      setUsers(userList);
      setRoles(roleList);
      setApprovalConfigs(configList);
      setTemplates(templateList);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao carregar");
    } finally {
      setLoading(false);
    }
  };

  const loadGrantsForAgent = async (agentId: string) => {
    try {
      const list = await multiTenantApi.listGrantsForAgent(agentId);
      setGrants(list);
    } catch {
      setGrants([]);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  // ── Agent Grants ─────────────────────────────────────────────────────────

  const openGrantModal = async (agentId: string) => {
    setSelectedAgentId(agentId);
    setGrantModalOpen(true);
    await loadGrantsForAgent(agentId);
  };

  useEffect(() => {
    if (grantModalOpen && grants.length >= 0) {
      setGrantTargetKeys(grants.map((g) => g.username));
    }
  }, [grants, grantModalOpen]);

  const handleGrantSave = async () => {
    if (!selectedAgentId) return;
    setGrantSaving(true);
    try {
      const currentUsers = new Set(grants.map((g) => g.username));
      const targetUsers = new Set(grantTargetKeys);

      const toGrant = grantTargetKeys.filter((u) => !currentUsers.has(u));
      const toRevoke = grants
        .map((g) => g.username)
        .filter((u) => !targetUsers.has(u));

      if (toGrant.length > 0) {
        await multiTenantApi.batchGrant(selectedAgentId, toGrant);
      }
      if (toRevoke.length > 0) {
        await multiTenantApi.batchRevoke(selectedAgentId, toRevoke);
      }

      message.success("Autorização atualizada");
      setGrantModalOpen(false);
      setSelectedAgentId(null);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setGrantSaving(false);
    }
  };

  const selectedAgentName = useMemo(() => {
    if (!selectedAgentId) return "";
    const agent = agents.find((a) => a.id === selectedAgentId);
    return agent?.name || selectedAgentId;
  }, [selectedAgentId, agents]);

  const agentColumns: ColumnsType<AgentSummary> = [
    {
      title: "Agente",
      key: "name",
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong>{record.name || record.id}</Typography.Text>
          <Typography.Text type="secondary" ellipsis style={{ maxWidth: 400 }}>
            {record.description || "Sem descrição"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 180,
      render: (value: string) => (
        <Typography.Text copyable type="secondary">
          {value}
        </Typography.Text>
      ),
    },
    {
      title: "Status",
      dataIndex: "enabled",
      key: "enabled",
      width: 90,
      render: (value: boolean) => (
        <Tag color={value ? "green" : "default"}>
          {value ? "Ativado" : "Desativado"}
        </Tag>
      ),
    },
    {
      title: "Ações",
      key: "actions",
      width: 130,
      render: (_, record) => (
        <Button
          size="small"
          icon={<TeamOutlined />}
          onClick={() => openGrantModal(record.id)}
        >
          Gerenciar autorização
        </Button>
      ),
    },
  ];

  // ── Capability Approval Config ───────────────────────────────────────────

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

  const approvalColumns: ColumnsType<CapabilityApprovalConfig> = [
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
      title: "Função aprovadora",
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

  // ── Templates ────────────────────────────────────────────────────────────

  const openTemplateCreate = () => {
    setEditingTemplate(null);
    templateForm.resetFields();
    templateForm.setFieldsValue({
      capabilities_tools: "",
      capabilities_skills: "",
      capabilities_mcps: "",
    });
    setTemplateModalOpen(true);
  };

  const openTemplateEdit = (tpl: AgentTemplate) => {
    setEditingTemplate(tpl);
    templateForm.setFieldsValue({
      template_id: tpl.template_id,
      name: tpl.name,
      description: tpl.description || "",
      capabilities_tools: (tpl.capabilities?.tools || []).join(", "),
      capabilities_skills: (tpl.capabilities?.skills || []).join(", "),
      capabilities_mcps: (tpl.capabilities?.mcps || []).join(", "),
    });
    setTemplateModalOpen(true);
  };

  const handleTemplateDelete = (tpl: AgentTemplate) => {
    Modal.confirm({
      title: "Excluir modelo",
      content: `Confirma a exclusão do modelo "${tpl.name}"?`,
      okText: "Excluir",
      okButtonProps: { danger: true },
      cancelText: "Cancelar",
      onOk: async () => {
        try {
          await multiTenantApi.deleteTemplate(tpl.template_id);
          message.success("Modelo excluído");
          setTemplates((prev) =>
            prev.filter((t) => t.template_id !== tpl.template_id),
          );
        } catch (error) {
          message.error(error instanceof Error ? error.message : "Falha ao excluir");
        }
      },
    });
  };

  const handleTemplateSave = async () => {
    const values = await templateForm.validateFields();
    setTemplateSaving(true);
    try {
      const capabilities: Record<string, string[]> = {};
      if (values.capabilities_tools?.trim()) {
        capabilities.tools = values.capabilities_tools
          .split(",")
          .map((s: string) => s.trim())
          .filter(Boolean);
      }
      if (values.capabilities_skills?.trim()) {
        capabilities.skills = values.capabilities_skills
          .split(",")
          .map((s: string) => s.trim())
          .filter(Boolean);
      }
      if (values.capabilities_mcps?.trim()) {
        capabilities.mcps = values.capabilities_mcps
          .split(",")
          .map((s: string) => s.trim())
          .filter(Boolean);
      }

      const payload = {
        template_id: values.template_id,
        name: values.name,
        description: values.description || "",
        capabilities,
      };

      if (editingTemplate) {
        const updated = await multiTenantApi.updateTemplate(
          editingTemplate.template_id,
          payload,
        );
        setTemplates((prev) =>
          prev.map((t) =>
            t.template_id === editingTemplate.template_id ? updated : t,
          ),
        );
      } else {
        const created = await multiTenantApi.createTemplate(payload);
        setTemplates((prev) => [...prev, created]);
      }

      message.success(editingTemplate ? "Modelo atualizado" : "Modelo criado");
      setTemplateModalOpen(false);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setTemplateSaving(false);
    }
  };

  const templateColumns: ColumnsType<AgentTemplate> = [
    {
      title: "Nome do modelo",
      key: "name",
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Space>
            <Typography.Text strong>{record.name}</Typography.Text>
            {record.builtin && <Tag color="blue">Integrado</Tag>}
          </Space>
          <Typography.Text type="secondary" ellipsis style={{ maxWidth: 400 }}>
            {record.description || "Sem descrição"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "ID do modelo",
      dataIndex: "template_id",
      key: "template_id",
      width: 180,
    },
    {
      title: "Capacidades incluídas",
      key: "capabilities",
      render: (_, record) => {
        const caps = record.capabilities || {};
        const tags: { label: string; items: string[] }[] = [
          { label: "Ferramenta", items: caps.tools || [] },
          { label: "Skill", items: caps.skills || [] },
          { label: "MCP", items: caps.mcps || [] },
        ];
        return (
          <Space wrap size={4}>
            {tags
              .filter((t) => t.items.length > 0)
              .map((t) => (
                <Tag key={t.label}>
                  {t.label}: {t.items.length}
                </Tag>
              ))}
            {tags.every((t) => t.items.length === 0) && (
              <Typography.Text type="secondary">Nenhuma</Typography.Text>
            )}
          </Space>
        );
      },
    },
    {
      title: "Ações",
      key: "actions",
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => openTemplateEdit(record)}
          >
            Editar
          </Button>
          {!record.builtin && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleTemplateDelete(record)}
            />
          )}
        </Space>
      ),
    },
  ];

  // ── Stats ────────────────────────────────────────────────────────────────

  const enabledApprovalCount = approvalConfigs.filter(
    (c) => c.add_policy !== "none" || c.remove_policy !== "none",
  ).length;

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className={styles.nexoraPage}>
      <PageHeader
        className={styles.pageHeader}
        parent="Gerenciamento de Permissões"
        current="Autorização de agentes"
        subRow={
          <Typography.Text type="secondary">
            Após criar um agente, o administrador o autoriza para uso pelos usuários; configure o controle de aprovação de forma independente por tipo de capacidade; inicialize rapidamente as capacidades do agente por meio de modelos.
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
                Total de agentes
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {agents.length}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Usuários da plataforma
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {users.length}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Regras de aprovação ativadas
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {enabledApprovalCount}/{approvalConfigs.length}
              </Typography.Title>
            </Card>
            <Card className={styles.metricCard} size="small">
              <Typography.Text className={styles.metricLabel}>
                Modelos de capacidade
              </Typography.Text>
              <Typography.Title className={styles.metricValue} level={3}>
                {templates.length}
              </Typography.Title>
            </Card>
          </div>

          <Tabs
            className={styles.tabs}
            items={[
              {
                key: "grants",
                label: "Autorização de agentes",
                children: (
                  <Card className={styles.tablePanel}>
                    <Table
                      rowKey="id"
                      columns={agentColumns}
                      dataSource={agents}
                      loading={loading}
                      pagination={{ pageSize: 10, showSizeChanger: true }}
                    />
                  </Card>
                ),
              },
              {
                key: "approval",
                label: "Configuração de aprovação de capacidades",
                children: (
                  <Card className={styles.tablePanel}>
                    <Table
                      rowKey="capability_type"
                      columns={approvalColumns}
                      dataSource={approvalConfigs}
                      loading={loading}
                      pagination={false}
                    />
                  </Card>
                ),
              },
              {
                key: "templates",
                label: "Modelos de agente",
                children: (
                  <Card className={styles.tablePanel}>
                    <div className={styles.toolbar}>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openTemplateCreate}
                      >
                        Adicionar modelo
                      </Button>
                    </div>
                    <Table
                      rowKey="template_id"
                      columns={templateColumns}
                      dataSource={templates}
                      loading={loading}
                      pagination={{ pageSize: 10, showSizeChanger: true }}
                    />
                  </Card>
                ),
              },
            ]}
          />
        </div>
      </div>

      {/* Grant Modal — Transfer picker */}
      <Modal
        title={
          <Space>
            <TeamOutlined />
            <span>Gerenciar autorização — {selectedAgentName}</span>
          </Space>
        }
        open={grantModalOpen}
        onCancel={() => {
          setGrantModalOpen(false);
          setSelectedAgentId(null);
        }}
        onOk={handleGrantSave}
        confirmLoading={grantSaving}
        okText="Salvar"
        cancelText="Cancelar"
        width={640}
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
          Selecione à esquerda os usuários que terão acesso autorizado a este agente; à direita estão os usuários já autorizados.
        </Typography.Paragraph>
        <Transfer
          dataSource={users.map((u) => ({
            key: u.username,
            title: u.username,
            description: u.roles.join(", "),
            disabled: u.status === "disabled",
          }))}
          titles={["Todos os usuários", "Autorizados"]}
          targetKeys={grantTargetKeys}
          onChange={(nextTargetKeys) =>
            setGrantTargetKeys(nextTargetKeys as string[])
          }
          render={(item) => (
            <span>
              {item.title}
              {item.description ? (
                <Typography.Text
                  type="secondary"
                  style={{ marginLeft: 8, fontSize: 12 }}
                >
                  ({item.description})
                </Typography.Text>
              ) : null}
            </span>
          )}
          listStyle={{ width: 260, height: 320 }}
          showSearch
          filterOption={(input, item) =>
            (item.title ?? "").toLowerCase().includes(input.toLowerCase())
          }
        />
      </Modal>

      {/* Template Modal */}
      <Modal
        title={editingTemplate ? "Editar modelo" : "Adicionar modelo"}
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        onOk={handleTemplateSave}
        confirmLoading={templateSaving}
        okText="Salvar"
        cancelText="Cancelar"
        destroyOnHidden
      >
        <Form form={templateForm} layout="vertical">
          <Form.Item
            name="template_id"
            label="ID do modelo"
            rules={[{ required: true, message: "Digite o ID do modelo" }]}
          >
            <Input
              placeholder="ex.: custom-template-1"
              disabled={Boolean(editingTemplate)}
            />
          </Form.Item>
          <Form.Item
            name="name"
            label="Nome do modelo"
            rules={[{ required: true, message: "Digite o nome do modelo" }]}
          >
            <Input placeholder="ex.: Pacote de operações personalizado" />
          </Form.Item>
          <Form.Item name="description" label="Descrição">
            <Input.TextArea rows={2} placeholder="Descrição da finalidade do modelo" />
          </Form.Item>
          <Form.Item name="capabilities_tools" label="Ferramentas (separadas por vírgula)">
            <Input.TextArea
              rows={2}
              placeholder="read_file, write_file, execute_command"
            />
          </Form.Item>
          <Form.Item name="capabilities_skills" label="Skill (separadas por vírgula)">
            <Input.TextArea rows={2} placeholder="log_query, metric_check" />
          </Form.Item>
          <Form.Item name="capabilities_mcps" label="MCP (separados por vírgula)">
            <Input.TextArea rows={2} placeholder="prometheus, grafana" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
