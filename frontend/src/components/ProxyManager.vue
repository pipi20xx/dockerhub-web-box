<template>
  <div class="proxy-manager">
    <div class="header">
      <h3>代理管理</h3>
      <el-button type="primary" size="small" @click="openAddDialog">添加代理</el-button>
    </div>

    <el-table :data="proxyStore.proxies" style="width: 100%" empty-text="暂无代理">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="url" label="地址" />
      <el-table-column label="操作" width="150">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑代理' : '添加代理'" width="500px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="代理名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: local-socks5" />
        </el-form-item>
        <el-form-item label="代理地址" prop="url">
          <el-input v-model="form.url" placeholder="例如: http://127.0.0.1:7890" />
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
import { useProxyStore } from '@/stores/proxyStore';
import { ElMessage, ElMessageBox } from 'element-plus';

const proxyStore = useProxyStore();
const dialogVisible = ref(false);
const loading = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const formRef = ref(null);

const form = reactive({
  name: '',
  url: '',
});

const rules = reactive({
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入代理地址', trigger: 'blur' }],
});

onMounted(() => {
  proxyStore.fetchProxies();
});

const resetForm = () => {
  form.name = '';
  form.url = '';
  isEditing.value = false;
  editingId.value = null;
  if(formRef.value) formRef.value.resetFields();
};

const openAddDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (row) => {
    resetForm();
    isEditing.value = true;
    editingId.value = row.id;
    form.name = row.name;
    form.url = row.url;
    dialogVisible.value = true;
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        if (isEditing.value) {
            await proxyStore.updateProxy(editingId.value, form);
            ElMessage.success('代理更新成功');
        } else {
            await proxyStore.addProxy(form);
            ElMessage.success('代理添加成功');
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
  ElMessageBox.confirm(`确定删除代理 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await proxyStore.deleteProxy(row.id);
      ElMessage.success('删除成功');
    } catch (error) {
      ElMessage.error('删除失败');
    }
  });
};
</script>