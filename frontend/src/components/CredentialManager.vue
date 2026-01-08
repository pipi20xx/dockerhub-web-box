<template>
  <div class="credential-manager">
    <div class="header">
      <h3>凭证管理</h3>
      <el-button type="primary" size="small" @click="openAddDialog">添加凭证</el-button>
    </div>

    <el-table :data="credStore.credentials" style="width: 100%" empty-text="暂无凭证">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="password" label="密码" />
      <el-table-column label="操作" width="150">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑凭证' : '添加凭证'" width="500px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="凭证名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: dockerhub-main" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="text" placeholder="若不修改请留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="loading">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useCredentialStore } from '@/stores/credentialStore';
import { ElMessage, ElMessageBox } from 'element-plus';

const credStore = useCredentialStore();
const dialogVisible = ref(false);
const loading = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const formRef = ref(null);

const form = reactive({
  name: '',
  username: '',
  password: '',
});

const rules = reactive({
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }], // Only required on create, handled in submit
});

onMounted(() => {
  credStore.fetchCredentials();
});

const resetForm = () => {
  form.name = '';
  form.username = '';
  form.password = '';
  isEditing.value = false;
  editingId.value = null;
  if(formRef.value) formRef.value.resetFields();
};

const openAddDialog = () => {
  resetForm();
  // Password required for new
  rules.password = [{ required: true, message: '请输入密码', trigger: 'blur' }];
  dialogVisible.value = true;
};

const openEditDialog = (row) => {
    resetForm();
    isEditing.value = true;
    editingId.value = row.id;
    
    form.name = row.name;
    form.username = row.username;
    form.password = row.password; // Populate password
    
    // Password optional for edit
    rules.password = [{ required: false }];
    
    dialogVisible.value = true;
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        if (isEditing.value) {
            const dataToSend = { ...form };
            if (!dataToSend.password) delete dataToSend.password; // Don't send empty password
            await credStore.updateCredential(editingId.value, dataToSend);
            ElMessage.success('凭证更新成功');
        } else {
            await credStore.addCredential(form);
            ElMessage.success('凭证添加成功');
        }
        dialogVisible.value = false;
      } catch (error) {
        ElMessage.error(`操作失败: ${error.response?.data?.detail || error.message}`);
      } finally {
        loading.value = false;
      }
    }
  });
};

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除凭证 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await credStore.deleteCredential(row.id);
      ElMessage.success('删除成功');
    } catch (error) {
      ElMessage.error('删除失败');
    }
  });
};
</script>

<style scoped>
.credential-manager {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
