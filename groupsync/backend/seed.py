"""Create demo data: 1 teacher, 7 students, 1 project, 5 groups (2 on the teacher's dashboard), tasks, milestones.

Usage:  python seed.py          (refuses to run if demo data already exists)
        python seed.py --reset  (deletes the demo users/project first)
"""
import sys
from datetime import timedelta

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import (
    ActivityLog, Group, GroupMember, GroupStatus, Milestone, MilestoneStatus, Note, Project, Role, Task, TaskStatus,
    TeacherGroup, User,
)
from app.security import hash_password
from app.services.timeutil import utcnow

PASSWORD = "password123"
TEACHER_EMAIL = "teacher@groupsync.dev"
STUDENTS = ["Alice Reyes", "Ben Santos", "Carla Lim", "Diego Cruz", "Ella Tan", "Felix Go", "Gina Ong"]


# Fixed Group IDs so you can type them into the app
CODES = {
    "ocean": "GS-4K7P2Q",    # on the teacher's dashboard (healthy)
    "forest": "GS-R9TM3X",   # on the teacher's dashboard (stalled, uneven work, overdue tasks)
    "desert": "GS-W5HN8D",   # NOT linked yet: use this to try "Add Group" as the teacher
    "archived": "GS-A2B3C4", # archived: adding/joining is blocked
    "locked": "GS-D5E6F7",   # joining disabled: adding/joining is blocked
    "mountain": "GS-M8N6P3", # on the teacher's dashboard (no activity for 8 days -> "Inactive")
}


def student_email(i: int) -> str:
    return f"student{i}@groupsync.dev"


def reset(db) -> None:
    emails = [TEACHER_EMAIL] + [student_email(i) for i in range(1, len(STUDENTS) + 1)]
    users = list(db.scalars(select(User).where(User.email.in_(emails))))
    ids = [u.id for u in users]
    # Groups are no longer deleted with their project, so remove the demo groups explicitly
    linked = select(TeacherGroup.group_id).where(TeacherGroup.teacher_id.in_(ids))
    for g in db.scalars(select(Group).where(Group.created_by.in_(ids) | Group.id.in_(linked) | Group.group_code.in_(CODES.values()))):
        db.delete(g)  # their workspaces cascade
    db.flush()
    for p in db.scalars(select(Project).where(Project.teacher_id.in_(ids))):
        db.delete(p)
    db.flush()
    db.execute(delete(ActivityLog).where(ActivityLog.user_id.in_(ids)))
    for u in users:
        db.delete(u)
    db.commit()


