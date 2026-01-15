import React, { createContext, useContext, useState, useCallback } from 'react'

export type Locale = 'ru' | 'en'

// Переводы
const translations = {
  ru: {
    // Роли
    'role.admin': 'Администратор',
    'role.teacher': 'Преподаватель',
    'role.student': 'Студент',
    
    // Навигация
    'nav.dashboard': 'Главная',
    'nav.tests': 'Тесты',
    'nav.questions': 'Вопросы',
    'nav.submissions': 'Результаты',
    'nav.profile': 'Профиль',
    'nav.logout': 'Выйти',
    'nav.admin': 'Админ-панель',
    'nav.topics': 'Темы',
    
    // Авторизация
    'auth.login': 'Войти',
    'auth.register': 'Зарегистрироваться',
    'auth.email': 'Email',
    'auth.password': 'Пароль',
    'auth.lastName': 'Фамилия',
    'auth.firstName': 'Имя',
    'auth.middleName': 'Отчество',
    'auth.noAccount': 'Нет аккаунта?',
    'auth.hasAccount': 'Уже есть аккаунт?',
    'auth.loading': 'Загрузка...',
    'auth.registering': 'Регистрация...',
    'auth.passwordMin': 'Минимум 6 символов',
    'auth.enterLastName': 'Введите фамилию',
    'auth.enterFirstName': 'Введите имя',
    'auth.invalidCredentials': 'Неверный email или пароль',
    'auth.userNotFound': 'Пользователь не найден',
    'auth.accountInactive': 'Аккаунт деактивирован',
    'auth.loginError': 'Ошибка входа. Проверьте данные.',
    'auth.networkError': 'Ошибка сети. Сервер недоступен.',
    
    // Профиль
    'profile.title': 'Профиль',
    'profile.edit': 'Редактировать профиль',
    'profile.save': 'Сохранить',
    'profile.cancel': 'Отмена',
    'profile.changePassword': 'Изменить пароль',
    'profile.currentPassword': 'Текущий пароль',
    'profile.newPassword': 'Новый пароль',
    'profile.confirmPassword': 'Подтвердите пароль',
    'profile.passwordMismatch': 'Пароли не совпадают',
    'profile.saved': 'Профиль сохранён',
    'profile.passwordChanged': 'Пароль изменён',
    'profile.editDescription': 'Здесь вы можете изменить свои данные',
    'profile.emailReadonly': 'Email нельзя изменить',
    'profile.changeEmail': 'Изменить email',
    'profile.newEmail': 'Новый email',
    'profile.sendCode': 'Отправить код',
    'profile.enterCode': 'Введите код из письма',
    'profile.codeSent': 'Код отправлен на',
    'profile.confirmCode': 'Подтвердить',
    'profile.emailChanged': 'Email успешно изменён',
    'profile.codeExpired': 'Код истёк, запросите новый',
    'profile.invalidCode': 'Неверный код',
    'profile.emailAlreadyRegistered': 'Этот email уже зарегистрирован',
    'profile.noPendingRequest': 'Нет активного запроса на смену email',
    
    // Dashboard
    'dashboard.welcome.admin': 'Добро пожаловать, администратор!',
    'dashboard.welcome.teacher': 'Добро пожаловать, преподаватель!',
    'dashboard.welcome.student': 'Добро пожаловать, студент!',
    'dashboard.welcome.default': 'Добро пожаловать!',
    'dashboard.availableTests': 'Доступные тесты',
    'dashboard.takeTest': 'Пройдите новый тест',
    'dashboard.myResults': 'Мои результаты',
    'dashboard.viewResults': 'Просмотрите ваши результаты',
    'dashboard.createTest': 'Создать тест',
    'dashboard.createTestDesc': 'Создайте новый тест для студентов',
    'dashboard.createQuestion': 'Создать вопрос',
    'dashboard.createQuestionDesc': 'Добавьте новый вопрос в базу',
    'dashboard.studentResults': 'Результаты студентов',
    'dashboard.studentResultsDesc': 'Просмотрите результаты тестов',
    'dashboard.go': 'Перейти',
    'dashboard.statistics': 'Статистика',
    'dashboard.statisticsDesc': 'Здесь будет отображаться статистика и аналитика',
    
    // Общие
    'common.loading': 'Загрузка...',
    'common.error': 'Ошибка',
    'common.success': 'Успешно',
    'common.save': 'Сохранить',
    'common.cancel': 'Отмена',
    'common.delete': 'Удалить',
    'common.edit': 'Редактировать',
    'common.notFound': '404 - Страница не найдена',
    'common.language': 'Язык',
    
    // Админ-панель
    'admin.title': 'Админ-панель',
    'admin.stats': 'Статистика',
    'admin.users': 'Пользователи',
    'admin.questions': 'Вопросы',
    'admin.tests': 'Тесты',
    'admin.submissions': 'Результаты',
    'admin.images': 'Изображения',
    'admin.auditLogs': 'Журнал действий',
    'admin.totalUsers': 'Всего пользователей',
    'admin.students': 'Студенты',
    'admin.teachers': 'Преподаватели',
    'admin.admins': 'Администраторы',
    'admin.publishedTests': 'Опубликованные тесты',
    'admin.completedSubmissions': 'Завершённые результаты',
    'admin.search': 'Поиск...',
    'admin.role': 'Роль',
    'admin.all': 'Все',
    'admin.addUser': 'Добавить пользователя',
    'admin.name': 'ФИО',
    'admin.status': 'Статус',
    'admin.createdAt': 'Создан',
    'admin.actions': 'Действия',
    'admin.active': 'Активен',
    'admin.inactive': 'Неактивен',
    'admin.verified': 'Подтверждён',
    'admin.rowsPerPage': 'Строк на странице',
    'admin.itemTitle': 'Название',
    'admin.type': 'Тип',
    'admin.author': 'Автор',
    'admin.content': 'Содержание',
    'admin.description': 'Описание',
    'admin.draft': 'Черновик',
    'admin.published': 'Опубликован',
    'admin.archived': 'В архиве',
    'admin.student': 'Студент',
    'admin.test': 'Тест',
    'admin.score': 'Баллы',
    'admin.startedAt': 'Начат',
    'admin.filename': 'Имя файла',
    'admin.dimensions': 'Размеры',
    'admin.size': 'Размер',
    'admin.user': 'Пользователь',
    'admin.action': 'Действие',
    'admin.resourceType': 'Тип ресурса',
    'admin.timestamp': 'Время',
    'admin.create': 'Создать',
    'admin.confirmDelete': 'Подтверждение удаления',
    'admin.deleteConfirmMessage': 'Вы уверены, что хотите удалить',

    // Темы
    'topics.title': 'Темы',
    'topics.create': 'Создать тему',
    'topics.edit': 'Редактировать тему',
    'topics.delete': 'Удалить тему',
    'topics.noTopics': 'Темы отсутствуют',
    'topics.createFirst': 'Создать первую тему',
    'topics.name': 'Название темы',
    'topics.description': 'Описание (опционально)',
    'topics.deleteConfirm': 'Вы уверены, что хотите удалить эту тему?',
    'topics.saving': 'Сохранение...',
    'topics.update': 'Обновить',
    'topics.error.deleteWithQuestions': 'Нельзя удалить тему, к которой привязаны вопросы',
    'topics.error.alreadyExists': 'Тема с таким названием уже существует',
    'topics.error.notFound': 'Тема не найдена',
    'topics.accessDenied': 'Доступ запрещен',
    'topics.accessDeniedDesc': 'Студенты не имеют доступа к этой странице.',
    'topics.loadError': 'Ошибка загрузки тем',

    // Ошибки
    'error.notEnoughPermissions': 'Недостаточно прав',
    'error.unexpected': 'Произошла непредвиденная ошибка',

    // Вопросы
    'questions.title': 'Вопросы',
    'questions.create': 'Создать вопрос',
    'questions.edit': 'Редактировать вопрос',
    'questions.view': 'Просмотр вопроса',
    'questions.type': 'Тип вопроса',
    'questions.type.text': 'Текстовый ответ',
    'questions.type.imageAnnotation': 'Графическая аннотация',
    'questions.topic': 'Тема',
    'questions.noTopic': 'Без темы',
    'questions.content': 'Текст вопроса',
    'questions.referenceAnswer': 'Эталонный ответ',
    'questions.referenceAnswerDesc': 'Ответ, с которым будут сравниваться ответы студентов',
    'questions.imageAnnotationInfo': 'Для графических вопросов студенты будут размечать изображения. Загрузка изображений пока не реализована - будет добавлена позже.',
    'questions.enterContent': 'Введите текст вопроса',
    'questions.enterReferenceAnswer': 'Введите эталонный ответ',
    'questions.difficulty': 'Сложность',
    'questions.selectType': 'Выберите тип вопроса',
    'questions.bank': 'Банк вопросов',
    'questions.searchPlaceholder': 'Поиск по названию или содержанию...',
    'questions.allTopics': 'Все темы',
    'questions.allTypes': 'Все типы',
    'questions.emptyBank': 'Банк вопросов пуст',
    'questions.noResults': 'Вопросы не найдены',
    'questions.createFirst': 'Создать первый вопрос',
    'questions.date': 'Дата',
    'questions.deleteConfirm': 'Вы уверены, что хотите удалить этот вопрос?',
    'questions.viewTitle': 'Просмотр',
    'questions.editTitle': 'Редактировать',
    'questions.deleteTitle': 'Удалить',
    'questions.uploadImageAndAnnotations': 'Загрузите изображение и (опционально) файл аннотаций',
    'questions.annotationsLoaded': 'Аннотации загружены',
    'questions.imageRequired': 'Изображение обязательно',
    'questions.selectImageAndAnnotations': 'Пожалуйста, выберите изображение вместе с файлом аннотаций',
    'questions.supportedFormats': 'Поддерживаются JPG, PNG и JSON (COCO format)',
    'questions.uploading': 'Загрузка...',
    'questions.chooseFiles': 'Выбрать файлы',
    'questions.annotationsRequired': 'Для графического вопроса наличие аннотаций обязательно',
  },
  en: {
    // Roles
    'role.admin': 'Administrator',
    'role.teacher': 'Teacher',
    'role.student': 'Student',
    
    // Navigation
    'nav.dashboard': 'Dashboard',
    'nav.tests': 'Tests',
    'nav.questions': 'Questions',
    'nav.submissions': 'Submissions',
    'nav.profile': 'Profile',
    'nav.logout': 'Logout',
    'nav.admin': 'Admin Panel',
    'nav.topics': 'Topics',
    
    // Auth
    'auth.login': 'Login',
    'auth.register': 'Register',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.lastName': 'Last Name',
    'auth.firstName': 'First Name',
    'auth.middleName': 'Middle Name',
    'auth.noAccount': "Don't have an account?",
    'auth.hasAccount': 'Already have an account?',
    'auth.loading': 'Loading...',
    'auth.registering': 'Registering...',
    'auth.passwordMin': 'Minimum 6 characters',
    'auth.enterLastName': 'Enter last name',
    'auth.enterFirstName': 'Enter first name',
    'auth.invalidCredentials': 'Invalid email or password',
    'auth.userNotFound': 'User not found',
    'auth.accountInactive': 'Account is deactivated',
    'auth.loginError': 'Login error. Check your credentials.',
    'auth.networkError': 'Network error. Server unavailable.',
    
    // Profile
    'profile.title': 'Profile',
    'profile.edit': 'Edit Profile',
    'profile.save': 'Save',
    'profile.cancel': 'Cancel',
    'profile.changePassword': 'Change Password',
    'profile.currentPassword': 'Current Password',
    'profile.newPassword': 'New Password',
    'profile.confirmPassword': 'Confirm Password',
    'profile.passwordMismatch': 'Passwords do not match',
    'profile.saved': 'Profile saved',
    'profile.passwordChanged': 'Password changed',
    'profile.editDescription': 'Here you can edit your information',
    'profile.emailReadonly': 'Email cannot be changed',
    'profile.changeEmail': 'Change email',
    'profile.newEmail': 'New email',
    'profile.sendCode': 'Send code',
    'profile.enterCode': 'Enter code from email',
    'profile.codeSent': 'Code sent to',
    'profile.confirmCode': 'Confirm',
    'profile.emailChanged': 'Email changed successfully',
    'profile.codeExpired': 'Code expired, request a new one',
    'profile.invalidCode': 'Invalid code',
    'profile.emailAlreadyRegistered': 'This email is already registered',
    'profile.noPendingRequest': 'No pending email change request',
    
    // Dashboard
    'dashboard.welcome.admin': 'Welcome, Administrator!',
    'dashboard.welcome.teacher': 'Welcome, Teacher!',
    'dashboard.welcome.student': 'Welcome, Student!',
    'dashboard.welcome.default': 'Welcome!',
    'dashboard.availableTests': 'Available Tests',
    'dashboard.takeTest': 'Take a new test',
    'dashboard.myResults': 'My Results',
    'dashboard.viewResults': 'View your results',
    'dashboard.createTest': 'Create Test',
    'dashboard.createTestDesc': 'Create a new test for students',
    'dashboard.createQuestion': 'Create Question',
    'dashboard.createQuestionDesc': 'Add a new question to the database',
    'dashboard.studentResults': 'Student Results',
    'dashboard.studentResultsDesc': 'View test results',
    'dashboard.go': 'Go',
    'dashboard.statistics': 'Statistics',
    'dashboard.statisticsDesc': 'Statistics and analytics will be displayed here',
    
    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.notFound': '404 - Page not found',
    'common.language': 'Language',
    
    // Admin Panel
    'admin.title': 'Admin Panel',
    'admin.stats': 'Statistics',
    'admin.users': 'Users',
    'admin.questions': 'Questions',
    'admin.tests': 'Tests',
    'admin.submissions': 'Submissions',
    'admin.images': 'Images',
    'admin.auditLogs': 'Audit Logs',
    'admin.totalUsers': 'Total Users',
    'admin.students': 'Students',
    'admin.teachers': 'Teachers',
    'admin.admins': 'Admins',
    'admin.publishedTests': 'Published Tests',
    'admin.completedSubmissions': 'Completed Submissions',
    'admin.search': 'Search...',
    'admin.role': 'Role',
    'admin.all': 'All',
    'admin.addUser': 'Add User',
    'admin.name': 'Name',
    'admin.status': 'Status',
    'admin.createdAt': 'Created',
    'admin.actions': 'Actions',
    'admin.active': 'Active',
    'admin.inactive': 'Inactive',
    'admin.verified': 'Verified',
    'admin.rowsPerPage': 'Rows per page',
    'admin.itemTitle': 'Title',
    'admin.type': 'Type',
    'admin.author': 'Author',
    'admin.content': 'Content',
    'admin.description': 'Description',
    'admin.draft': 'Draft',
    'admin.published': 'Published',
    'admin.archived': 'Archived',
    'admin.student': 'Student',
    'admin.test': 'Test',
    'admin.score': 'Score',
    'admin.startedAt': 'Started',
    'admin.filename': 'Filename',
    'admin.dimensions': 'Dimensions',
    'admin.size': 'Size',
    'admin.user': 'User',
    'admin.action': 'Action',
    'admin.resourceType': 'Resource Type',
    'admin.timestamp': 'Timestamp',
    'admin.create': 'Create',
    'admin.confirmDelete': 'Confirm Delete',
    'admin.deleteConfirmMessage': 'Are you sure you want to delete',

    // Topics
    'topics.title': 'Topics',
    'topics.create': 'Create Topic',
    'topics.edit': 'Edit Topic',
    'topics.delete': 'Delete Topic',
    'topics.noTopics': 'No topics',
    'topics.createFirst': 'Create first topic',
    'topics.name': 'Topic Name',
    'topics.description': 'Description (optional)',
    'topics.deleteConfirm': 'Are you sure you want to delete this topic?',
    'topics.saving': 'Saving...',
    'topics.update': 'Update',
    'topics.error.deleteWithQuestions': 'Cannot delete topic with associated questions',
    'topics.error.alreadyExists': 'Topic with this name already exists',
    'topics.error.notFound': 'Topic not found',
    'topics.accessDenied': 'Access Denied',
    'topics.accessDeniedDesc': 'Students do not have access to this page.',
    'topics.loadError': 'Error loading topics',

    // Errors
    'error.notEnoughPermissions': 'Not enough permissions',
    'error.unexpected': 'An unexpected error occurred',

    // Questions
    'questions.title': 'Questions',
    'questions.create': 'Create Question',
    'questions.edit': 'Edit Question',
    'questions.view': 'View Question',
    'questions.type': 'Question Type',
    'questions.type.text': 'Text Answer',
    'questions.type.imageAnnotation': 'Image Annotation',
    'questions.topic': 'Topic',
    'questions.noTopic': 'No Topic',
    'questions.content': 'Question Content',
    'questions.referenceAnswer': 'Reference Answer',
    'questions.referenceAnswerDesc': 'The answer that student answers will be compared to',
    'questions.imageAnnotationInfo': 'For image questions, students will annotate images. Image uploading is not yet implemented - it will be added later.',
    'questions.enterContent': 'Enter question content',
    'questions.enterReferenceAnswer': 'Enter reference answer',
    'questions.difficulty': 'Difficulty',
    'questions.selectType': 'Select question type',
    'questions.bank': 'Question Bank',
    'questions.searchPlaceholder': 'Search by content...',
    'questions.allTopics': 'All Topics',
    'questions.allTypes': 'All Types',
    'questions.emptyBank': 'Question bank is empty',
    'questions.noResults': 'No questions found',
    'questions.createFirst': 'Create first question',
    'questions.date': 'Date',
    'questions.deleteConfirm': 'Are you sure you want to delete this question?',
    'questions.viewTitle': 'View',
    'questions.editTitle': 'Edit',
    'questions.deleteTitle': 'Delete',
    'questions.uploadImageAndAnnotations': 'Upload image and (optional) annotation file',
    'questions.annotationsLoaded': 'Annotations loaded',
    'questions.imageRequired': 'Image is required',
    'questions.selectImageAndAnnotations': 'Please select an image along with the annotation file',
    'questions.supportedFormats': 'Supported formats: JPG, PNG and JSON (COCO format)',
    'questions.uploading': 'Uploading...',
    'questions.chooseFiles': 'Choose files',
    'questions.annotationsRequired': 'Annotations are required for image questions',
  },
}

