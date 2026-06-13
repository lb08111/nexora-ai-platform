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
import styles from "../nexoraPages.module.less";

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
  "system.admin": "菜单：系统管理",
  "users.manage": "菜单：管理用户和角色",
  "users.view": "菜单：查看用户",
  "agents.manage": "菜单：智能体管理",
  "agents.use": "能力：使用智能体",
  "tools.manage": "菜单：工具配置",
  "tools.execute": "能力：调用工具/MCP/Skill",
  "models.manage": "菜单：模型管理",
  "mcp.manage": "菜单：MCP 配置",
  "governance.manage": "菜单：管理智能体权限",
  "governance.view": "菜单：查看智能体权限",
  "audit.view": "菜单：查看审计",
};

const capabilityPermissions = new Set(["agents.use", "tools.execute"]);
const permissionGroupLabels = {
  menu: "菜单权限",
  capability: "能力权限",
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
        error instanceof Error ? error.message : "加载用户权限失败",
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
        message.success("用户已更新");
      } else {
        await usersApi.createUser({
          username: values.username.trim(),
          password: values.password || "",
          roles: values.roles,
        });
        message.success("用户已创建");
      }
      setUserModalOpen(false);
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
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
        message.success("角色已更新");
      } else {
        await usersApi.createRole({
          id: values.id.trim(),
          name: values.name.trim(),
          description: values.description || "",
          permissions: values.permissions,
        });
        message.success("角色已创建");
      }
      setRoleModalOpen(false);
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUser = async (username: string) => {
    try {
      await usersApi.deleteUser(username);
      message.success("用户已删除");
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    try {
      await usersApi.deleteRole(roleId);
      message.success("角色已删除");
      await fetchAll();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  };

  const userColumns: ColumnsType<PlatformUser> = [
    {
      title: "用户名",
      dataIndex: "username",
      key: "username",
      render: (value) => <Typography.Text strong>{value}</Typography.Text>,
    },
    {
      title: "角色",
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
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (value: PlatformUser["status"]) => (
        <Tag color={value === "active" ? "green" : "default"}>
          {value === "active" ? "启用" : "停用"}
        </Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEditUser(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该用户？"
            onConfirm={() => handleDeleteUser(record.username)}
          >
            <Button size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const roleColumns: ColumnsType<PlatformRole> = [
    {
      title: "角色",
      dataIndex: "name",
      key: "name",
      render: (value, record) => (
        <Space direction="vertical" size={2}>
          <Space>
            <Typography.Text strong>{value}</Typography.Text>
            {record.builtin ? <Tag>内置</Tag> : <Tag color="blue">自定义</Tag>}
          </Space>
          <Typography.Text type="secondary">{record.id}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "说明",
      dataIndex: "description",
      key: "description",
      render: (value) => value || "-",
    },
    {
      title: "权限",
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
      title: "操作",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEditRole(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该角色？"
            onConfirm={() => handleDeleteRole(record.id)}
            disabled={record.builtin}
          >
            <Button size="small" danger disabled={record.builtin}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.nexoraPage}>
      <PageHeader
        className={styles.pageHeader}
        parent="权限管理"
        current="用户权限"
      />

      <div className={styles.content}>
        <Tabs
          className={styles.tabs}
          items={[
            {
              key: "users",
              label: "用户管理",
              children: (
                <Card className={styles.tablePanel}>
                  <div className={styles.toolbar}>
                    <Space>
                      <Button icon={<ReloadOutlined />} onClick={fetchAll}>
                        刷新
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openCreateUser}
                      >
                        新建用户
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
              label: "角色管理",
              children: (
                <Card className={styles.tablePanel}>
                  <div className={styles.toolbar}>
                    <Space>
                      <Button icon={<ReloadOutlined />} onClick={fetchAll}>
                        刷新
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={openCreateRole}
                      >
                        新建角色
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
        title={editingUser ? "编辑用户" : "新建用户"}
        open={userModalOpen}
        confirmLoading={saving}
        onCancel={() => setUserModalOpen(false)}
        onOk={handleUserSubmit}
        destroyOnHidden
      >
        <Form form={userForm} layout="vertical">
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            label={editingUser ? "重置密码" : "密码"}
            name="password"
            rules={
              editingUser ? [] : [{ required: true, message: "请输入初始密码" }]
            }
          >
            <Input.Password
              placeholder={editingUser ? "留空表示不修改" : "请输入初始密码"}
            />
          </Form.Item>

          <Form.Item
            label="角色"
            name="roles"
            rules={[{ required: true, message: "请选择角色" }]}
          >
            <Select
              mode="multiple"
              options={roles.map((role) => ({
                value: role.id,
                label: `${role.name} (${role.id})`,
              }))}
            />
          </Form.Item>

          <Form.Item label="状态" name="status">
            <Select
              options={[
                { value: "active", label: "启用" },
                { value: "disabled", label: "停用" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRole ? "编辑角色" : "新建角色"}
        open={roleModalOpen}
        confirmLoading={saving}
        onCancel={() => setRoleModalOpen(false)}
        onOk={handleRoleSubmit}
        width={720}
        destroyOnHidden
      >
        <Form form={roleForm} layout="vertical">
          <Form.Item
            label="角色 ID"
            name="id"
            rules={[{ required: true, message: "请输入角色 ID" }]}
          >
            <Input disabled={!!editingRole} placeholder="例如: deployer" />
          </Form.Item>

          <Form.Item
            label="角色名称"
            name="name"
            rules={[{ required: true, message: "请输入角色名称" }]}
          >
            <Input placeholder="例如: 发布工程师" />
          </Form.Item>

          <Form.Item label="角色说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item
            label="权限"
            name="permissions"
            rules={[{ required: true, message: "请选择权限" }]}
          >
            <Select mode="multiple" options={permissionSelectOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