def seed(db) -> None:
    now = utcnow()
    teacher = User(name="Ms. Rivera", email=TEACHER_EMAIL, password_hash=hash_password(PASSWORD), role=Role.teacher)
    students = [
        User(name=n, email=student_email(i + 1), password_hash=hash_password(PASSWORD), role=Role.student)
        for i, n in enumerate(STUDENTS)
    ]
    db.add_all([teacher, *students])
    db.flush()

    project = Project(
        teacher_id=teacher.id,
        title="Climate Change Research Presentation",
        description="Research one effect of climate change and present your findings to the class.",
        rubric="Research quality 40%\nPresentation clarity 30%\nTeamwork 30%",
        deadline=now + timedelta(days=21),
    )
    db.add(project)
    db.flush()

    def activity(group, user, action, text, ago):
        db.add(ActivityLog(group_id=group.id, user_id=user.id, action_type=action, description=text, created_at=now - ago))

    def task(group, title, status, assignee, due, creator, done_ago=None):
        t = Task(
            group_id=group.id, title=title, status=status, assignee_id=assignee.id if assignee else None,
            due_date=now + due if due is not None else None, created_by=creator.id,
            completed_at=now - done_ago if done_ago is not None else None,
        )
        db.add(t)
        return t

    # Group 1: healthy and active
    a, b, c, d, e, f, gina = students
    g1 = Group(project_id=project.id, name="Group 1 - Ocean Team", group_code=CODES["ocean"], created_by=a.id)
    # Group 2: active but unbalanced (one student did everything, overdue work) -> "Needs attention"
    g2 = Group(project_id=project.id, name="Group 2 - Forest Team", group_code=CODES["forest"], created_by=d.id)
    # Groups 3-5 are not on the teacher's dashboard; they exist to try Add Group and its error messages
    g3 = Group(name="Group 3 - Desert Team", group_code=CODES["desert"], created_by=gina.id)
    g4 = Group(name="Group 4 - Archived Team", group_code=CODES["archived"], created_by=gina.id, status=GroupStatus.archived)
    g5 = Group(name="Group 5 - Locked Team", group_code=CODES["locked"], created_by=gina.id, join_enabled=False)
    # Group 6: nothing for over a week -> "Inactive"
    g6 = Group(project_id=project.id, name="Group 6 - Mountain Team", group_code=CODES["mountain"], created_by=e.id)
    db.add_all([g1, g2, g3, g4, g5, g6])
    db.flush()
    for g, members in ((g1, [a, b, c]), (g2, [d, e, f]), (g3, [gina]), (g4, [gina]), (g5, [gina]), (g6, [e, f])):
        db.add_all([GroupMember(group_id=g.id, user_id=s.id) for s in members])
    db.add_all([TeacherGroup(teacher_id=teacher.id, group_id=g1.id), TeacherGroup(teacher_id=teacher.id, group_id=g2.id),
        TeacherGroup(teacher_id=teacher.id, group_id=g6.id),
    ])

    task(g1, "Research sea level data", TaskStatus.done, a, timedelta(days=-2), a, timedelta(days=2))
    task(g1, "Outline the presentation", TaskStatus.done, b, timedelta(days=-1), b, timedelta(days=1))
    task(g1, "Draft slides 1-5", TaskStatus.in_progress, b, timedelta(hours=20), a)  # due soon
    task(g1, "Find three credible sources", TaskStatus.in_progress, c, timedelta(days=3), a)
    task(g1, "Design charts", TaskStatus.todo, c, timedelta(days=5), b)
    task(g1, "Rehearse presentation", TaskStatus.todo, None, timedelta(days=12), a)

    task(g2, "Choose a forest region", TaskStatus.done, d, timedelta(days=-8), d, timedelta(days=9))
    task(g2, "Map the study area", TaskStatus.done, d, timedelta(days=-6), d, timedelta(days=7))
    task(g2, "Read two background articles", TaskStatus.done, d, timedelta(days=-5), d, timedelta(days=6))
    task(g2, "Collect deforestation statistics", TaskStatus.in_progress, e, timedelta(days=-3), d)  # overdue
    task(g2, "Interview a local expert", TaskStatus.todo, f, timedelta(days=-1), e)  # overdue
    task(g2, "Write the summary", TaskStatus.todo, d, timedelta(days=10), d)
    task(g2, "Build the slide deck", TaskStatus.todo, None, timedelta(days=14), e)

    db.add_all(
        [
            Milestone(group_id=g1.id, title="Outline", due_date=now - timedelta(days=1), status=MilestoneStatus.submitted),
            Milestone(group_id=g1.id, title="Draft", due_date=now + timedelta(days=7), status=MilestoneStatus.pending),
            Milestone(group_id=g1.id, title="Final", due_date=now + timedelta(days=18), status=MilestoneStatus.pending),
            Milestone(group_id=g2.id, title="Outline", due_date=now - timedelta(days=4), status=MilestoneStatus.pending),
            Milestone(group_id=g2.id, title="Draft", due_date=now + timedelta(days=8), status=MilestoneStatus.pending),
            Milestone(group_id=g2.id, title="Final", due_date=now + timedelta(days=19), status=MilestoneStatus.pending),
        ]
    )
    db.add(Note(group_id=g1.id, author_id=a.id, content="Useful dataset: https://sealevel.nasa.gov", created_at=now - timedelta(hours=5)))

    db.add(Note(group_id=g2.id, author_id=d.id, content="Region idea: Amazon basin", created_at=now - timedelta(days=8)))
    db.add(Note(group_id=g2.id, author_id=d.id, content="Sources so far: FAO and Global Forest Watch", created_at=now - timedelta(days=6)))
    activity(g1, a, "task_created", "Alice Reyes created task 'Research sea level data'", timedelta(days=4))
    activity(g1, a, "task_completed", "Alice Reyes completed task 'Research sea level data'", timedelta(days=2))
    activity(g1, b, "task_completed", "Ben Santos completed task 'Outline the presentation'", timedelta(days=1))
    activity(g1, a, "note_added", "Alice Reyes added a note", timedelta(hours=5))
    activity(g2, d, "task_created", "Diego Cruz created task 'Choose a forest region'", timedelta(days=10))
    activity(g2, d, "task_completed", "Diego Cruz completed task 'Choose a forest region'", timedelta(days=9))
    activity(g2, d, "task_completed", "Diego Cruz completed task 'Read two background articles'", timedelta(days=1))
    task(g6, "Pick a mountain range", TaskStatus.done, e, timedelta(days=-9), e, timedelta(days=9))
    task(g6, "Compare glacier photos", TaskStatus.todo, f, timedelta(days=4), e)
    activity(g6, e, "task_completed", "Ella Tan completed task 'Pick a mountain range'", timedelta(days=8))
    db.commit()


def main() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == TEACHER_EMAIL)):
            if "--reset" not in sys.argv:
                sys.exit("Demo data already exists. Run `python seed.py --reset` to recreate it.")
            reset(db)
        seed(db)
    finally:
        db.close()
    print("Seeded demo data. All accounts use password:", PASSWORD)
    print("  Teacher:", TEACHER_EMAIL)
    print("Group IDs:")
    for key, label in (
        ("ocean", "on the teacher's dashboard"), ("forest", "on the teacher's dashboard"),
        ("mountain", "on the teacher's dashboard"), ("desert", "free: try Add Group with this one"), ("archived", "archived: blocked"), ("locked", "joining disabled: blocked"),
    ):
        print(f"  {CODES[key]}  {key:9} ({label})")
    for i, n in enumerate(STUDENTS, 1):
        print(f"  Student {i}: {student_email(i)}  ({n})")


if __name__ == "__main__":
    main()
