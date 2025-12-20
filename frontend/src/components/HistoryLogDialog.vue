<template>
  <el-dialog
    v-model="isDialogVisible"
    :title="`项目 '${currentProjectName}' 的历史日志`"
    width="70%"
    @open="fetchLogs"
  >
    <el-table :data="logs" v-loading="isLoading" style="width: 100%" height="50vh">
      <el-table-column prop="created_at" label="执行时间" width="200">
        <template #default="scope">
          <span>{{ formatTime(scope.row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="tag" label="Tag" width="150" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
                {{ formatStatus(scope.row.status) }}
            </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button size="small" @click="showLogContent(scope.row)">在弹窗中查看</el-button>
          <!-- ✨ “在主面板查看”按钮已被删除 -->
          <!-- ✨ 新增“删除”按钮 -->
          <el-button size="small" type="danger" plain @click="handleDeleteLog(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="logContentVisible"
      title="日志内容"
      width="60%"
      append-to-body
    >
      <pre class="log-content-box">{{ logContent }}</pre>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue';
import apiClient from '@/services/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useTaskStore } from '@/stores/taskStore';
import { useProjectStore } from '@/stores/projectStore';

const props = defineProps({
  modelValue: Boolean,
  projectId: String,
});
const emit = defineEmits(['update:modelValue']);

const taskStore = useTaskStore();
const projectStore = useProjectStore();

const logs = ref([]);
const isLoading = ref(false);
const logContentVisible = ref(false);
const logContent = ref('');

const isDialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const currentProjectName = computed(() => {
  const project = projectStore.projects.find(p => p.id === props.projectId);
  return project ? project.name : '...';
});

const fetchLogs = async () => {
  if (!props.projectId) return;
  isLoading.value = true;
  try {
    const response = await apiClient.get(`/tasks/projects/${props.projectId}/logs`);
    logs.value = response.data;
  } catch (error) {
    ElMessage.error('获取历史日志失败');
  } finally {
    isLoading.value = false;
  }
};

const showLogContent = async (task) => {
  try {
    const response = await apiClient.get(`/tasks/logs/${task.id}/content`);
    logContent.value = response.data;
    logContentVisible.value = true;
  } catch (error) {
    ElMessage.error('获取日志内容失败');
  }
};

// ✨ --- “在主面板查看”的函数已被删除 ---

const getStatusTagType = (status) => {
  switch (status) {
    case 'SUCCESS':
      return 'success';
    case 'FAILED':
      return 'danger';
    case 'PENDING':
      return 'warning';
    default:
      return 'info';
  }
};

const formatStatus = (status) => {
  switch (status) {
    case 'SUCCESS':
      return '成功';
    case 'FAILED':
      return '失败';
    case 'PENDING':
      return '进行中';
    default:
      return status;
  }
};

const formatTime = (isoString) => {
  if (!isoString) return '';
  let utcIsoString = isoString.replace(' ', 'T');
  if (!utcIsoString.endsWith('Z') && !utcIsoString.includes('+')) {
    utcIsoString += 'Z';
  }
  const date = new Date(utcIsoString);
  const options = {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  };
  try {
    return new Intl.DateTimeFormat('zh-CN', options).format(date);
  } catch (e) {
    console.error("格式化日期时出错:", e);
    return "日期无效";
  }
};

// ✨ --- 新增：删除单条日志的函数 --- ✨
const handleDeleteLog = (task) => {
  ElMessageBox.confirm(
    `确定要删除这条执行于 [${formatTime(task.created_at)}]，Tag为 [${task.tag}] 的日志吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await apiClient.delete(`/tasks/logs/${task.id}`);
      ElMessage.success('日志删除成功');
      // 删除成功后，重新获取列表以刷新UI
      fetchLogs(); 
    } catch (error) {
      ElMessage.error(`删除失败: ${error.response?.data?.detail || error.message}`);
    }
  });
};

</script>

<style scoped>
.log-content-box {
  background-color: #1f1f1f;
  color: #d4d4d4;
  padding: 1rem;
  border-radius: 4px;
  max-height: 60vh;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>