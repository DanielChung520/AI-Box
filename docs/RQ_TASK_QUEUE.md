# RQ 任务队列使用说明

## 📋 RQ 与 Redis 的关系

### ✅ RQ 使用现有的 Redis 服务

**重要说明**：
- **RQ 不是独立服务**，它是一个 Python 库
- **RQ 使用现有的 Redis 服务**来存储任务队列数据
- **不需要启动额外的 Redis 实例**
- RQ Worker 是独立进程，从 Redis 拉取任务并执行

### 架构图

```
FastAPI API Server
    ↓ (提交任务)
RQ Queue (Python 库)
    ↓ (存储任务)
Redis (现有服务) ← RQ Worker 进程（拉取任务）
    ↓ (执行任务)
Worker 执行任务函数
```

## 🔧 已创建的文件

1. **database/rq/queue.py** - RQ 队列客户端封装
2. **workers/tasks.py** - Worker 任务处理函数
3. **scripts/start_rq_worker.sh** - Worker 启动脚本

## 📊 队列定义

- `file_processing` - 文件处理队列（分块+向量化+图谱）
- `vectorization` - 向量化专用队列
- `kg_extraction` - 知识图谱提取专用队列

## 🚀 使用方法

### 1. 启动 RQ Worker

```bash
# 启动文件处理队列 Worker
./scripts/start_rq_worker.sh file_processing

# 启动向量化队列 Worker
./scripts/start_rq_worker.sh vectorization

# 启动图谱提取队列 Worker
./scripts/start_rq_worker.sh kg_extraction
```

### 2. 在代码中使用 RQ

```python
from database.rq.queue import get_task_queue, FILE_PROCESSING_QUEUE
from workers.tasks import process_file_chunking_and_vectorization_task

# 获取队列
queue = get_task_queue(FILE_PROCESSING_QUEUE)

# 提交任务
job = queue.enqueue(
    process_file_chunking_and_vectorization_task,
    file_id=file_id,
    file_path=file_path,
    file_type=file_type,
    user_id=user_id,
)
```

### 3. 监控任务状态

```python
# 检查任务状态
job = queue.fetch_job(job_id)
print(job.get_status())  # queued, started, finished, failed

# 获取任务结果
result = job.result
```

## 📝 下一步

需要修改以下文件，将 BackgroundTasks 替换为 RQ：

1. `api/routers/file_upload.py` - 文件上传处理
2. `api/routers/file_management.py` - 向量和图谱重新生成

## 🔍 监控和管理

### RQ Dashboard（可选）

```bash
# 启动 RQ Dashboard（Web 界面）
rq-dashboard --redis-url redis://localhost:6379/0
```

访问：http://localhost:9181

### 命令行工具

```bash
# 查看队列状态
rq info --url redis://localhost:6379/0

# 查看 Worker 状态
rq worker --url redis://localhost:6379/0
```

## ⚠️ 注意事项

1. **Redis 必须运行**：RQ 依赖 Redis，确保 Redis 服务正在运行
2. **Worker 进程**：需要单独启动 Worker 进程来处理任务
3. **任务序列化**：任务函数必须可以被 pickle 序列化
4. **异步函数**：异步函数需要在 Worker 中使用 `asyncio.run()` 或事件循环

## 📚 参考文档

- RQ 官方文档：https://python-rq.org/
- RQ Dashboard：https://github.com/nvie/rq-dashboard
