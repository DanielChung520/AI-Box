// 檢查前端 localStorage 中的文件記錄
console.log('='.repeat(60));
console.log('檢查前端 localStorage 中的文件記錄');
console.log('='.repeat(60));

// 檢查任務
const taskListKey = 'ai-box-tasks';
const taskListData = localStorage.getItem(taskListKey);
if (taskListData) {
  const taskList = JSON.parse(taskListData);
  console.log(`\n找到 ${taskList.length} 個任務`);

  taskList.forEach(taskId => {
    const taskKey = `ai-box-task-${taskId}`;
    const taskData = localStorage.getItem(taskKey);
    if (taskData) {
      const task = JSON.parse(taskData);
      console.log(`\n📁 任務 ID: ${taskId}`);
      console.log(`   標題: ${task.title}`);
      console.log(`   fileTree 文件數量: ${task.fileTree?.length || 0}`);
      if (task.fileTree && task.fileTree.length > 0) {
        task.fileTree.forEach((file, index) => {
          console.log(`     ${index + 1}. ${file.name} (ID: ${file.id})`);
        });
      }
    }
  });
} else {
  console.log('\n⚠️  沒有找到任務列表');
}

// 檢查模擬文件
console.log('\n' + '='.repeat(60));
console.log('檢查模擬文件存儲：');
console.log('='.repeat(60));

let fileCount = 0;
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key && key.startsWith('ai-box-mock-files-')) {
    const taskId = key.replace('ai-box-mock-files-', '');
    const fileData = localStorage.getItem(key);
    if (fileData) {
      const files = JSON.parse(fileData);
      console.log(`\n📁 任務 ID: ${taskId}`);
      console.log(`   模擬文件數量: ${files.length}`);
      files.forEach((file, index) => {
        console.log(`     ${index + 1}. ${file.filename}`);
        console.log(`        - 文件ID (file_id): ${file.file_id}`);
        console.log(`        - 任務ID: ${file.task_id}`);
        console.log(`        - 用戶ID: ${file.user_id || 'N/A'}`);
        fileCount++;
      });
    }
  }
}

if (fileCount === 0) {
  console.log('\n⚠️  沒有找到模擬文件記錄');
}

console.log('\n' + '='.repeat(60));
console.log(`總結: 找到 ${fileCount} 個模擬文件記錄`);
console.log('='.repeat(60));
