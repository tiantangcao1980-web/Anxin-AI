"""
团队管理服务
"""

from typing import Any, cast

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.firm_management import Team, TeamMember
from src.models.user import User


class TeamService:
    """团队管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_teams(self, org_id: str) -> list[dict[str, Any]]:
        """获取组织下所有团队（含成员数）"""
        # 子查询：每个团队的成员数
        member_count_sq = (
            select(
                TeamMember.team_id,
                func.count(TeamMember.id).label("member_count"),
            )
            .group_by(TeamMember.team_id)
            .subquery()
        )

        stmt = (
            select(Team, member_count_sq.c.member_count)
            .outerjoin(member_count_sq, Team.id == member_count_sq.c.team_id)
            .where(Team.org_id == org_id)
            .order_by(Team.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        teams: list[dict[str, Any]] = []
        for team, count in rows:
            d = team.to_dict()
            d["member_count"] = count or 0
            d["leader_name"] = "待指定"

            if team.leader_id:
                leader_result = await self.db.execute(
                    select(User).where(User.id == team.leader_id)
                )
                leader = leader_result.scalar_one_or_none()
                if leader:
                    d["leader_name"] = leader.name

            member_stmt = (
                select(TeamMember, User)
                .join(User, TeamMember.user_id == User.id)
                .where(TeamMember.team_id == team.id)
                .order_by(TeamMember.role.desc(), TeamMember.created_at)
            )
            member_rows = (await self.db.execute(member_stmt)).all()
            d["members"] = [
                {
                    "id": member.user_id,
                    "user_id": member.user_id,
                    "name": user.name,
                    "user_name": user.name,
                    "role": member.role,
                    "avatar_url": user.avatar_url,
                    "title": user.department or "",
                }
                for member, user in member_rows
            ]
            teams.append(d)
        return teams

    async def create_team(
        self,
        org_id: str,
        name: str,
        description: str | None = None,
        leader_id: str | None = None,
    ) -> dict[str, Any]:
        """创建团队"""
        team = Team(
            org_id=org_id,
            name=name,
            description=description,
            leader_id=leader_id,
        )
        self.db.add(team)
        await self.db.flush()

        # 如果指定了负责人，自动添加为成员
        if leader_id:
            member = TeamMember(team_id=team.id, user_id=leader_id, role="leader")
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(team)
        logger.info(f"创建团队: {team.id} - {name}")
        return team.to_dict()

    async def update_team(self, team_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """更新团队信息"""
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team:
            return None

        for key, value in data.items():
            if hasattr(team, key) and key not in ("id", "org_id", "created_at", "updated_at"):
                setattr(team, key, value)

        await self.db.commit()
        await self.db.refresh(team)
        return team.to_dict()

    async def delete_team(self, team_id: str) -> bool:
        """删除团队（级联删除成员关系）"""
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team:
            return False

        await self.db.delete(team)
        await self.db.commit()
        logger.info(f"删除团队: {team_id}")
        return True

    async def add_member(self, team_id: str, user_id: str, role: str = "member") -> dict[str, Any]:
        """添加团队成员"""
        member = TeamMember(team_id=team_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member.to_dict()

    async def remove_member(self, team_id: str, user_id: str) -> bool:
        """移除团队成员"""
        stmt = delete(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        deleted_count = cast(Any, result).rowcount
        return bool(deleted_count > 0)

    async def list_members(self, team_id: str) -> list[dict[str, Any]]:
        """获取团队成员列表"""
        stmt = (
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.role.desc(), TeamMember.created_at)
        )
        result = await self.db.execute(stmt)
        members = result.scalars().all()
        return [m.to_dict() for m in members]
