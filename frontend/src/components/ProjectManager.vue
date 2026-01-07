<template>
  <div class="project-manager">
    <div class="header-controls">
      <h2>项目管理</h2>
      <div> <!-- ✨ 新增div用于包裹按钮 -->
        <el-button type="info" plain @click="handleExport">导出全量配置</el-button>
        <el-button type="warning" plain @click="triggerImport">导入配置</el-button>
        <el-button type="danger" plain @click="handleClearAllLogs">清理所有日志</el-button>
        <el-button type="primary" @click="openAddDialog">添加新项目</el-button>
        
        <!-- Hidden file input for import -->
        <input 
            type="file" 
            ref="fileInputRef" 
            style="display: none;" 
            accept=".json" 
            @change="handleImport"
        >
      </div>
    </div>

    <el-table :data="projectStore.projects" v-loading="projectStore.isLoading" style="width: 100%">
      <el-table-column prop="name" label="项目名称" width="200" />
      <el-table-column prop="repo_image_name" label="目标镜像">
          <template #default="scope">
              {{ scope.row.registry_url }}/{{ scope.row.repo_image_name }}
          </template>
      </el-table-column>
      <el-table-column prop="build_context" label="构建路径" width="300" />
      
      <el-table-column label="操作" width="700">
        <template #default="scope">
          <div class="actions-cell">
            <el-input v-model="scope.row.tag" size="small" style="width: 120px;" placeholder="Tag(s), 支持 | 或逗号" />
            <el-button size="small" type="success" @click="handleBuild(scope.row)">构建&推送</el-button>
            <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button size="small" type="primary" plain @click="handleBackup(scope.row)">备份</el-button>
            <el-button size="small" @click="openBackupManager(scope.row)">恢复</el-button>
            <el-button size="small" type="info" plain @click="handleClone(scope.row)">克隆</el-button>
            <el-button size="small" type="info" @click="openHistoryDialog(scope.row)">历史日志</el-button>
            <el-button size="small" type="warning" plain @click="openCopyDialog(scope.row)">复制命令</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑项目 Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑项目' : '添加新项目'" width="60%" @close="resetForm">
      <el-form ref="projectFormRef" :model="currentProject" :rules="rules" label-width="140px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="currentProject.name" />
        </el-form-item>
        <el-form-item label="构建上下文路径" prop="build_context">
          <el-input v-model="currentProject.build_context" placeholder="例如: /path/to/your/project" />
        </el-form-item>
        <el-form-item label="Dockerfile路径" prop="dockerfile_path">
          <el-input v-model="currentProject.dockerfile_path" placeholder="相对于构建上下文的路径, 例如: Dockerfile" />
        </el-form-item>
        <el-form-item label="本地镜像名 (可选)" prop="local_image_name">
          <el-input v-model="currentProject.local_image_name" placeholder="构建时在本地使用的名称 (留空则直推远程)" />
        </el-form-item>
        <el-form-item label="仓库地址" prop="registry_url">
          <el-input v-model="currentProject.registry_url" placeholder="例如: registry.cn-hangzhou.aliyuncs.com" />
        </el-form-item>
        <el-form-item label="仓库镜像名" prop="repo_image_name">
          <el-input v-model="currentProject.repo_image_name" placeholder="例如: my-namespace/my-app" />
        </el-form-item>
        <el-form-item label="使用凭证">
            <el-select v-model="currentProject.credential_id" placeholder="选择凭证" clearable style="width: 100%;">
              <el-option label="无" :value="null" />
              <el-option
                v-for="cred in credentialStore.credentials"
                :key="cred.id"
                :label="`${cred.name} (${cred.username})`"
                :value="cred.id"
              />
            </el-select>
        </el-form-item>
        <el-form-item label="使用代理">
            <el-select v-model="currentProject.proxy_id" placeholder="选择代理" clearable style="width: 100%;">
              <el-option label="无" :value="null" />
              <el-option
                v-for="proxy in proxyStore.proxies"
                :key="proxy.id"
                :label="`${proxy.name} (${proxy.url})`"
                :value="proxy.id"
              />
            </el-select>
        </el-form-item>
        <el-form-item label="无缓存构建">
          <el-switch v-model="currentProject.no_cache" />
        </el-form-item>
        <el-form-item label="构建后清理">
          <el-switch v-model="currentProject.auto_cleanup" />
          <span style="margin-left: 10px; font-size: 12px; color: #909399;">成功推送后自动删除本地镜像标签</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <CommandCopyDialog v-model="commandCopyDialogVisible" :command-text="commandToCopy" />
    <HistoryLogDialog v-model="historyLogDialogVisible" :project-id="historyProjectId" />
    <BackupManagerDialog v-model="backupManagerVisible" :project-id="backupProjectId" :project-name="backupProjectName" />
    <BackupOptionsDialog 
        v-model="backupOptionsVisible" 
        :initial-patterns="currentBackupProject?.backup_ignore_patterns"
        @confirm="confirmBackup"
    />
    <OperationProgressDialog 
        :visible="backupProgress.isVisible.value"
        :percentage="backupProgress.percentage.value"
        :status="backupProgress.status.value"
        title="正在创建备份"
        @close="backupProgress.close()"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useProjectStore } from '@/stores/projectStore';
