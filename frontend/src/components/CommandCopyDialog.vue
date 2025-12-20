<template>
  <el-dialog
    :model-value="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    title="复制构建命令"
    width="70vw"
  >
    <p style="margin-top: 0;">由于浏览器安全限制，自动复制失败。请手动复制以下命令：</p>
    <div class="command-container">
      <pre ref="commandTextRef">{{ commandText }}</pre>
      <el-button @click="fallbackCopy" type="primary" size="small" class="copy-button">复制</el-button>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:modelValue', false)" size="small">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps({
  modelValue: Boolean, // v-model
  commandText: String,
});

defineEmits(['update:modelValue']);

const commandTextRef = ref(null);

// 使用已废弃但兼容性极佳的后备方案
const fallbackCopy = () => {
  if (commandTextRef.value) {
    const textarea = document.createElement('textarea');
    textarea.value = props.commandText;
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      ElMessage.success('命令已复制到剪贴板！');
    } catch (err) {
      ElMessage.error('复制失败，请手动选择并复制。');
    }
    document.body.removeChild(textarea);
  }
};
</script>

<style scoped>
.command-container {
  position: relative;
  background-color: #1e1e1e;
  color: #d4d4d4;
  border-radius: 4px;
  padding: 15px;
}
pre {
  font-family: 'Courier New', Courier, monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-size: 14px;
}
.copy-button {
  position: absolute;
  top: 10px;
  right: 10px;
}
</style>