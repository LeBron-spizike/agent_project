"""用户求职画像 schema."""

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户求职画像（onboarding 表单字段，全部可选，未填字段为空串）.

    存于 User.profile（JSON 列），同时以摘要写入 mem0 长期记忆，
    供 system prompt 结构化注入与语义检索两种方式实现个性化回答。
    """

    job_direction: str = Field(default="", description="求职方向", max_length=100)
    education: str = Field(default="", description="最高学历", max_length=50)
    major: str = Field(default="", description="专业", max_length=100)
    work_experience: str = Field(default="", description="工作年限", max_length=50)
    target_position: str = Field(default="", description="目标岗位", max_length=100)
    target_city: str = Field(default="", description="目标城市", max_length=100)
    target_salary: str = Field(default="", description="期望薪资", max_length=100)
    current_status: str = Field(default="", description="求职状态", max_length=50)
    key_skills: str = Field(default="", description="核心技能", max_length=300)
    career_goal: str = Field(default="", description="职业目标", max_length=300)

    def to_summary(self) -> str:
        """转成可注入 system prompt / mem0 的画像摘要文本（跳过空字段）."""
        fields = [
            ("求职方向", self.job_direction),
            ("学历", self.education),
            ("专业", self.major),
            ("工作年限", self.work_experience),
            ("目标岗位", self.target_position),
            ("目标城市", self.target_city),
            ("期望薪资", self.target_salary),
            ("求职状态", self.current_status),
            ("核心技能", self.key_skills),
            ("职业目标", self.career_goal),
        ]
        parts = [f"{label}={value.strip()}" for label, value in fields if value.strip()]
        return "求职画像：" + "；".join(parts) + "。" if parts else ""
