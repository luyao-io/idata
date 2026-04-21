from langgraph.types import Command
from langchain.messages import ToolMessage
import glob
from function.SQLExecutor import run_sql
from langchain.tools import tool, ToolRuntime
import os
from utils.skill_loader import load_skills_from_directory
from config import load_config
from tools.filesystem import read_file, write_file, edit_file, list_directory

# 加载配置
config = load_config()

MEMORY_PATH = "./longtermmemory"


# Create SQL execution tool
@tool
async def execute_sql(query: str, domain: str, runtime: ToolRuntime, ) -> str:
    """Execute SQL query against the database to get actual data.
    
    Use this tool when you need to retrieve data from the database using SQL.
    
    Args:
        query (str): The SQL query to execute (required)
        domain (str,required): The business domain or vertical.
                 Optional values: investment-portfolio-analysis, marketing-management-analysis, 
                 external-information-analysis, performance-evaluation-analysis, product-management-analysis.
    Returns:
        pd.DataFrame: 查询结果的数据框，默认返回50条数据，除非特殊说明
    """
    # Check if the required skill has been loaded
    skills_loaded = runtime.state.get("skills_loaded", [])

    if domain not in skills_loaded:
        return (
            f"Error: You must load the '{domain}' skill first "
            f"to understand the database schema before writing queries. "
            f"Use load_skill('{domain}') to load the schema."
        )

    # Check if query is provided
    if not query:
        return "Error: SQL query is required."

    try:
        import pandas as pd
        from config.context import request_user
        from utils.verticaModule import VerticaDatabase

        credentials_file = config.verticadb.credentials_file
        user_account = pd.read_csv(credentials_file, sep=',', encoding='utf-8')

        user_id = request_user.get()
        user_row = user_account[user_account['user'] == user_id]

        if not user_row.empty:
            passwd = user_row['password'].values[0]
            # 使用自定义用户名和密码创建数据库连接
            db = VerticaDatabase(user=user_id, password=passwd)
            df = await db.execute_query(query)
        else:
            df = await run_sql(query)

        # Convert the result to a string representation
        if df.empty:
            return "查询结果：无数据"

        # Return the dataframe as a string
        return f"{df.to_markdown(index=False)}\n"
    except Exception as e:
        return f"Error executing query: {str(e)}"


