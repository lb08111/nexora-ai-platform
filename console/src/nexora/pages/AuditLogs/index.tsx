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

/* ---- Mapeamento de tipo de operação ---- */
const actionLabels: Record<string, string> = {
  "auth.login": "Login",
  "auth.logout": "Logout",
  "auth.register": "Cadastro",
  "auth.profile.update": "Alteração de conta",
  "auth.revoke_all_tokens": "Encerrar todas as sessões",
  "page.view": "Acesso à página",
  "api.mutate": "Operação na plataforma",
  "api.denied": "Bloqueio de permissão",
  "chat.create": "Criar conversa",
  "chat.update": "Atualizar conversa",
  "chat.delete": "Excluir conversa",
  "chat.batch_delete": "Exclusão em lote de conversas",
  "chat.message.send": "Enviar mensagem",
  "chat.reconnect": "Reconectar conversa",
  "chat.stop": "Parar conversa",
  "chat.file.upload": "Enviar anexo",
  "agent.tool.execute": "Chamada de ferramenta",
  "mcp.create.approved": "Criação de MCP aprovada",
  "mcp.create.rejected": "Criação de MCP rejeitada",
  "skill.create.approved": "Criação de habilidade aprovada",
  "skill.create.rejected": "Criação de habilidade rejeitada",
  "plugin.install.approved": "Instalação de plugin aprovada",
  "plugin.install.rejected": "Instalação de plugin rejeitada",
  "tool.create.approved": "Criação de ferramenta aprovada",
  "tool.create.rejected": "Criação de ferramenta rejeitada",
};

const statusLabels: Record<string, string> = {
  success: "Sucesso",
  failure: "Falha",
  denied: "Negado",
  started: "Em execução",
};

const statusColors: Record<string, string> = {
  success: "green",
  failure: "red",
  denied: "orange",
  started: "blue",
};

/* ---- Formatação de data/hora ---- */
function formatTime(timestamp: number) {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
}

