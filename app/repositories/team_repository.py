"""Team repository for database operations."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.repositories.base_repository import BaseRepository
from app.models.team import Team, TeamMember, TeamRole
from app.models.invitation import Invitation
from app.models.project import Project


class TeamRepository(BaseRepository[Team]):
    """Repository for Team model operations."""

    def __init__(self, db: Session):
        """
        Initialize TeamRepository.

        Args:
            db: Database session
        """
        super().__init__(Team, db)

    def get_by_name(self, name: str, exclude_id: Optional[int] = None) -> Optional[Team]:
        """
        Get team by name.

        Args:
            name: Team name
            exclude_id: Optional team ID to exclude from search

        Returns:
            Team or None if not found
        """
        query = self.db.query(Team).filter(Team.name == name)
        if exclude_id:
            query = query.filter(Team.id != exclude_id)
        return query.first()

    def get_user_teams(self, user_id: int) -> List[Team]:
        """
        Get all teams a user is a member of.

        Args:
            user_id: User ID

        Returns:
            List of teams
        """
        return (
            self.db.query(Team)
            .join(TeamMember)
            .filter(TeamMember.user_id == user_id)
            .all()
        )

    def get_user_team_ids(self, user_id: int) -> List[int]:
        """
        Get all team IDs a user is a member of.

        Args:
            user_id: User ID

        Returns:
            List of team IDs
        """
        return [
            team_id
            for (team_id,) in self.db.query(TeamMember.team_id)
            .filter(TeamMember.user_id == user_id)
            .distinct()
            .all()
        ]

    def count_members(self, team_id: int) -> int:
        """
        Count members in a team.

        Args:
            team_id: Team ID

        Returns:
            Number of members
        """
        return (
            self.db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team_id)
            .scalar()
        )

    def count_projects(self, team_id: int) -> int:
        """
        Count projects in a team.

        Args:
            team_id: Team ID

        Returns:
            Number of projects
        """
        return (
            self.db.query(func.count(Project.id))
            .filter(Project.team_id == team_id)
            .scalar()
        )

    def get_projects(self, team_id: int) -> List[Project]:
        """
        Get all projects for a team.

        Args:
            team_id: Team ID

        Returns:
            List of projects
        """
        return self.db.query(Project).filter(Project.team_id == team_id).all()


class TeamMemberRepository(BaseRepository[TeamMember]):
    """Repository for TeamMember model operations."""

    def __init__(self, db: Session):
        """
        Initialize TeamMemberRepository.

        Args:
            db: Database session
        """
        super().__init__(TeamMember, db)

    def get_by_team_and_user(
        self, team_id: int, user_id: int
    ) -> Optional[TeamMember]:
        """
        Get team member by team and user ID.

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            TeamMember or None if not found
        """
        return (
            self.db.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            .first()
        )

    def get_team_members(
        self, team_id: int, role: Optional[TeamRole] = None
    ) -> List[TeamMember]:
        """
        Get all members of a team, optionally filtered by role.

        Args:
            team_id: Team ID
            role: Optional role filter

        Returns:
            List of team members
        """
        query = self.db.query(TeamMember).filter(TeamMember.team_id == team_id)
        if role:
            query = query.filter(TeamMember.role == role)
        return query.all()

    def get_team_member_user_ids(self, team_id: int) -> List[int]:
        """
        Get all user IDs of team members.

        Args:
            team_id: Team ID

        Returns:
            List of user IDs
        """
        return [
            user_id
            for (user_id,) in self.db.query(TeamMember.user_id)
            .filter(TeamMember.team_id == team_id)
            .all()
        ]

    def is_member(self, team_id: int, user_id: int) -> bool:
        """
        Check if user is a member of the team.

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            True if user is a member, False otherwise
        """
        return self.get_by_team_and_user(team_id, user_id) is not None

    def has_role(
        self, team_id: int, user_id: int, required_roles: List[TeamRole]
    ) -> bool:
        """
        Check if user has one of the required roles in the team.

        Args:
            team_id: Team ID
            user_id: User ID
            required_roles: List of acceptable roles

        Returns:
            True if user has one of the required roles, False otherwise
        """
        member = self.get_by_team_and_user(team_id, user_id)
        return member is not None and member.role in required_roles

    def count_owners(self, team_id: int, exclude_user_id: Optional[int] = None) -> int:
        """
        Count number of owners in a team.

        Args:
            team_id: Team ID
            exclude_user_id: Optional user ID to exclude from count

        Returns:
            Number of owners
        """
        query = (
            self.db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team_id, TeamMember.role == TeamRole.OWNER)
        )
        if exclude_user_id:
            query = query.filter(TeamMember.user_id != exclude_user_id)
        return query.scalar()

    def delete_by_team_and_user(self, team_id: int, user_id: int) -> None:
        """
        Delete team member by team and user ID.

        Args:
            team_id: Team ID
            user_id: User ID
        """
        self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id, TeamMember.user_id == user_id
        ).delete()
        self.db.flush()


class InvitationRepository(BaseRepository[Invitation]):
    """Repository for Invitation model operations."""

    def __init__(self, db: Session):
        """
        Initialize InvitationRepository.

        Args:
            db: Database session
        """
        super().__init__(Invitation, db)

    def get_by_token(self, token: str) -> Optional[Invitation]:
        """
        Get invitation by token.

        Args:
            token: Invitation token

        Returns:
            Invitation or None if not found
        """
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_by_email_and_team(
        self, email: str, team_id: int, status: Optional[str] = None
    ) -> Optional[Invitation]:
        """
        Get invitation by email and team.

        Args:
            email: Invitation email
            team_id: Team ID
            status: Optional status filter

        Returns:
            Invitation or None if not found
        """
        query = self.db.query(Invitation).filter(
            Invitation.email == email, Invitation.team_id == team_id
        )
        if status:
            query = query.filter(Invitation.status == status)
        return query.first()

    def get_team_invitations(
        self, team_id: int, status: Optional[str] = None
    ) -> List[Invitation]:
        """
        Get all invitations for a team.

        Args:
            team_id: Team ID
            status: Optional status filter

        Returns:
            List of invitations
        """
        query = self.db.query(Invitation).filter(Invitation.team_id == team_id)
        if status:
            query = query.filter(Invitation.status == status)
        return query.all()

    def get_user_invitations(
        self, user_id: int, status: Optional[str] = None
    ) -> List[Invitation]:
        """
        Get all invitations for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of invitations
        """
        query = self.db.query(Invitation).filter(Invitation.invited_by_id == user_id)
        if status:
            query = query.filter(Invitation.status == status)
        return query.all()

    def delete_by_email_and_team(self, email: str, team_id: int) -> None:
        """
        Delete invitation by email and team.

        Args:
            email: Invitation email
            team_id: Team ID
        """
        self.db.query(Invitation).filter(
            Invitation.email == email, Invitation.team_id == team_id
        ).delete()
        self.db.flush()
