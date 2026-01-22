import React from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button
} from '@mui/material'
import { useLocale } from '../../contexts/LocaleContext'

interface MessageDialogProps {
  open: boolean
  title: string
  content: string
  buttonText?: string
  onClose: () => void
  severity?: 'error' | 'info' | 'success' | 'warning'
}

export const MessageDialog: React.FC<MessageDialogProps> = ({
  open,
  title,
  content,
  buttonText,
  onClose,
  severity = 'info'
}) => {
  const { t } = useLocale()
  
  const finalButtonText = buttonText || t('common.ok')

  const getColor = () => {
    switch (severity) {
      case 'error': return 'error'
      case 'success': return 'success'
      case 'warning': return 'warning'
      default: return 'primary'
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="message-dialog-title"
      aria-describedby="message-dialog-description"
    >
      <DialogTitle id="message-dialog-title" sx={{ color: `${getColor()}.main` }}>
        {title}
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="message-dialog-description">
          {content}
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ p: 2, pt: 0 }}>
        <Button 
          onClick={onClose} 
          variant="contained" 
          color={getColor()}
          autoFocus
        >
          {finalButtonText}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
