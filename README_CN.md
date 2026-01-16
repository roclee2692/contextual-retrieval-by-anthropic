# 龙子湖食堂 RAG 系统 - 完整测试流程

## 📋 任务目标

完成上下文检索（Contextual Retrieval）vs 普通 RAG 的 A/B 对比测试：
- ✅ 配置 WSL Linux 上的 Ollama (gemma2:12b)
- ✅ 建立向量数据库和 BM25 索引
- ✅ 启动 FastAPI 服务
- ✅ 使用 20 个测试问题进行 A/B 对比
- ✅ 生成测试报告

## 🚀 快速开始

### 步骤 0: 准备 WSL Ollama

在 WSL (Linux) 终端中：

```bash
# 启动 Ollama 服务
ollama serve

# 如果还没下载模型，在另一个 WSL 终端运行:
ollama pull gemma2:12b

# 验证服务运行
curl http://localhost:11434/api/tags
```

### 步骤 1: 配置 Windows 环境

在 Windows PowerShell 中（项目目录）：

```powershell
# 使用快速启动脚本
.\start.ps1

# 或手动安装依赖
pip install -r requirements.txt
```

### 步骤 2: 测试 Ollama 连接

```powershell
python test_ollama_connection.py
```

如果连接失败：
1. 确认 WSL 的 `ollama serve` 正在运行
2. 检查 `.env` 文件中的 `OLLAMA_BASE_URL`
3. Windows 11/10 最新版本可以使用 `http://localhost:11434`
4. 或者获取 WSL IP: `wsl hostname -I`，然后使用 `http://WSL_IP:11434`

### 步骤 3: 创建数据库（首次运行）

```powershell
python create_save_db.py
```

这将：
- 读取 `./data` 目录的 PDF 文件
- 为每个文本块生成上下文（使用 gemma2:12b）
- 创建 ChromaDB 向量数据库
- 创建 BM25 关键词索引

⏱️ **预计耗时**: 5-30 分钟（取决于文档大小）

### 步骤 4: 启动 API 服务

在**新的** PowerShell 终端：

```powershell
python app.py
```

API 地址: http://127.0.0.1:8000

### 步骤 5: 测试 API（可选）

在**另一个新的** PowerShell 终端：

```powershell
# 方式 1: 使用测试脚本
python test_api.py

# 方式 2: 使用 curl
curl -X POST http://127.0.0.1:8000/rag-chat -H "Content-Type: application/json" -d "{\"query\":\"龙子湖校区有几个食堂？\"}"
```

### 步骤 6: 运行 A/B 对比测试

```powershell
# 完整测试 (20 个问题，使用现有数据库)
python test_ab_simple.py

# 快速测试 (前 5 个问题)
python test_ab_simple.py 5

# 完整重建测试 (重新创建索引，耗时长)
python test_ab_comparison.py
```

### 步骤 7: 查看结果

测试完成后会生成：
- `ab_test_results_YYYYMMDD_HHMMSS.json` - 详细数据
- `ab_test_report_YYYYMMDD_HHMMSS.txt` - 可读报告

### 步骤 8: 启动 Web UI（可选）

```powershell
streamlit run main.py
```

浏览器访问: http://localhost:8501

---

## 🧠 进阶：知识图谱构建（可选）

### 什么是知识图谱？

知识图谱通过**实体-关系-实体**的三元组结构，实现：
- ✅ 关系推理（多跳查询）
- ✅ 实体关联发现
- ✅ 结构化知识表示

### 快速构建

```powershell
# 创建知识图谱（15-40分钟）
python create_knowledge_graph.py

# 测试图谱查询
python create_knowledge_graph.py test
```

### 知识图谱示例

**三元组结构**:
```
(一号餐厅, 包含窗口, 19号我爱我粥)
(19号我爱我粥, 提供, 小米南瓜粥)
(小米南瓜粥, 价格, 2元)
```

**查询能力**:
- "一号餐厅有哪些2元的食品？" → 多跳关系查询
- "最便宜的粥在哪个窗口？" → 价格比较 + 归属查找

详细说明: 查看 `knowledge_graph_guide.md`

---

## 📁 项目文件说明

### 核心文件
- `create_save_db.py` - 创建数据库（带上下文增强）
- `create_knowledge_graph.py` - **创建知识图谱（进阶）**
- `app.py` - FastAPI 后端服务
- `main.py` - Streamlit 前端界面
- `.env` - 环境配置文件

### 测试文件（新增）
- `test_ollama_connection.py` - **测试 WSL Ollama 连接**
- `test_ab_simple.py` - **简化版 A/B 测试（推荐）**
- `test_ab_comparison.py` - 完整版 A/B 测试（重建索引）
- `test_api.py` - API 接口测试
- `start.ps1` - PowerShell 快速启动脚本
- `TEST_GUIDE.md` - 详细测试指南
- `knowledge_graph_guide.md` - **知识图谱构建指南**

### 数据文件
- `data/NCWU_Longzihu_Canteens_CR_Prefixed.pdf` - 龙子湖食堂资料（带上下文）
- `data/NCWU_Longzihu_Canteens_RAG_Chunked.pdf` - 龙子湖食堂资料（分块）

## 🧪 20 个测试问题

