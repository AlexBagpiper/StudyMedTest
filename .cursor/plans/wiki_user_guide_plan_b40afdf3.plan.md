---
name: Wiki User Guide Plan
overview: Создание комплексного Wiki-руководства на русском языке, охватывающего все роли пользователей, интерфейс фронтенда и детальную методологию оценки знаний (CV и LLM).
todos:
  - id: setup-wiki-structure
    content: Создать структуру папок docs/wiki/ и базовые файлы.
    status: completed
  - id: write-student-guide
    content: Написать 'Инструкцию для Студента' на основе UI и логики прохождения тестов.
    status: completed
  - id: write-teacher-guide
    content: Написать 'Инструкцию для Преподавателя' (создание контента, проверка).
    status: completed
  - id: write-admin-guide
    content: Написать 'Панель Администратора' (системные настройки, LLM/CV конфиги).
    status: completed
  - id: write-scoring-methodology
    content: Сформировать раздел 'Методология оценки' на основе актуального кода сервисов.
    status: completed
  - id: final-review-wiki
    content: Финальная вычитка и перекрестные ссылки между файлами Wiki.
    status: completed
---

Я подготовлю структуру Wiki, которая будет состоять из взаимосвязанных разделов. Каждый раздел будет описывать функционал через призму конкретной роли и подкрепляться техническим описанием логики расчетов.

### Структура Wiki

1. **[Главная (Введение)](docs/wiki/Home.md)**: Обзор MedTest Platform, ее назначение в медицинском образовании.
2. **[Роли и права доступа](docs/wiki/Roles.md)**: Матрица возможностей для Студента, Преподавателя и Администратора.
3. **[Инструкция для Студента](docs/wiki/StudentGuide.md)**:

    - Регистрация и личный кабинет.
    - Прохождение тестов: как работать с текстовыми ответами, тестами с выбором и инструментом графической аннотации (Canvas).
    - Интерпретация результатов: понимание баллов и фидбека от ИИ.

4. **[Инструкция для Преподавателя](docs/wiki/TeacherGuide.md)**:

    - Управление темами (Topics) и банком вопросов.
    - Создание тестов: настройка сложности, времени и выбор вопросов.
    - Проверка работ: просмотр ответов студентов и ручная корректировка (Review).

5. **[Панель Администратора](docs/wiki/AdminGuide.md)**:

    - Управление пользователями и модерация заявок преподавателей.
    - Настройка параметров ИИ-оценки (LLM Промпты, выбор провайдеров).
    - Настройка CV-метрик (веса IoU, точности и полноты).

6. **[Методология оценки (Технический раздел)](docs/wiki/ScoringMethodology.md)**:

    - Алгоритм взвешенной сложности (Difficulty 1-5).
    - Как работает CV-оценка: геометрия, IoU и сравнение с эталоном.
    - Как работает LLM-оценка: критерии (factual, completeness, terminology) и система fallback.

7. **[FAQ и Решение проблем](docs/wiki/FAQ.md)**: Ответы на частые вопросы заказчика.

### Ключевые файлы для анализа и актуализации:

- Бэкенд логика: [`backend/app/tasks/evaluation_tasks.py`](backend/app/tasks/evaluation_tasks.py)
- CV сервис: [`backend/app/services/cv_service.py`](backend/app/services/cv_service.py)
- LLM сервис: [`backend/app/services/llm_service.py`](backend/app/services/llm_service.py)
- Фронтенд роутинг: [`frontend/src/App.tsx`](frontend/src/App.tsx)
- Компонент аннотации: [`frontend/src/components/annotation/AnnotationEditor.tsx`](frontend/src/components/annotation/AnnotationEditor.tsx)