<template>
  <div class="registry-manager">
    <div class="header-controls">
      <h3>仓库管理</h3>
      <el-button type="primary" size="small" @click="openAddDialog">添加仓库</el-button>
    </div>

    <el-table :data="registryStore.registries" v-loading="registryStore.loading" style="width: 100%" empty-text="暂无仓库配置">
      <el-table-column prop="name" label="仓库名称" width="180" />
      <el-table-column prop="url" label="地址 (Registry URL)" />
      <el-table-column label="绑定凭据" width="200">
        <template #default="scope">
          <el-tag v-if="getCredentialName(scope.row.credential_id)" type="info" size="small">
            {{ getCredentialName(scope.row.credential_id) }}
          </el-tag>
          <span v-else class="text-muted">未绑定</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="confirmDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑仓库 Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑仓库' : '添加仓库'" width="500px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: Docker Hub" />
        </el-form-item>
        <el-form-item label="仓库地址" prop="url">
          <el-input v-model="form.url" placeholder="例如: docker.io">
            <template #prepend>
              <el-select v-model="form.is_https" style="width: 100px">
                <el-option label="https://" :value="true" />
                <el-option label="http://" :value="false" />
              </el-select>
            </template>
          </el-input>
          <div class="form-tip">如果是 Docker Hub 请填 docker.io</div>
        </el-form-item>
        <el-form-item label="认证凭据">
          <el-select v-model="form.credential_id" placeholder="选择绑定凭据" clearable style="width: 100%;">
            <el-option label="不使用凭据 (匿名/公共)" :value="null" />
            <el-option
              v-for="cred in credentialStore.credentials"
              :key="cred.id"
              :label="`${cred.name} (${cred.username})`"
              :value="cred.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="warning" plain @click="testConnection" :loading="testing">测试连接</el-button>
          <el-button type="primary" @click="saveRegistry" :loading="saving">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRegistryStore } from '../stores/registryStore';
import { useCredentialStore } from '../stores/credentialStore';
import { ElMessage, ElMessageBox } from 'element-plus';
import apiClient from '@/services/api';

const registryStore = useRegistryStore();
const credentialStore = useCredentialStore();

const dialogVisible = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const saving = ref(false);
const testing = ref(false);
const formRef = ref(null);

const form = reactive({
  name: '',
  url: '',
  is_https: true,
  credential_id: null
});

// ... inside testConnection (keeping existing logic)

const testConnection = async () => {
  if (!form.url) {
    ElMessage.warning('请先输入仓库地址');
    return;
  }
  testing.value = true;
  try {
    const res = await apiClient.post('/registries/test', { ...form });
    const { status, message } = res.data;
    
    // 根据后端返回的 status 弹出不同颜色的消息
    if (status === 'success') {
      ElMessage.success(message);
    } else if (status === 'warning') {
      ElMessage.warning(message);
    } else if (status === 'info') {
      ElMessage.info(message);
    } else {
      ElMessage.success(message);
    }
  } catch (err) {
    ElMessage.error('测试失败: ' + (err.response?.data?.detail || err.message));
  } finally {
    testing.value = false;
  }
};

const rules = reactive({
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }]
});

onMounted(() => {
  registryStore.fetchRegistries();
  credentialStore.fetchCredentials();
});

const getCredentialName = (id) => {
  if (!id) return null;
  const cred = credentialStore.credentials.find(c => c.id === id);
  return cred ? cred.name : '未知凭据';
};

const resetForm = () => {
  form.name = '';
  form.url = '';
  form.is_https = true;
  form.credential_id = null;
  isEditing.value = false;
  editingId.value = null;
  if(formRef.value) formRef.value.resetFields();
};

const openAddDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (registry) => {
  isEditing.value = true;
  editingId.value = registry.id;
  form.name = registry.name;
  form.url = registry.url;
  form.is_https = registry.is_https !== undefined ? registry.is_https : true;
  form.credential_id = registry.credential_id;
  dialogVisible.value = true;
};

const saveRegistry = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        if (isEditing.value) {
          await registryStore.updateRegistry(editingId.value, { ...form });
          ElMessage.success('仓库更新成功');
        } else {
          await registryStore.addRegistry({ ...form });
          ElMessage.success('仓库添加成功');
        }
        dialogVisible.value = false;
      } catch (err) {
        ElMessage.error('保存失败: ' + (err.response?.data?.detail || err.message));
      } finally {
        saving.value = false;
      }
    }
  });
};

const confirmDelete = (registry) => {
  ElMessageBox.confirm(`确定要删除仓库 "${registry.name}" 吗？这可能导致关联的项目无法正常构建。`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await registryStore.deleteRegistry(registry.id);
      ElMessage.success('删除成功');
    } catch (err) {
      ElMessage.error('删除失败: ' + (err.response?.data?.detail || err.message));
    }
  });
};
</script>

<style scoped>
.registry-manager {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
}
.text-muted {
  color: #909399;
  font-size: 13px;
}
</style>
