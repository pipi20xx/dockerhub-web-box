<template>
  <el-dialog
    v-model="visible"
    title="备份配置"
    width="40%"
    :close-on-click-modal="false"
  >
    <div style="margin-bottom: 20px;">
      <el-alert
        title="设置文件过滤规则"
        type="info"
        description="指定要从备份中排除的文件或文件夹名称（支持通配符 *）。每一行一个规则。"
        show-icon
        :closable="false"
      />
    </div>

    <el-form label-position="top">
        <el-form-item label="备注 (可选)">
             <el-input 
                v-model="remark" 
                placeholder="例如：修改配置前的备份"
                maxlength="50"
                show-word-limit
             />
        </el-form-item>
        <el-form-item label="忽略模式 (glob patterns)">
            <el-input
                v-model="patternsStr"
                type="textarea"
                :rows="8"
                placeholder="例如:
node_modules
.git
*.log
dist"
            />
        </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirm">开始备份</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue';

const props = defineProps({
  modelValue: Boolean,
  initialPatterns: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'confirm']);

const visible = ref(false);
const patternsStr = ref('');
const remark = ref('');

// 默认全局规则
const DEFAULT_PATTERNS = [
    "venv",
    ".env",
    "__pycache__",
    "*.pyc",
    ".git",
    "node_modules",
    "target",
    ".vscode",
    ".idea",
    "dist",
    "build",
    "*.log"
].join('\n');

watch(() => props.modelValue, (val) => {
  visible.value = val;
  if (val) {
      // 如果项目还没有设置过规则，则显示默认推荐规则
      // 否则显示项目已有的规则
      patternsStr.value = props.initialPatterns || DEFAULT_PATTERNS;
      remark.value = ''; // Reset remark
  }
});

watch(visible, (val) => {
  emit('update:modelValue', val);
});

const handleConfirm = () => {
    // Split by newline and filter empty lines
    const patterns = patternsStr.value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    emit('confirm', { patterns, remark: remark.value });
    visible.value = false;
};
</script>
