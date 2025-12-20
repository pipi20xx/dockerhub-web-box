<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="30%"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    align-center
  >
    <div class="progress-container">
      <el-progress 
        type="circle" 
        :percentage="percentage" 
        :status="status" 
      />
      <p class="status-text">{{ statusText }}</p>
    </div>

    <template #footer>
        <div v-if="status === 'success' || status === 'exception'" style="text-align: center;">
            <el-button type="primary" @click="$emit('close')">关闭窗口</el-button>
        </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, defineProps, defineEmits } from 'vue';

const props = defineProps({
  visible: Boolean,
  title: {
    type: String,
    default: '处理中'
  },
  percentage: {
    type: Number,
    default: 0
  },
  status: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['close']);

const statusText = computed(() => {
  if (props.status === 'success') return '操作成功!';
  if (props.status === 'exception') return '操作失败!';
  if (props.percentage >= 99) return '正在最后处理...';
  return '正在进行中...';
});
</script>

<style scoped>
.progress-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
}
.status-text {
  margin-top: 20px;
  font-size: 16px;
  font-weight: 500;
}
</style>