type TranslationKey = keyof typeof translations.ru

interface LocaleContextType {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey) => string
  translateError: (detail: any) => string
  formatName: (lastName: string, firstName: string, middleName?: string | null) => string
  formatRole: (role: string) => string
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined)

const LOCALE_STORAGE_KEY = 'app_locale'

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
    return (saved as Locale) || 'ru'
  })

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale)
    localStorage.setItem(LOCALE_STORAGE_KEY, newLocale)
  }, [])

  const t = useCallback((key: TranslationKey): string => {
    return translations[locale][key] || key
  }, [locale])

  // Перевод ошибок API
  const translateError = useCallback((detail: any): string => {
    if (typeof detail !== 'string') {
      return translations[locale]['common.error'] || 'Error'
    }

    const errorMap: Record<string, TranslationKey> = {
      'Not enough permissions': 'error.notEnoughPermissions',
      'Topic with this name already exists': 'topics.error.alreadyExists',
      'Topic not found': 'topics.error.notFound',
      'Cannot delete topic with associated questions': 'topics.error.deleteWithQuestions',
      'Incorrect email or password': 'auth.invalidCredentials',
      'User not found': 'auth.userNotFound',
      'Inactive user': 'auth.accountInactive',
      'Email already registered': 'profile.emailAlreadyRegistered',
    }

    const key = errorMap[detail]
    if (key && translations[locale][key]) {
      return translations[locale][key]
    }

    return detail
  }, [locale])

  // Форматирование ФИО: "Фамилия И.О." или "LastName F.M."
  const formatName = useCallback((lastName: string, firstName: string, middleName?: string | null): string => {
    const firstInitial = firstName ? firstName.charAt(0).toUpperCase() + '.' : ''
    const middleInitial = middleName ? middleName.charAt(0).toUpperCase() + '.' : ''
    
    return `${lastName} ${firstInitial}${middleInitial}`.trim()
  }, [])

  // Форматирование роли на текущем языке
  const formatRole = useCallback((role: string): string => {
    const roleKey = `role.${role}` as TranslationKey
    return translations[locale][roleKey] || role
  }, [locale])

  const value = {
    locale,
    setLocale,
    t,
    translateError,
    formatName,
    formatRole,
  }

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  const context = useContext(LocaleContext)
  if (context === undefined) {
    throw new Error('useLocale must be used within a LocaleProvider')
  }
  return context
}