import { useCredentialStore } from '@/stores/credentialStore';
import { useProxyStore } from '@/stores/proxyStore';
import { useTaskStore } from '@/stores/taskStore';
import { ElMessage, ElMessageBox } from 'element-plus';
import apiClient from '@/services/api';
import CommandCopyDialog from './CommandCopyDialog.vue';
import HistoryLogDialog from './HistoryLogDialog.vue';
import BackupManagerDialog from './BackupManagerDialog.vue';
import OperationProgressDialog from './OperationProgressDialog.vue';
import BackupOptionsDialog from './BackupOptionsDialog.vue';
import { useSimulatedProgress } from '@/composables/useSimulatedProgress';

const projectStore = useProjectStore();
const credentialStore = useCredentialStore();
const proxyStore = useProxyStore();
const taskStore = useTaskStore();

const dialogVisible = ref(false);
const isEditing = ref(false);
const commandCopyDialogVisible = ref(false);
const historyLogDialogVisible = ref(false);
const backupManagerVisible = ref(false);
const backupOptionsVisible = ref(false);
const backupProjectId = ref(null);
const backupProjectName = ref('');
const currentBackupProject = ref(null);

// Backup Progress
const backupProgress = useSimulatedProgress();

const projectFormRef = ref(null);
const fileInputRef = ref(null); // Ref for file input
const initialProjectState = {
  name: '',
  build_context: '',
  dockerfile_path: 'Dockerfile',
  local_image_name: '',
  registry_url: '',
  repo_image_name: '',
  no_cache: false,
  auto_cleanup: true,
  credential_id: null,
  proxy_id: null,
};
const currentProject = ref({ ...initialProjectState });
const historyProjectId = ref(null);
const commandToCopy = ref('');

const rules = reactive({
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  build_context: [{ required: true, message: '请输入构建上下文的绝对路径', trigger: 'blur' }],
  dockerfile_path: [{ required: true, message: '请输入Dockerfile的相对路径', trigger: 'blur' }],
  local_image_name: [{ required: false, message: '请输入本地镜像名', trigger: 'blur' }],
  registry_url: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }],
  repo_image_name: [{ required: true, message: '请输入仓库镜像名', trigger: 'blur' }],
});

onMounted(() => {
  projectStore.fetchProjects();
  credentialStore.fetchCredentials();
  proxyStore.fetchProxies();
});

const resetForm = () => {
    currentProject.value = { ...initialProjectState };
    if(projectFormRef.value) {
        projectFormRef.value.resetFields();
    }
}

const openAddDialog = () => {
  resetForm();
  isEditing.value = false;
  dialogVisible.value = true;
};

const openEditDialog = (project) => {
  isEditing.value = true;
  currentProject.value = { ...project };
  dialogVisible.value = true;
};

const handleSave = async () => {
  if (!projectFormRef.value) return;
  await projectFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const dataToSend = { ...currentProject.value };
        delete dataToSend.tag;

        if (isEditing.value) {
          await apiClient.put(`/projects/${dataToSend.id}`, dataToSend);
          ElMessage.success('项目更新成功！');
        } else {
          await apiClient.post('/projects/', dataToSend);
          ElMessage.success('项目添加成功！');
        }
        dialogVisible.value = false;
        await projectStore.fetchProjects();
      } catch (error) {
        ElMessage.error(`操作失败: ${error.response?.data?.detail || error.message}`);
      }
    } else {
      ElMessage.error('请检查表单输入是否正确');
      return false;
    }
  });
};

