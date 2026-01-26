"""
API v1 Router
"""

from fastapi import APIRouter

from app.api.v1 import auth, users, topics, questions, tests, submissions, analytics, admin, teacher_applications

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(topics.router, prefix="/topics", tags=["topics"])
router.include_router(questions.router, prefix="/questions", tags=["questions"])
router.include_router(tests.router, prefix="/tests", tags=["tests"])
router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(teacher_applications.router, prefix="/teacher-applications", tags=["teacher-applications"])