@tool
async def load_skill(skill_name: str, runtime: ToolRuntime) -> Command:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name(str,required): The name of the skill to load
                 Optional values: investment-portfolio-analysis, marketing-management-analysis,
                 external-information-analysis, performance-evaluation-analysis, product-management-analysis.

    """
    from config.context import request_user
    
    # Find and return the requested skill
    SKILLS_DIR = os.path.join(os.path.dirname(__file__), "../skills")
    
    # 获取当前用户ID
    try:
        user_id = request_user.get()
    except:
        user_id = "default"

    # 加载公共技能
    SKILLS = load_skills_from_directory(SKILLS_DIR)
    
    # 加载用户私有技能
    USER_SKILLS_DIR = os.path.join(os.path.dirname(__file__), f"../longtermmemory/users/{user_id}/skills")
    if os.path.exists(USER_SKILLS_DIR):
        USER_SKILLS = load_skills_from_directory(USER_SKILLS_DIR)
        # 合并技能列表，用户私有技能优先
        skills_dict = {skill["name"]: skill for skill in SKILLS}
        for user_skill in USER_SKILLS:
            skills_dict[user_skill["name"]] = user_skill
        SKILLS = list(skills_dict.values())
        
    for skill in SKILLS:
        if skill["name"] == skill_name:
            skill_content = f"{skill['content']}"

            # Update state to track loaded skill
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=skill_content,
                            tool_call_id=runtime.tool_call_id,
                        )
                    ],
                    "skills_loaded": [skill_name],
                }
            )
    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Skill '{skill_name}' not found. Available skills: {available}",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        }
    )


# ====== 2. TOOL：搜索Memory（核心） ======
@tool
async def search_memory(query: str, domain: str ) -> str:
    """
    从用户私有memory中检索知识：
    - 词汇映射
    - 业务规则
    - 历史SQL查询
    - 最佳实践

    Args:
        query (str): 搜索关键词或查询语句
        domain (str, optional): The business domain or vertical.
                 Optional values: investment-portfolio-analysis, marketing-management-analysis,
                 external-information-analysis, performance-evaluation-analysis, product-management-analysis.

    Returns:
        str: 搜索结果，包含匹配的记忆内容
    """
    import re
    from pathlib import Path
    from config.context import request_user

    # 获取当前用户ID
    try:
        user_id = request_user.get()
    except:
        user_id = "default"
    
    results = []
    query_lower = query.lower()

    # 搜索terms（使用模糊匹配）
    # 只搜索用户私有内容
    user_terms_path = Path(MEMORY_PATH) / "users" / user_id / "terms"
    
    term_files = []
    if user_terms_path.exists():
        term_files.extend(user_terms_path.glob("*.md"))
        
    for f in term_files:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            # 使用更灵活的匹配策略
            if query_lower in content.lower() or any(word in content.lower() for word in query_lower.split()):
                results.append(f"### 用户私有业务术语: {f.name}\n{content}")

    # 搜索rules（按领域过滤）
    # 只搜索用户私有内容
    user_rules_path = Path(MEMORY_PATH) / "users" / user_id / "rules"
    
    rule_files = []
    if user_rules_path.exists():
        rule_files.extend(user_rules_path.glob("*.md"))

    for f in rule_files:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            # 如果指定了领域，优先匹配领域相关的规则
            if domain != "general" and domain in str(f):
                score = 2  # 高权重
            elif query_lower in content.lower():
                score = 1  # 中等权重
            elif any(word in content.lower() for word in query_lower.split()):
                score = 0.5  # 低权重
            else:
                score = 0

            if score > 0:
                results.append(f"### 用户私有业务规则: {f.name}\n{content}")

    # 搜索queries（Top-K，按相关性排序）
    # 只搜索用户私有内容
    user_queries_path = Path(MEMORY_PATH) / "users" / user_id / "queries"

    
    query_files = []
    if user_queries_path.exists():
        # 使用rglob递归搜索所有子目录中的.md文件，同时也包括当前目录的文件
        query_files.extend(list(user_queries_path.rglob("*.md")))

        
    scored_queries = []
    for f in query_files:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            # 计算相关性分数
            score = 0
            if query_lower in content.lower():
                score += 2
            if domain != "general" and domain in str(f):
                score += 1
            # 检查关键词匹配
            score += sum(1 for word in query_lower.split() if word in content.lower())

            if score > 0:
                scored_queries.append((score, f"### 用户私有SQL示例: {f.name}\n{content}"))

    # 按分数降序排列，取前3个
    scored_queries.sort(key=lambda x: x[0], reverse=True)
    for _, content in scored_queries[:3]:
        results.append(content)

    # 限制结果数量并返回
    return "\n\n".join(results[:5]) if results else f"未找到与'{query}'相关的用户私有记忆内容"




# ====== 3. TOOL：写入Memory ======
@tool
async def write_memory(query: str, sql: str, domain: str = "general", memory_type: str = "query") -> str:
    """
    将知识写入用户私有memory：
    - SQL查询示例
    - 业务术语
    - 业务规则
    - 最佳实践
    Args:
        query (str): 用户的原始查询语句或知识点描述
        sql (str): 对应的SQL执行语句或知识点内容
        domain (str, optional): The business domain or vertical.
                 Optional values: investment-portfolio-analysis, marketing-management-analysis,
                 external-information-analysis, performance-evaluation-analysis, product-management-analysis.

    Returns:
        str: 执行结果信息，成功返回写入确认信息，失败返回错误信息
    """
    from pathlib import Path
    import os
    from datetime import datetime
    from utils.llms import get_tool_llm, with_llm_semaphore
    import asyncio
    from config.context import request_user
    import re

    # 获取当前用户ID
    try:
        user_id = request_user.get()
    except:
        user_id = "default"

    # 验证domain是否为有效的技能领域
    valid_domains = []
    skills_path = "skills"
    if os.path.exists(skills_path):
        valid_domains = [d for d in os.listdir(skills_path) if os.path.isdir(os.path.join(skills_path, d))]
    # 添加general作为有效领域
    valid_domains.append("general")

    if domain not in valid_domains:
        return f"写入失败: 无效的domain '{domain}'。有效值为: {', '.join(valid_domains)}"

    try:
        # 根据记忆类型选择存储路径 - 默认写入用户私有目录
        base_path = Path(MEMORY_PATH) / "users" / user_id
        
        # 确保用户目录存在
        os.makedirs(base_path, exist_ok=True)

        # 使用模板路径
        template_path = Path("./longtermmemory/templates")
        
        # 只创建一次LLM实例
        llm = get_tool_llm("Qwen2.5-72B-Instruct", streaming=False)


        # 读取对应类型的模板
        if memory_type == "term":
            template_file = template_path / "term_template.md"
            with open(template_file, "r", encoding="utf-8") as f:
                template_content = f.read()
            term_name = query.strip().replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_")[
                        :50].lower()
            if not term_name:
                term_name = f"term_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # 保存到用户私有目录
            filename = base_path / "terms" / f"{term_name}.md"
            os.makedirs(base_path / "terms", exist_ok=True)

            # 使用LLM智能生成术语内容
            prompt = f"""请根据以下信息生成一个结构化的业务术语文档：

用户查询: {query}
详细信息: {sql}
业务领域: {domain}
规则模板：{template_content}
请按照术语模板的结构，生成详细的术语定义。