```
1. 龙子湖校区有几个食堂？
2. 哪个食堂最便宜？
3. 哪个食堂的菜品种类最多？
4. 食堂的营业时间是什么时候？
5. 早餐有什么推荐的？
6. 哪里可以吃到面食？
7. 哪个食堂的环境最好？
8. 有清真餐厅吗？
9. 晚上宵夜哪里可以吃？
10. 哪个食堂离教学楼最近？
11. 食堂可以用支付宝吗？
12. 哪里有麻辣烫？
13. 食堂的米饭多少钱？
14. 哪个食堂人最少？
15. 有没有水果店？
16. 食堂二楼有什么特色？
17. 周末食堂开门吗？
18. 哪里可以吃到炒菜？
19. 食堂有WiFi吗？
20. 学生推荐去哪个食堂？
```

## 🔧 环境配置文件 (.env)

```env
DATA_DIR="./data"
SAVE_DIR="./src/db"
VECTOR_DB_PATH="./src/db/canteen_db_vectordb"
BM25_DB_PATH="./src/db/canteen_db_bm25"
COLLECTION_NAME="ncwu_canteen_collection"
API_URL="http://127.0.0.1:8000/rag-chat"
OLLAMA_BASE_URL="http://localhost:11434"
```

## 🎯 A/B 测试对比

### 方法 A: 向量检索（Vector Only）
- 仅使用语义向量检索
- 基于文本相似度匹配

### 方法 B: 混合检索（Hybrid: Vector + BM25）
- 结合向量检索和 BM25 关键词检索
- 提高召回率和准确性

### 预期观察
- 响应时间对比
- 答案准确性对比
- 上下文相关性对比

## ❓ 常见问题

### Q1: 无法连接 Ollama

**错误**: `Connection refused` 或 `timeout`

**解决**:
```bash
# 在 WSL 中检查 Ollama 是否运行
ps aux | grep ollama

# 重启 Ollama
pkill ollama
ollama serve

# 允许外部访问（如果需要）
ollama serve --host 0.0.0.0
```

### Q2: 模型未找到

**错误**: `model 'gemma2:12b' not found`

**解决**:
```bash
# 在 WSL 中下载模型
ollama pull gemma2:12b

# 查看已下载的模型
ollama list
```

### Q3: 内存不足

**问题**: gemma2:12b 占用内存较大（约 8GB）

**解决**:
1. 确保系统有足够内存（建议 16GB+）
2. 关闭其他大型应用
3. 或使用更小的模型：
   ```bash
   # 在代码中改为
   model="gemma2:2b"  # 约 2GB
   ```

### Q4: ChromaDB 错误

**错误**: `PersistentClient error`

**解决**:
```powershell
# 删除旧数据库重试
Remove-Item -Recurse -Force .\src\db\*
python create_save_db.py
```

### Q5: Windows 无法访问 WSL localhost

**解决**:
```powershell
# 方法 1: 更新 Windows（推荐）
# Windows 11 和最新 Windows 10 支持直接访问

# 方法 2: 使用 WSL IP
wsl hostname -I
# 在 .env 中设置: OLLAMA_BASE_URL="http://WSL_IP:11434"

# 方法 3: 端口转发
netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=WSL_IP
```

## 📊 测试结果示例

```
测试总结
================================================================================

总问题数: 20
方法 A 成功: 20/20
方法 B 成功: 20/20

方法 A (向量检索):
  - 平均响应时间: 3.45s
  - 最快: 2.10s
  - 最慢: 5.20s

方法 B (混合检索):
  - 平均响应时间: 3.89s
  - 最快: 2.35s
  - 最慢: 5.80s
```

## 🎓 技术栈

- **LLM**: Ollama (gemma2:12b) - 本地运行在 WSL
- **Embedding**: BAAI/bge-small-zh-v1.5 - 中文语义向量
- **Vector DB**: ChromaDB - 向量存储
- **Keyword Search**: BM25 - 关键词检索
- **Knowledge Graph**: LlamaIndex KnowledgeGraphIndex - 知识图谱推理（可选）
- **Framework**: LlamaIndex - RAG 框架
- **Backend**: FastAPI - API 服务
- **Frontend**: Streamlit - Web UI

## 📝 修改记录

### 已优化配置
1. ✅ 添加 `OLLAMA_BASE_URL` 环境变量支持
2. ✅ 修正模型名称为 `gemma2:12b`
3. ✅ 增加请求超时时间为 120s
4. ✅ 创建 WSL 连接测试脚本
5. ✅ 创建简化版 A/B 测试脚本
6. ✅ 创建 PowerShell 启动脚本
7. ✅ 添加中文 Embedding 模型支持

## 🔗 相关资源

- [Anthropic Contextual Retrieval Blog](https://www.anthropic.com/news/contextual-retrieval)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [Ollama Documentation](https://ollama.ai/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

## 📧 联系方式

原项目作者:
- GitHub: [@RionDsilvaCS](https://github.com/RionDsilvaCS)
- LinkedIn: [Rion Dsilva](https://www.linkedin.com/in/rion-dsilva-043464229/)

---

**祝测试顺利！如有问题请查看 `TEST_GUIDE.md` 获取详细说明。**

