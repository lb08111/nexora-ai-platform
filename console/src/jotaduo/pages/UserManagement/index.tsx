import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageHeader } from "../../../components/PageHeader";
import {
  type PlatformRole,
  type PlatformUser,
  usersApi,
} from "../../api/users";
import { useAppMessage } from "../../../hooks/useAppMessage";
import styles from "../jotaduoPages.module.less";

type UserFormValues = {
  username: string;
  password?: string;
  roles: string[];
  status: "active" | "disabled";
};

type RoleFormValues = {
  id: string;
  name: string;
  description?: string;
  permissions: string[];
};

const permissionLabels: Record<string, string> = {
  "system.admin": "Menu: Gerenciamento do Sistema",
  "users.manage": "Menu: Gerenciar Usuários e Funções",
  "users.view": "Menu: Visualizar Usuários",
  "agents.manage": "Menu: Gerenciamento de Agentes",
  "agents.use": "Capacidade: Usar Agentes",
  "tools.manage": "Menu: Configuração de Ferramentas",
  "tools.execute": "Capacidade: Chamar Ferramentas/MCP/Skill",
  "models.manage": "Menu: Gerenciamento de Modelos",
  "mcp.manage": "Menu: Configuração de MCP",
  "governance.manage": "Menu: Gerenciar Permissões de Agentes",
  "governance.view": "Menu: Visualizar Permissões de Agentes",
  "audit.view": "Menu: Visualizar Auditoria",
};

const capabilityPermissions = new Set(["agents.use", "tools.execute"]);
const permissionGroupLabels = {
  menu: "Permissões de Menu",
  capability: "Permissões de Capacidade",
};

function permissionText(permission: string) {
  return permissionLabels[permission] || permission;
}

