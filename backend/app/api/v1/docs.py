"""
Documentation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User, Role
from pathlib import Path
import os

router = APIRouter()

# Список доступных файлов для каждой роли
ROLE_DOCS = {
    Role.STUDENT: ["StudentGuide.md"],
    Role.TEACHER: ["TeacherGuide.md", "StudentGuide.md", "ScoringMethodology.md"],
    Role.ADMIN: ["Home.md", "AdminGuide.md", "TeacherGuide.md", "StudentGuide.md", "ScoringMethodology.md", "FAQ.md", "Roles.md"]
}

# Путь к Wiki-документации
# В Docker он будет /app/docs/wiki (parents[3]), локально - в корне проекта (parents[4])
def get_wiki_dir():
    # 1. Проверяем переменную окружения
    env_path = os.getenv("WIKI_DIR")
    if env_path:
        return Path(env_path)
    
    # 2. Пытаемся найти папку docs/wiki, поднимаясь вверх от текущего файла
    current = Path(__file__).resolve().parent
    for _ in range(5):
        potential_path = current / "docs" / "wiki"
        if potential_path.exists() and potential_path.is_dir():
            return potential_path
        current = current.parent
    
    # 3. Путь по умолчанию для Docker (/app/docs/wiki)
    docker_path = Path(__file__).resolve().parents[3] / "docs" / "wiki"
    if docker_path.exists():
        return docker_path
        
    # 4. Путь по умолчанию для локальной разработки
    return Path(__file__).resolve().parents[4] / "docs" / "wiki"

WIKI_DIR = get_wiki_dir()

@router.get("/list")
async def list_wiki_docs(
    current_user: User = Depends(get_current_user)
):
    """
    Список доступных документов для текущей роли
    """
    allowed_docs = ROLE_DOCS.get(current_user.role, [])
    
    # Проверяем реальное наличие файлов
    available_docs = []
    for doc in allowed_docs:
        file_path = WIKI_DIR / doc
        if file_path.exists():
            available_docs.append(doc)
            
    return {"documents": available_docs}

@router.get("/{filename}")
async def get_wiki_doc(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получение содержимого конкретного .md файла из Wiki
    """
    # Защита от выхода за пределы директории
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Проверка прав доступа к конкретному файлу
    allowed_docs = ROLE_DOCS.get(current_user.role, [])
    if filename not in allowed_docs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this document"
        )
    
    file_path = WIKI_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading document: {str(e)}"
        )