请直接返回格式化的术语文档内容，不要添加额外的说明。
"""

        elif memory_type == "rule":
            template_file = template_path / "rule_template.md"
            rule_name = query.strip().replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_")[
                        :50].lower()
            if not rule_name:
                rule_name = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # 保存到用户私有目录
            filename = base_path / "rules" / f"{rule_name}.md"
            os.makedirs(base_path / "rules", exist_ok=True)
            with open(template_file, "r", encoding="utf-8") as f:
                template_content = f.read()
            # 使用LLM智能生成规则内容
            prompt = f"""请根据以下信息生成一个结构化的业务规则文档：

规则名称: {query}
规则详情: {sql}
业务领域: {domain}
规则模板：{template_content}
请按照规则模板的结构，生成详细的业务规则，包括：
请直接返回格式化的规则文档内容，不要添加额外的说明。
"""

        elif memory_type in ["query", "practice"]:
            template_file = template_path / "query_template.md"
            with open(template_file, "r", encoding="utf-8") as f:
                template_content = f.read()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            date_folder = datetime.now().strftime('%Y-%m-%d')
            if memory_type == "practice":
                practice_name = query.strip().replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_")[
                            :50].lower()
                if not practice_name:
                    practice_name = f"practice_{timestamp}"
                # 保存到用户私有目录
                filename = base_path / "practices" / date_folder / f"{practice_name}.md"
                os.makedirs(base_path / "practices" / date_folder, exist_ok=True)
            else:  # query
                # 保存到用户私有目录
                filename = base_path / "queries" / date_folder / f"query_{timestamp}.md"
                os.makedirs(base_path / "queries" / date_folder, exist_ok=True)

            # 使用LLM智能生成查询内容
            prompt = f"""请根据以下信息生成一个结构化的SQL查询文档：

用户查询: {query}
SQL语句: {sql}
业务领域: {domain}
查询模板: {template_content}

请按照查询模板的结构，生成详细的查询文档，

请直接返回格式化的查询文档内容，不要添加额外的说明。
"""

            # 使用LLM生成内容
            llm_response = await llm.ainvoke(prompt)
            generated_content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # 写入文件
            with open(filename, "w", encoding="utf-8") as f:
                f.write(generated_content)
            
            return f"memory写入成功: {filename}"

        # 对于term和rule类型，使用模板并生成内容
        if memory_type in ["term", "rule"]:
            # 读取模板
            with open(template_file, "r", encoding="utf-8") as f:
                template_content = f.read()

            # 使用LLM生成内容
            prompt_content = prompt
            llm_response = await llm.ainvoke(prompt_content)
            generated_content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            # 使用LLM根据模板和用户输入填充模板
            fill_prompt = f"""你是一个专业的文档编写助手。请根据以下信息，使用指定模板来生成结构化的文档。

模板:
{template_content}

用户查询: {query}
详细信息: {sql}
业务领域: {domain}

请严格按照模板格式，将用户信息填充到模板中对应的位置，生成完整的文档。不要添加模板中没有的额外内容，也不要遗漏模板中的任何部分。

请直接返回填充完成的文档内容，不要添加任何额外说明或格式。
"""

            llm = get_tool_llm("Qwen2.5-72B-Instruct", streaming=False)
            fill_response = await llm.ainvoke(fill_prompt)
            final_content = fill_response.content if hasattr(fill_response, 'content') else str(fill_response)

            # 写入文件
            with open(filename, "w", encoding="utf-8") as f:
                f.write(final_content)

            return f"memory写入成功: {filename}"

        # 对于query和practice类型，使用模板并生成内容
        if memory_type in ["query", "practice"]:
            # 读取模板
            with open(template_file, "r", encoding="utf-8") as f:
                template_content = f.read()

            # 使用LLM生成内容
            prompt_content = prompt
            llm_response = await llm.ainvoke(prompt_content)
            generated_content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            # 使用LLM根据模板和用户输入填充模板
            fill_prompt = f"""你是一个专业的文档编写助手。请根据以下信息，使用指定模板来生成结构化的文档。

模板:
{template_content}

用户信息:
用户查询: {query}
SQL语句: {sql}
业务领域: {domain}

请严格按照模板格式，将用户信息填充到模板中对应的位置，生成完整的文档。不要添加模板中没有的额外内容，也不要遗漏模板中的任何部分。

请直接返回填充完成的文档内容，不要添加任何额外说明或格式。
"""

            llm = get_tool_llm("Qwen2.5-72B-Instruct", streaming=False)
            fill_response = await llm.ainvoke(fill_prompt)
            final_content = fill_response.content if hasattr(fill_response, 'content') else str(fill_response)

            # 写入文件
            with open(filename, "w", encoding="utf-8") as f:
                f.write(final_content)

            return f"memory写入成功: {filename}"
    except Exception as e:
        return f"写入失败: {str(e)}"