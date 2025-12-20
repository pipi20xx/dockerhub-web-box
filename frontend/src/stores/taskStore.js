import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTaskStore = defineStore('task', () => {
  const logs = ref([])
  const currentTaskId = ref(null)
  const isRunning = ref(false)
  let ws = null

  function startLogStream(taskId) {
    // 如果已有连接，先关闭它
    if (isRunning.value && ws) {
      ws.close()
    }
    
    logs.value = [] // 清空旧日志
    currentTaskId.value = taskId
    isRunning.value = true

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // 我们直接使用 window.location.host，因为它已经指向了我们的应用服务器
    // ✨ 核心修复：使用正确的后端API WebSocket路径
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/tasks/logs/${taskId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      logs.value.push('✅ WebSocket 连接成功，等待日志输出...');
    };

    ws.onmessage = (event) => {
      logs.value.push(event.data);
    };

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error);
      logs.value.push('❌ WebSocket 连接发生错误。请检查浏览器控制台获取详细信息。');
      isRunning.value = false;
    };

    ws.onclose = () => {
      // 只有在不是我们主动关闭时才显示 "连接已关闭"
      // 当我们启动新任务并关闭旧连接时，isRunning可能还是true，所以加个判断
      if (isRunning.value) {
        logs.value.push('🔌 WebSocket 连接已关闭。');
        isRunning.value = false;
      }
    };
  }

  return { logs, currentTaskId, isRunning, startLogStream }
})