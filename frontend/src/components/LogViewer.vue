<template>
    <div class="log-container">
        <pre class="log-output" ref="logOutputRef">{{ formattedLogs }}</pre>
    </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue' // 引入 nextTick
import { useTaskStore } from '@/stores/taskStore'

const taskStore = useTaskStore()
const logOutputRef = ref(null)

const formattedLogs = computed(() => {
    if (taskStore.logs.length === 0) {
        return '等待执行任务...'
    }
    return taskStore.logs.join('\n')
})

// 监听日志变化，自动滚动到底部
watch(() => taskStore.logs, () => {
    nextTick(() => {
        const el = logOutputRef.value
        if (el) {
            el.scrollTop = el.scrollHeight
        }
    })
}, { deep: true }) // 使用 deep watch 确保能监听到数组内部变化
</script>

<style scoped>
.log-container {
    /* ✨ 核心修改：使用 min-height 和 max-height */
    min-height: 400px;  /* 设置一个最小高度，与其他表格对齐 */
    max-height: 70vh; /* 设置一个最大高度，防止日志过多时页面过长 */
    height: auto;       /* 高度自适应 */
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    display: flex; /* 使用flex布局让pre占满容器 */
}
.log-output {
    flex-grow: 1; /* pre元素填满父容器 */
    overflow-y: auto;
    padding: 15px;
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Courier New', Courier, monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 0;
    font-size: 14px; /* 调整字体大小使其更紧凑 */
}
</style>