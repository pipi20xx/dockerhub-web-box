import { ref } from 'vue';

export function useSimulatedProgress() {
  const percentage = ref(0);
  const status = ref(''); // '', 'success', 'exception'
  const isVisible = ref(false);
  let timer = null;

  const start = () => {
    percentage.value = 0;
    status.value = '';
    isVisible.value = true;
    
    if (timer) clearInterval(timer);
    
    timer = setInterval(() => {
      // Fast at first, then slower, capping at 95%
      if (percentage.value < 50) {
        percentage.value += Math.random() * 5;
      } else if (percentage.value < 80) {
        percentage.value += Math.random() * 2;
      } else if (percentage.value < 99) {
        percentage.value += 0.1;
      }
      
      if (percentage.value > 99) percentage.value = 99;
      
      // Keep it strictly formatted if needed, but number is fine for el-progress
      percentage.value = Math.min(Number(percentage.value.toFixed(1)), 99);
    }, 200);
  };

  const finish = () => {
    if (timer) clearInterval(timer);
    percentage.value = 100;
    status.value = 'success';
  };

  const fail = () => {
    if (timer) clearInterval(timer);
    status.value = 'exception';
  };

  const close = () => {
    if (timer) clearInterval(timer);
    isVisible.value = false;
    percentage.value = 0;
    status.value = '';
  };

  return {
    percentage,
    status,
    isVisible,
    start,
    finish,
    fail,
    close
  };
}
