<template>
  <el-dialog
    v-model="visible"
    title="备份管理与恢复"
    width="70%"
    @open="fetchBackups"
  >
    <div v-loading="loading">
       <div style="margin-bottom: 10px; display: flex; justify-content: flex-end;">
         <el-button 
            v-if="backups.length > 0" 
            type="danger" 
            plain 
            size="small" 
            @click="clearAllBackups"
         >
           清空所有备份
         </el-button>
       </div>
       <el-table :data="backups" style="width: 100%">
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="remark" label="备注" width="180" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" :formatter="formatDate" />
          <el-table-column prop="size" label="大小" :formatter="formatSize" />
          <el-table-column label="操作">
            <template #default="scope">
               <el-button type="primary" size="small" @click="confirmRestore(scope.row)">恢复</el-button>
               <el-button type="danger" size="small" @click="deleteBackup(scope.row)">删除</el-button>
            </template>
          </el-table-column>
       </el-table>
       <div v-if="backups.length === 0" style="text-align: center; margin-top: 20px; color: #999;">
         暂无备份
       </div>
    </div>
    
    <!-- Restore Strategy Dialog -->
    <el-dialog
      v-model="restoreDialogVisible"
      title="确认恢复策略"
      width="40%"
      append-to-body
    >
      <p>正在恢复: {{ selectedBackup?.filename }}</p>
      <div style="margin: 20px 0;">
        <el-alert
          title="警告：恢复操作将修改项目文件"
          type="warning"
          show-icon
          :closable="false"
          style="margin-bottom: 10px;"
        />
        <p>请选择恢复策略：</p>
        <el-radio-group v-model="restoreStrategy" style="display: flex; flex-direction: column; align-items: flex-start;">
           <el-radio label="overwrite" style="height: auto; margin-bottom: 10px;">
             <div>
                 <strong>单纯覆盖 (Overwrite)</strong>
                 <div style="font-size: 12px; color: #666; line-height: 1.2;">解压文件覆盖现有文件。现有文件中如果备份里没有，则保留。</div>
             </div>
           </el-radio>
           <el-radio label="clear_and_overwrite" style="height: auto;">
             <div>
                 <strong>清空再覆盖 (Clear and Overwrite)</strong>
                 <div style="font-size: 12px; color: #666; line-height: 1.2;">先清空项目构建目录下的所有内容，然后解压备份。确保与备份完全一致。</div>
             </div>
           </el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="restoring" @click="executeRestore">执行恢复</el-button>
      </template>
    </el-dialog>
    
    <OperationProgressDialog 
        :visible="restoreProgress.isVisible.value"
        :percentage="restoreProgress.percentage.value"
        :status="restoreProgress.status.value"
        title="正在恢复项目"
        @close="restoreProgress.close()"
    />
  </el-dialog>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue';
import apiClient from '@/services/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import OperationProgressDialog from './OperationProgressDialog.vue';
import { useSimulatedProgress } from '@/composables/useSimulatedProgress';

const props = defineProps({
  modelValue: Boolean,
  projectId: String,
  projectName: String
});

const emit = defineEmits(['update:modelValue']);

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const backups = ref([]);
const loading = ref(false);

const restoreDialogVisible = ref(false);
const selectedBackup = ref(null);
const restoreStrategy = ref('overwrite');
const restoring = ref(false);

// Restore Progress
const restoreProgress = useSimulatedProgress();

const fetchBackups = async () => {
  if (!props.projectId) return;
  loading.value = true;
  try {
    const res = await apiClient.get(`/backups/${props.projectId}`);
    backups.value = res.data;
  } catch (error) {
    ElMessage.error('获取备份列表失败');
  } finally {
    loading.value = false;
  }
};

const formatDate = (row, column, cellValue) => {
  return new Date(cellValue).toLocaleString();
};

const formatSize = (row, column, cellValue) => {
  if (cellValue < 1024) return cellValue + ' B';
  if (cellValue < 1024 * 1024) return (cellValue / 1024).toFixed(2) + ' KB';
  if (cellValue < 1024 * 1024 * 1024) return (cellValue / (1024 * 1024)).toFixed(2) + ' MB';
  return (cellValue / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
};

const deleteBackup = async (backup) => {
  try {
    await ElMessageBox.confirm(`确定要删除备份 ${backup.filename} 吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    await apiClient.delete(`/backups/${props.projectId}/${backup.filename}`);
    ElMessage.success('删除成功');
    fetchBackups();
  } catch (e) {
    // Cancelled or error
    if (e !== 'cancel') ElMessage.error('删除失败');
  }
};

const clearAllBackups = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除项目 "${props.projectName}" 的所有备份文件吗？该操作不可恢复。`, '清空所有备份', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    });
    loading.value = true;
    await apiClient.delete(`/backups/${props.projectId}/clear_all`);
    ElMessage.success('所有备份已清空');
    await fetchBackups();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('清空失败');
  } finally {
    loading.value = false;
  }
};

const confirmRestore = (backup) => {
  selectedBackup.value = backup;
  restoreStrategy.value = 'overwrite';
  restoreDialogVisible.value = true;
};

const executeRestore = async () => {
  if (!selectedBackup.value) return;
  
  restoreDialogVisible.value = false; // Close strategy dialog
  restoreProgress.start(); // Start progress dialog

  try {
    await apiClient.post(`/backups/${props.projectId}/restore`, {
      backup_filename: selectedBackup.value.filename,
      strategy: restoreStrategy.value
    });
    restoreProgress.finish();
    // Do not auto-close
  } catch (error) {
    restoreProgress.fail();
    // Do not auto-close
    ElMessage.error(`恢复失败: ${error.response?.data?.detail || error.message}`);
  }
};
</script>

