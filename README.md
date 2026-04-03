# SQLAgent 🤖

一个基于大语言模型的智能SQL查询代理系统，专为金融数据分析场景设计。通过自然语言理解技术，将业务问题转换为准确的SQL查询，让每个人都能轻松进行数据分析。

## 🌟 核心特性

- **🎯 智能SQL生成**：自然语言 → SQL查询，无需编写复杂SQL
- **🔧 模块化技能**：可扩展的业务知识系统，支持多领域分析
- **🧠 长期记忆**：个性化知识积累，越用越聪明
- **⚡ 流式响应**：实时交互，无需等待
- **🔐 企业级安全**：OAuth 2.0认证，数据隔离保护
- **🌐 多领域支持**：投资、营销、产品等金融业务全覆盖

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Redis 6.0+
- SQLite 3.0+


### 启动服务
```bash
# 启动Web服务
python web/server.py

# 或使用uvicorn直接启动
uvicorn web.server:app --host 0.0.0.0 --port 8023
```

访问：http://localhost:8023

## 📖 使用指南

### 1. 基础查询
```bash
curl -X POST http://localhost:8023/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "type": "sql",
    "question": "查询今年以来收益率最高的前5只基金"
  }'
```

### 2. 技能使用
系统内置多种业务技能：

- **投资组合分析**：基金收益率、资产配置查询
- **营销管理分析**：营销活动效果分析  
- **产品管理分析**：产品生命周期管理
- **绩效评估分析**：员工和部门绩效分析
- **外部信息分析**：市场数据和外部情报

### 3. 记忆功能
系统会自动保存有价值的查询：
- 成功的SQL查询示例
- 业务术语定义
- 业务规则说明
- 最佳实践案例

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   FastAPI       │    │   LLM Service   │
│   (Frontend)    │◄──►│   (API Layer)   │◄──►│   (AI Engine)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │   SQLAgent      │
                       │   Core Logic    │
                       └─────────────────┘
                                │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│   Skill System   │    │  Memory System  │    │  SQL Executor   │
│ (Business Logic) │    │  (Knowledge)    │    │  (Data Access)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 核心模块
- **[main.py](main.py)**：主入口，提供流式和本地模式
- **[web/server.py](web/server.py)**：FastAPI Web服务
- **[utils/SkillMiddleware.py](utils/SkillMiddleware.py)**：技能系统核心
- **[function/SQLExecutor.py](function/SQLExecutor.py)**：SQL执行器
- **[tools/tools.py](tools/tools.py)**：记忆和工具函数


### 技能开发规范
1. **渐进式披露**：保持技能内容简洁，按需加载
2. **模板化**：使用提供的模板确保格式一致
3. **测试验证**：充分测试技能功能
4. **文档完整**：提供清晰的使用说明


## 📊 性能优化

### 数据库优化
- 使用连接池管理数据库连接
- 为常用查询添加索引
- 实施查询超时控制
- 启用查询缓存

### 缓存策略
- Redis缓存热点数据
- 本地缓存常用技能
- 实施缓存失效策略
- 监控缓存命中率

### 异步优化
- 合理使用async/await
- 避免阻塞操作
- 优化并发度
- 监控异步任务状态

## 🧪 测试

### 测试结构
```
tests/
├── unit/                 # 单元测试
│   ├── test_api_request.py    # API请求测试
│   ├── test_llms.py           # LLM相关功能测试
│   └── test_tools.py          # 工具函数测试
├── integration/          # 集成测试
│   ├── test_api_integration.py # API集成测试
│   └── test_tool_integration.py # 工具集成测试
├── test_config.py        # 测试配置
└── __init__.py
```

### 运行测试
```
# 安装测试依赖
pip install pytest pytest-asyncio

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 运行所有测试
pytest tests/

# 生成覆盖率报告
pytest --cov=.
```

### 测试覆盖
- 核心功能测试覆盖 > 90%
- 边界条件测试
- 异常处理测试
- 性能基准测试

### 关键挑战：

* 需要加强测试和安全建设
* 性能优化空间较大
* 运维和监控体系待完善

