from app.models.basket import Basket
from app.models.basket_item import BasketItem
from app.models.course import UniqueCourse, OfferedCourse
from app.models.instructor import Instructor
from app.models.room import Room
from app.models.schedule import ScheduledClass
from app.models.schedule_history import ScheduleHistory
from app.models.term_course import TermCourse
from app.models.teaching_preference import TeachingPreference
from app.models.time_preference import TimePreference
from app.models.workflow import ScheduleWorkflow
from app.models.basket_item import BasketItem
from .unassigned_class import UnassignedClass

# ===== Student 360 domain models =====
from app.models.student360 import (
    Program,
    Curriculum,
    Student,
    AcademicStatus,
    Term,
    Enrollment,
    Grade,
    CourseRule,
    Regulation,
    ProcessGuide,
    CalendarEvent,
    NotificationChannel,
    Alert,
    CounselingRequest,
    Quiz,
    QuizQuestion,
    QuizAttempt,
    LearningContent,
    Conversation,
    AuditLog,
    DataDiscrepancyReport,
    CourseScenario,
    StaffUser,
    UnifiedUser,
)
# ===== Event Tracking (STU-EVT) =====
from app.models.event_log import StuEventLog

# ===== Interventions (Phase 2) =====
from app.models.intervention import StuIntervention

# ===== Adaptive Quiz (Phase 2) =====
from app.models.adaptive_quiz import StuAdaptiveAttempt, StuAdaptiveQuiz

# ===== Career Skills (Phase 2) =====
from app.models.skills import StuCourseSkill

# ===== Feedback Insights (Phase 2) =====
from app.models.feedback_insight import StuFeedbackInsight
from app.models.vote_poll import VotePoll
from app.models.course_vote import CourseVote
from app.models.course_proposal import CourseProposal
from app.models.course_rating import CourseRating

# ===== Permissions (Access Control) =====
from app.models.permission import SysPermission
