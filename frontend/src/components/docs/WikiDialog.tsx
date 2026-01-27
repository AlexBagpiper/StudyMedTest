import React, { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Divider,
  Paper
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import DashboardIcon from '@mui/icons-material/Dashboard'
import SchoolIcon from '@mui/icons-material/School'
import PersonIcon from '@mui/icons-material/Person'
import CalculateIcon from '@mui/icons-material/Calculate'
import QuizIcon from '@mui/icons-material/Quiz'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { docsApi } from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'

interface WikiDialogProps {
  open: boolean
  onClose: () => void
}

const WikiDialog: React.FC<WikiDialogProps> = ({ open, onClose }) => {
  const { user } = useAuth()
  const { t } = useLocale()
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState<string[]>([])
  const [currentDoc, setCurrentDoc] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')

  const loadDocList = useCallback(async () => {
    try {
      const data = await docsApi.listDocs()
      setDocs(data.documents)
      
      // Выбор начального документа
      if (data.documents.length > 0) {
        let initialDoc = 'Home.md'
        if (user?.role === 'admin' && data.documents.includes('AdminGuide.md')) {
          initialDoc = 'AdminGuide.md'
        } else if (user?.role === 'teacher' && data.documents.includes('TeacherGuide.md')) {
          initialDoc = 'TeacherGuide.md'
        } else if (user?.role === 'student' && data.documents.includes('StudentGuide.md')) {
          initialDoc = 'StudentGuide.md'
        } else if (!data.documents.includes(initialDoc)) {
          initialDoc = data.documents[0]
        }
        
        setCurrentDoc(initialDoc)
      }
    } catch (err) {
      console.error('Failed to load wiki docs list:', err)
    }
  }, [user?.role])

  const loadDocContent = useCallback(async (filename: string) => {
    try {
      setLoading(true)
      const data = await docsApi.getDoc(filename)
      setContent(data.content)
      setCurrentDoc(filename)
    } catch (err) {
      console.error(`Failed to load wiki doc ${filename}:`, err)
      setContent('Ошибка при загрузке документа.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadDocList()
    }
  }, [open, loadDocList])

  useEffect(() => {
    if (currentDoc) {
      loadDocContent(currentDoc)
    }
  }, [currentDoc, loadDocContent])

  const handleLinkClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'A') {
      const href = target.getAttribute('href')
      if (href && href.endsWith('.md') && docs.includes(href)) {
        e.preventDefault()
        setCurrentDoc(href)
      }
    }
  }

  const getDocIcon = (doc: string) => {
    const name = doc.replace('.md', '')
    switch (name) {
      case 'Home': return <DashboardIcon fontSize="small" />
      case 'AdminGuide': return <AdminPanelSettingsIcon fontSize="small" />
      case 'TeacherGuide': return <SchoolIcon fontSize="small" />
      case 'StudentGuide': return <PersonIcon fontSize="small" />
      case 'ScoringMethodology': return <CalculateIcon fontSize="small" />
      case 'FAQ': return <HelpOutlineIcon fontSize="small" />
      case 'Roles': return <QuizIcon fontSize="small" />
      default: return <HelpOutlineIcon fontSize="small" />
    }
  }

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="lg" 
      fullWidth
      PaperProps={{
        sx: { 
          height: '80vh', 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden' // Запрещаем скролл на уровне Paper
        }
      }}
    >
      <DialogTitle component="div" sx={{ m: 0, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Typography variant="h6">Справка MedTest Platform</Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent 
        dividers 
        sx={{ 
          p: 0, 
          display: 'flex', 
          flex: 1, 
          overflow: 'hidden',
          minHeight: 0 // Важно для корректного flex-сжатия
        }}
      >
        {/* Боковая панель со списком документов */}
        <Box sx={{ width: 250, borderRight: '1px solid #e0e0e0', overflowY: 'auto', bgcolor: '#f9f9f9' }}>
          <List>
            {docs.map((doc) => (
              <ListItem key={doc} disablePadding>
                <ListItemButton 
                  selected={currentDoc === doc}
                  onClick={() => setCurrentDoc(doc)}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {getDocIcon(doc)}
                  </ListItemIcon>
                  <ListItemText 
                    primary={t(`wiki.${doc.replace('.md', '')}` as any).includes('wiki.') 
                      ? doc.replace('.md', '') 
                      : t(`wiki.${doc.replace('.md', '')}` as any)} 
                    primaryTypographyProps={{ 
                      fontSize: '0.85rem',
                      fontWeight: currentDoc === doc ? 'bold' : 'normal'
                    }} 
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>

        {/* Основной контент */}
        <Box 
          sx={{ flex: 1, p: 3, overflowY: 'auto', bgcolor: 'white' }} 
          onClick={handleLinkClick}
        >
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box 
              className="markdown-body"
              sx={{ 
                '& table': { display: 'block', overflowX: 'auto' },
                '& pre': { overflowX: 'auto' }
              }}
            >
              <ReactMarkdown 
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  h1: ({node, ref, ...props}: any) => <Typography variant="h4" gutterBottom {...props} />,
                  h2: ({node, ref, ...props}: any) => <Typography variant="h5" gutterBottom sx={{ mt: 3 }} {...props} />,
                  h3: ({node, ref, ...props}: any) => <Typography variant="h6" gutterBottom sx={{ mt: 2 }} {...props} />,
                  p: ({node, ref, ...props}: any) => <Typography variant="body1" paragraph {...props} />,
                  li: ({node, ref, ...props}: any) => <Typography component="li" variant="body1" {...props} />,
                  table: ({node, ref, ...props}: any) => (
                    <Paper variant="outlined" sx={{ my: 2, overflow: 'hidden' }}>
                      <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', '& td, & th': { border: '1px solid #e0e0e0', p: 1 } }} {...props} />
                    </Paper>
                  )
                }}
              >
                {content}
              </ReactMarkdown>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}

export default WikiDialog
