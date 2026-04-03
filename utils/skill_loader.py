import os
from typing import TypedDict, List


class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str  # Unique identifier for the skill
    description: str  # 1-2 sentence description to show in system prompt
    content: str  # Full skill content with detailed instructions

def load_skills_from_directory(skills_dir: str) -> List[Skill]:
    """
    从指定目录动态加载技能文档

    Args:
        skills_dir: 技能文档所在的目录路径

    Returns:
        List[Skill]: 技能列表
    """
    skills = []

    # 检查目录是否存在
    if not os.path.exists(skills_dir):
        print(f"警告: 技能目录 {skills_dir} 不存在")
        return skills

    # 遍历技能目录下的所有子目录
    for skill_folder in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_folder)

        # 确保是目录
        if os.path.isdir(skill_path):
            skill_md_path = os.path.join(skill_path, "SKILL.md")

            # 检查SKILL.md文件是否存在
            if os.path.exists(skill_md_path):
                try:
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 解析YAML头部信息
                    lines = content.split('\n')
                    name = skill_folder  # 默认使用文件夹名作为技能名
                    description = ""
                    content_start = 0

                    # 查找YAML头部
                    if lines[0].strip() == '---':
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() == '---':
                                content_start = i + 1
                                break
                            elif line.startswith('name:'):
                                # 修复：正确解析name字段值，去除引号
                                name_value = line[5:].strip()
                                if name_value.startswith('"') and name_value.endswith('"'):
                                    name = name_value[1:-1]
                                elif name_value.startswith("'") and name_value.endswith("'"):
                                    name = name_value[1:-1]
                                else:
                                    name = name_value
                            elif line.startswith('description:'):
                                # 修复：正确解析description字段值，去除引号
                                desc_value = line[12:].strip()
                                if desc_value.startswith('"') and desc_value.endswith('"'):
                                    description = desc_value[1:-1]
                                elif desc_value.startswith("'") and desc_value.endswith("'"):
                                    description = desc_value[1:-1]
                                else:
                                    description = desc_value
                        # 提取内容部分（去掉YAML头部）
                        skill_content = '\n'.join(lines[content_start:])
                    else:
                        # 没有YAML头部，使用整个文件内容
                        skill_content = content

                    # 如果没有从YAML获取描述，则使用文件夹名作为默认描述
                    if not description:
                        description = f"Skill for {name}"

                    skills.append({
                        "name": name,
                        "description": description,
                        "content": skill_content
                    })
                except Exception as e:
                    print(f"加载技能 {skill_folder} 时出错: {e}")
            else:
                print(f"警告: 技能目录 {skill_folder} 中未找到 SKILL.md 文件")

    return skills