export default function UserManagementPage() {
  const { message } = useAppMessage();
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [roles, setRoles] = useState<PlatformRole[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<PlatformUser | null>(null);
  const [editingRole, setEditingRole] = useState<PlatformRole | null>(null);
  const [userForm] = Form.useForm<UserFormValues>();
  const [roleForm] = Form.useForm<RoleFormValues>();

  const roleNameMap = useMemo(
    () => Object.fromEntries(roles.map((role) => [role.id, role.name])),
    [roles],
  );

  const permissionSelectOptions = useMemo(() => {
    const toOptions = (items: string[]) =>
      items.map((permission) => ({
        value: permission,
        label: `${permissionText(permission)} (${permission})`,
      }));
    const capability = permissions.filter((permission) =>
      capabilityPermissions.has(permission),
    );
    const menu = permissions.filter(
      (permission) => !capabilityPermissions.has(permission),
    );
    return [
      {
        label: permissionGroupLabels.menu,
        options: toOptions(menu),
      },
      {
        label: permissionGroupLabels.capability,
        options: toOptions(capability),
      },
    ];
  }, [permissions]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [userList, roleList, permissionList] = await Promise.all([
        usersApi.listUsers(),
        usersApi.listRoles(),
        usersApi.listPermissions(),
      ]);
      setUsers(userList);
      setRoles(roleList);
      setPermissions(permissionList);
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : "Falha ao carregar permissões de usuário",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const openCreateUser = () => {
    setEditingUser(null);
    userForm.resetFields();
    userForm.setFieldsValue({ roles: ["operator"], status: "active" });
    setUserModalOpen(true);
  };

  const openEditUser = (user: PlatformUser) => {
    setEditingUser(user);
    userForm.setFieldsValue({
      username: user.username,
      roles: user.roles,
      status: user.status,
      password: "",
    });
    setUserModalOpen(true);
  };

  const openCreateRole = () => {
    setEditingRole(null);
    roleForm.resetFields();
    roleForm.setFieldsValue({ permissions: ["agents.use"] });
    setRoleModalOpen(true);
  };

  const openEditRole = (role: PlatformRole) => {
    setEditingRole(role);
    roleForm.setFieldsValue({
      id: role.id,
      name: role.name,
      description: role.description,
      permissions: role.permissions,
    });
    setRoleModalOpen(true);
  };

  const handleUserSubmit = async () => {
    const values = await userForm.validateFields();
    setSaving(true);
    try {
      if (editingUser) {
        await usersApi.updateUser(editingUser.username, {
          roles: values.roles,
          status: values.status,
          password: values.password?.trim() || undefined,
        });
        message.success("Usuário atualizado");
      } else {
        await usersApi.createUser({
          username: values.username.trim(),
          password: values.password || "",
          roles: values.roles,
        });
        message.success("Usuário criado");
      }
      setUserModalOpen(false);
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleRoleSubmit = async () => {
    const values = await roleForm.validateFields();
    setSaving(true);
    try {
      if (editingRole) {
        await usersApi.updateRole(editingRole.id, {
          name: values.name,
          description: values.description || "",
          permissions: values.permissions,
        });
        message.success("Função atualizada");
      } else {
        await usersApi.createRole({
          id: values.id.trim(),
          name: values.name.trim(),
          description: values.description || "",
          permissions: values.permissions,
        });
        message.success("Função criada");
      }
      setRoleModalOpen(false);
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Falha ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUser = async (username: string) => {
    try {
      await usersApi.deleteUser(username);
      message.success("Usuário excluído");
      await fetchAll();
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : "Falha ao excluir",
      );
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    try {
      await usersApi.deleteRole(roleId);
      message.success("Função excluída");
      await fetchAll();
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : "Falha ao excluir",
      );
    }
  };

  const userColumns: ColumnsType<PlatformUser> = [
    {
      title: "Nome de usuário",
      dataIndex: "username",
      key: "username",
      render: (value) => <Typography.Text strong>{value}</Typography.Text>,
    },
    {
      title: "Função",
      dataIndex: "roles",
      key: "roles",
      render: (value: string[]) => (
        <Space wrap>
          {value.map((roleId) => (
            <Tag color={roleId === "admin" ? "red" : "blue"} key={roleId}>
              {roleNameMap[roleId] || roleId}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (value: PlatformUser["status"]) => (
        <Tag color={value === "active" ? "green" : "default"}>
          {value === "active" ? "Ativado" : "Desativado"}
        </Tag>
      ),
    },
    {
      title: "Ações",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEditUser(record)}>
            Editar
          </Button>
          <Popconfirm
            title="Confirma a exclusão deste usuário?"
            onConfirm={() => handleDeleteUser(record.username)}
          >
            <Button size="small" danger>
              Excluir
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const roleColumns: ColumnsType<PlatformRole> = [
    {
      title: "Função",
      dataIndex: "name",
      key: "name",
      render: (value, record) => (
        <Space direction="vertical" size={2}>
          <Space>
            <Typography.Text strong>{value}</Typography.Text>
            {record.builtin ? (
              <Tag>Integrada</Tag>
            ) : (
              <Tag color="blue">Personalizada</Tag>
            )}
          </Space>
          <Typography.Text type="secondary">{record.id}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "Descrição",
      dataIndex: "description",
      key: "description",
      render: (value) => value || "-",
    },
    {
      title: "Permissões",
      dataIndex: "permissions",
      key: "permissions",
      render: (value: string[]) => (
        <Space wrap>
          {value.map((permission) => (
            <Tag key={permission}>{permissionText(permission)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "Ações",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEditRole(record)}>
            Editar
          </Button>
          <Popconfirm
            title="Confirma a exclusão desta função?"
            onConfirm={() => handleDeleteRole(record.id)}
            disabled={record.builtin}
          >
            <Button size="small" danger disabled={record.builtin}>
              Excluir
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.jotaduoPage}>
      <PageHeader
        className={styles.pageHeader}
        parent="Gerenciamento de Permissões"
        current="Permissões de Usuário"
      />

      <div className={styles.content}>
        <Tabs
          className={styles.tabs}
          items={[
            {
              key: "users",
              label: "Gerenciamento de Usuários",
              children: (
                <Card className={styles.tablePanel}>
                  <div className={styles.toolbar}>
                    <Space>
                      <Button icon={<ReloadOutlined />} onClick={fetchAll}>
                        Atualizar
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openCreateUser}
                      >
                        Adicionar Usuário
                      </Button>
                    </Space>
                  </div>
                  <Table
                    rowKey="id"
                    loading={loading}
                    columns={userColumns}
                    dataSource={users}
                    pagination={false}
                  />
                </Card>
              ),
            },
            {
              key: "roles",
              label: "Gerenciamento de Funções",
              children: (
                <Card className={styles.tablePanel}>
                  <div className={styles.toolbar}>
                    <Space>
                      <Button icon={<ReloadOutlined />} onClick={fetchAll}>
                        Atualizar
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openCreateRole}
                      >
                        Adicionar Função
                      </Button>
                    </Space>
                  </div>
                  <Table
                    rowKey="id"
                    loading={loading}
                    columns={roleColumns}
                    dataSource={roles}
                    pagination={false}
                  />
                </Card>
              ),
            },
          ]}
        />
      </div>

      <Modal
        title={editingUser ? "Editar Usuário" : "Adicionar Usuário"}
        open={userModalOpen}
        confirmLoading={saving}
        onCancel={() => setUserModalOpen(false)}
        onOk={handleUserSubmit}
        destroyOnHidden
      >
        <Form form={userForm} layout="vertical">
          <Form.Item
            label="Nome de usuário"
            name="username"
            rules={[{ required: true, message: "Digite o nome de usuário" }]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            label={editingUser ? "Redefinir senha" : "Senha"}
            name="password"
            rules={
              editingUser
                ? []
                : [{ required: true, message: "Digite a senha inicial" }]
            }
          >
            <Input.Password
              placeholder={
                editingUser
                  ? "Deixe em branco para não alterar"
                  : "Digite a senha inicial"
              }
            />
          </Form.Item>

          <Form.Item
            label="Função"
            name="roles"
            rules={[{ required: true, message: "Selecione a função" }]}
          >
            <Select
              mode="multiple"
              options={roles.map((role) => ({
                value: role.id,
                label: `${role.name} (${role.id})`,
              }))}
            />
          </Form.Item>

          <Form.Item label="Status" name="status">
            <Select
              options={[
                { value: "active", label: "Ativado" },
                { value: "disabled", label: "Desativado" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRole ? "Editar Função" : "Adicionar Função"}
        open={roleModalOpen}
        confirmLoading={saving}
        onCancel={() => setRoleModalOpen(false)}
        onOk={handleRoleSubmit}
        width={720}
        destroyOnHidden
      >
        <Form form={roleForm} layout="vertical">
          <Form.Item
            label="ID da Função"
            name="id"
            rules={[{ required: true, message: "Digite o ID da função" }]}
          >
            <Input disabled={!!editingRole} placeholder="Ex: deployer" />
          </Form.Item>

          <Form.Item
            label="Nome da Função"
            name="name"
            rules={[{ required: true, message: "Digite o nome da função" }]}
          >
            <Input placeholder="Ex: Engenheiro de Implantação" />
          </Form.Item>

          <Form.Item label="Descrição da Função" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item
            label="Permissões"
            name="permissions"
            rules={[{ required: true, message: "Selecione as permissões" }]}
          >
            <Select mode="multiple" options={permissionSelectOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