/* ---- Exibe detail estruturado por tipo de action ---- */
function DetailContent({ event }: { event: AuditEvent }) {
  const { action, detail, resource_id, resource_type } = event;
  const d = detail || {};

  const baseItems = [
    { label: "ID do evento", value: event.id },
    { label: "Data/hora da operação", value: formatTime(event.timestamp) },
    { label: "Usuário da operação", value: event.actor },
    { label: "Tipo de operação", value: actionLabels[action] || action },
    { label: "Resultado", value: statusLabels[event.status] || event.status },
    { label: "Tipo de recurso", value: resource_type || "-" },
    { label: "ID do recurso", value: resource_id || "-" },
    { label: "IP de origem", value: event.ip || "-" },
  ];

  if (event.user_agent) {
    baseItems.push({ label: "Navegador", value: event.user_agent });
  }

  let contextItems: { label: string; value: string }[] = [];

  if (action === "chat.message.send") {
    contextItems = [
      { label: "Agente", value: String(d.agent_id || "-") },
      { label: "ID da conversa", value: String(d.session_id || "-") },
      { label: "Canal", value: String(d.channel || "-") },
      { label: "Usuário de destino", value: String(d.target_user || "-") },
      { label: "Tamanho da mensagem", value: String(d.message_length ?? "-") },
      { label: "Conteúdo da mensagem", value: String(d.message_preview || "-") },
    ];
  } else if (action === "agent.tool.execute") {
    contextItems = [
      { label: "Agente", value: String(d.agent_id || "-") },
      { label: "ID da chamada", value: String(d.tool_call_id || "-") },
      { label: "ID da conversa", value: String(d.session_id || "-") },
      { label: "Canal", value: String(d.channel || "-") },
      { label: "Motivo do disparo", value: String(d.reason || "-") },
    ];
    if (d.input_preview) {
      contextItems.push({ label: "Parâmetros de entrada", value: String(d.input_preview) });
    }
    if (d.result_preview) {
      contextItems.push({ label: "Resultado da execução", value: String(d.result_preview) });
    }
    if (d.error) {
      contextItems.push({ label: "Mensagem de erro", value: String(d.error) });
    }
  } else if (action === "api.mutate" || action === "api.denied") {
    contextItems = [
      { label: "Método HTTP", value: String(d.method || "-") },
      { label: "Caminho da requisição", value: resource_id || "-" },
      { label: "Permissão necessária", value: String(d.permission || "-") },
    ];
    if (d.status_code) {
      contextItems.push({ label: "Código de status", value: String(d.status_code) });
    }
    if (d.query) {
      contextItems.push({ label: "Parâmetros de consulta", value: String(d.query) });
    }
  } else if (action === "auth.login") {
    contextItems = [
      {
        label: "Perfil",
        value: Array.isArray(d.roles)
          ? d.roles.join(", ")
          : String(d.roles || "-"),
      },
    ];
    if (d.reason) {
      contextItems.push({ label: "Motivo da falha", value: String(d.reason) });
    }
  } else if (action === "auth.profile.update") {
    contextItems = [];
    if (d.username_changed !== undefined) {
      contextItems.push({
        label: "Nome de usuário alterado",
        value: d.username_changed ? "Sim" : "Não",
      });
    }
    if (d.password_changed !== undefined) {
      contextItems.push({
        label: "Senha alterada",
        value: d.password_changed ? "Sim" : "Não",
      });
    }
    if (d.reason) {
      contextItems.push({ label: "Motivo da falha", value: String(d.reason) });
    }
  } else if (action === "page.view") {
    contextItems = [
      { label: "Título da página", value: String(d.title || "-") },
      { label: "Caminho da página", value: resource_id || "-" },
    ];
  } else if (action === "chat.file.upload") {
    contextItems = [
      { label: "Agente", value: String(d.agent_id || "-") },
      {
        label: "Tamanho do arquivo",
        value: d.size ? `${Number(d.size).toLocaleString()} bytes` : "-",
      },
      { label: "Nome armazenado", value: String(d.stored_name || "-") },
    ];
  } else if (action.includes(".approved") || action.includes(".rejected")) {
    contextItems = [
      { label: "ID da solicitação de aprovação", value: String(d.approval_request_id || "-") },
    ];
    if (d.reason) {
      contextItems.push({ label: "Motivo da rejeição", value: String(d.reason) });
    }
    if (d.result) {
      contextItems.push({
        label: "Resultado da aprovação",
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
        title="Informações básicas"
        column={2}
        bordered
        size="small"
        style={{ marginBottom: 16 }}
      >
        {baseItems.map((item) => (
          <Descriptions.Item
            key={item.label}
            label={item.label}
            span={item.label === "Navegador" ? 2 : 1}
          >
            <Typography.Text copyable={item.label === "ID do evento"}>
              {item.value}
            </Typography.Text>
          </Descriptions.Item>
        ))}
      </Descriptions>

      {contextItems.length > 0 && (
        <Descriptions title="Detalhes da operação" column={1} bordered size="small">
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

/* ---- Página principal ---- */
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
        error instanceof Error ? error.message : "Falha ao carregar os logs de auditoria",
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
      if (!resp.ok) throw new Error(`Falha na exportação: ${resp.status}`);
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] || "audit_logs.csv";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
      message.success(`Exportado: ${events.length > 0 ? "logs de auditoria" : "dados"}`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha na exportação");
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    void loadEvents({ limit: 200 });
  }, []);

  /* ---- Resumo do detail (exibição curta na tabela) ---- */
  const detailSummary = (event: AuditEvent): string => {
    const { action, detail: d } = event;
    if (!d || Object.keys(d).length === 0) return "-";

    if (action === "chat.message.send") {
      return String(d.message_preview || "-");
    }
    if (action === "agent.tool.execute") {
      const parts: string[] = [];
      if (d.agent_id) parts.push(`Agente: ${d.agent_id}`);
      if (d.reason) parts.push(`Motivo: ${d.reason}`);
      if (d.error) parts.push(`Erro: ${d.error}`);
      return parts.join(" | ") || "-";
    }
    if (action === "api.mutate") {
      return `${d.method || ""} ${event.resource_id || ""}`.trim() || "-";
    }
    if (action === "api.denied") {
      return `${d.method || ""} ${event.resource_id || ""} (requer permissão ${
        d.permission || "?"
      })`.trim();
    }
    if (action === "page.view") {
      return String(d.title || "-");
    }
    if (action === "auth.login") {
      if (d.reason) return `Falha: ${d.reason}`;
      if (Array.isArray(d.roles)) return `Perfil: ${d.roles.join(", ")}`;
    }
    if (action === "chat.file.upload") {
      return `Arquivo: ${d.stored_name || "-"} (${
        d.size ? Number(d.size).toLocaleString() + " B" : "-"
      })`;
    }
    if (action.includes(".approved")) return "Aprovação concedida";
    if (action.includes(".rejected"))
      return `Aprovação rejeitada${d.reason ? ": " + d.reason : ""}`;

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
      title: "Data/Hora",
      dataIndex: "timestamp",
      key: "timestamp",
      width: 180,
      render: (value: number) => formatTime(value),
    },
    {
      title: "Usuário",
      dataIndex: "actor",
      key: "actor",
      width: 120,
      render: (value: string) => (
        <Typography.Text strong>{value}</Typography.Text>
      ),
    },
    {
      title: "Operação",
      dataIndex: "action",
      key: "action",
      width: 150,
      render: (value: string) => actionLabels[value] || value,
    },
    {
      title: "Resultado",
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
      title: "Objeto",
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
      title: "Resumo",
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
        parent="Gerenciamento de Segurança"
        current="Logs de Auditoria"
        subRow={
          <Typography.Text type="secondary">
            Registra logins de usuários, mensagens de chat, chamadas de ferramentas, operações na plataforma e bloqueios de permissão, facilitando a auditoria de segurança e o rastreamento de problemas.
            {events.length > 0 && ` Exibindo ${events.length} registros no momento.`}
          </Typography.Text>
        }
        extra={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exporting}
            >
              Exportar CSV
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadEvents(form.getFieldsValue())}
              loading={loading}
            >
              Atualizar
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
              <Form.Item name="actor" label="Usuário">
                <Input allowClear placeholder="Nome de usuário" style={{ width: 120 }} />
              </Form.Item>
              <Form.Item name="action" label="Operação">
                <Select
                  allowClear
                  style={{ width: 180 }}
                  placeholder="Todos"
                  options={Object.entries(actionLabels).map(
                    ([value, label]) => ({
                      value,
                      label,
                    }),
                  )}
                />
              </Form.Item>
              <Form.Item name="status" label="Resultado">
                <Select
                  allowClear
                  style={{ width: 100 }}
                  placeholder="Todos"
                  options={[
                    { value: "success", label: "Sucesso" },
                    { value: "failure", label: "Falha" },
                    { value: "denied", label: "Negado" },
                    { value: "started", label: "Em execução" },
                  ]}
                />
              </Form.Item>
              <Form.Item name="timeRange" label="Intervalo de tempo">
                <RangePicker />
              </Form.Item>
              <Form.Item name="limit" label="Quantidade">
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
                  Consultar
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
                showTotal: (total) => `Total de ${total}`,
              }}
              size="middle"
            />
          </Card>
        </div>
      </div>

      <Drawer
        title="Detalhes do evento de auditoria"
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
