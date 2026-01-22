import React from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Box,
  CircularProgress
} from '@mui/material'
import { useLocale } from '../../contexts/LocaleContext'

interface ConfirmDialogProps {
  open: boolean
  title: string
  content: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
  color?: 'primary' | 'secondary' | 'error' | 'success' | 'info' | 'warning'
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  content,
  confirmText,
  cancelText,
  onConfirm,
  onCancel,
  isLoading = false,
  color = 'primary'
}) => {
  const { t } = useLocale()
  
  const finalConfirmText = confirmText || t('common.confirm')
  const finalCancelText = cancelText || t('common.cancel')

  return (
    <Dialog
      open={open}
      onClose={() => !isLoading && onCancel()}
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-description"
    >
      <DialogTitle id="confirm-dialog-title">
        {title}
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="confirm-dialog-description">
          {content}
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ p: 2, pt: 0 }}>
        <Button 
          onClick={onCancel} 
          disabled={isLoading}
          variant="outlined"
          color="inherit"
        >
          {finalCancelText}
        </Button>
        <Button 
          onClick={onConfirm} 
          disabled={isLoading}
          variant="contained" 
          color={color}
          autoFocus
          startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {isLoading ? t('common.loading') : finalConfirmText}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