const handleDelete = (project) => {
  ElMessageBox.confirm(`确定要永久删除项目 "${project.name}" 吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await apiClient.delete(`/projects/${project.id}`);
      ElMessage.success('删除成功！');
      await projectStore.fetchProjects();
    } catch (error) {
      ElMessage.error(`删除失败: ${error.response?.data?.detail || error.message}`);
    }
  });
};

const emit = defineEmits(['switch-tab']);

const handleBuild = async (project) => {
    if (!project.tag || project.tag.trim() === '') {
        ElMessage.warning('请输入要构建的镜像标签 (Tag)');
        return;
    }
    const taskId = await projectStore.startBuildTask(project.id, project.tag);
    if(taskId) {
        taskStore.startLogStream(taskId);
        // ✨ 修改：不再打开弹窗，而是切换到“执行日志”选项卡
        emit('switch-tab', 'logs');
    }
};

const openCopyDialog = (project) => {
    const tagInput = project.tag || 'latest';
    // 支持英文逗号、中文逗号、竖线分割
    const tags = tagInput.split(/[,，|]/).map(t => t.trim()).filter(t => t);
    const repoBase = `${project.registry_url}/${project.repo_image_name}`;
    
    let commands = [];
    const primaryFullImage = `${repoBase}:${tags[0]}`;
    
    // 构建命令 (直接构建主标签)
    commands.push(`# 1. 构建主标签\ndocker build -t ${primaryFullImage} -f ${project.dockerfile_path} ${project.build_context}`);
    
    // 额外标签命令
    if (tags.length > 1) {
        commands.push(`\n# 2. 打额外标签`);
        for (let i = 1; i < tags.length; i++) {
            commands.push(`docker tag ${primaryFullImage} ${repoBase}:${tags[i]}`);
        }
    }

    // 推送命令
    commands.push(`\n# 3. 推送所有标签`);
    tags.forEach(t => {
        commands.push(`docker push ${repoBase}:${t}`);
    });

    commandToCopy.value = commands.join('\n');
    commandCopyDialogVisible.value = true;
};

const openHistoryDialog = (project) => {
    historyProjectId.value = project.id;
    historyLogDialogVisible.value = true;
};

const handleBackup = (project) => {
    currentBackupProject.value = project;
    backupOptionsVisible.value = true;
};

const confirmBackup = async ({ patterns, remark }) => {
    if (!currentBackupProject.value) return;
    
    const projectId = currentBackupProject.value.id;
    backupProgress.start();
    try {
        await apiClient.post(`/backups/${projectId}`, {
            ignore_patterns: patterns,
            remark: remark
        });
        ElMessage.success('备份成功');
        backupProgress.finish();
    } catch (error) {
        console.error('Backup failed:', error);
        ElMessage.error('备份失败: ' + (error.response?.data?.detail || error.message));
        backupProgress.fail();
    }
};

const handleClone = async (project) => {
  try {
    await ElMessageBox.confirm(`确定要克隆项目 "${project.name}" 吗？`, '项目克隆', {
      confirmButtonText: '确定克隆',
      cancelButtonText: '取消',
      type: 'info',
    });
    await apiClient.post(`/projects/${project.id}/copy`);
    ElMessage.success('项目克隆成功！');
    await projectStore.fetchProjects();
  } catch (error) {
    if (error !== 'cancel') {
        ElMessage.error(`克隆失败: ${error.response?.data?.detail || error.message}`);
    }
  }
};

const openBackupManager = (project) => {
    backupProjectId.value = project.id;
    backupProjectName.value = project.name;
    backupManagerVisible.value = true;
};

// ✨ --- 新增：清理所有日志的函数 --- ✨
const handleClearAllLogs = () => {
  ElMessageBox.confirm(
    '此操作将永久删除所有项目的历史任务记录和对应的日志文件，且无法恢复。确定要继续吗？',
    '严重警告',
    {
      confirmButtonText: '确定清理',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await apiClient.delete('/tasks/logs/clear_all');
      ElMessage.success('所有历史日志已清理完毕');
    } catch (error) {
      ElMessage.error(`清理失败: ${error.response?.data?.detail || error.message}`);
    }
  });
};

const handleExport = async () => {
  try {
    const res = await apiClient.get('/projects/all/export');
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res.data, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `docker-pusher-config-${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
    ElMessage.success('配置导出成功');
  } catch (error) {
    ElMessage.error('导出失败');
  }
};

const triggerImport = () => {
  fileInputRef.value.click();
};

const handleImport = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const json = JSON.parse(e.target.result);
      await ElMessageBox.confirm('导入配置将合并现有数据（同名项目/凭证将被覆盖），确定要继续吗？', '导入确认', {
        confirmButtonText: '确定导入',
        cancelButtonText: '取消',
        type: 'warning'
      });
      
      await apiClient.post('/projects/all/import', json);
      ElMessage.success('配置导入成功');
      // Refresh all stores
      await projectStore.fetchProjects();
      await credentialStore.fetchCredentials();
      await proxyStore.fetchProxies();
      
      // Clear file input
      event.target.value = '';
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error(`导入失败: ${error.message}`);
      }
      event.target.value = '';
    }
  };
  reader.readAsText(file);
};


</script>

<style scoped>
.project-manager {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.actions-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>