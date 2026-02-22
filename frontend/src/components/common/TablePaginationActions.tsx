import { Box, Pagination } from '@mui/material'

/**
 * Нумерованная пагинация для TablePagination: 1 … 4 [5] 6 … 11
 * с первой/пред/след/последней кнопками (best practice).
 */
export function TablePaginationActions(props: {
  count: number
  page: number
  rowsPerPage: number
  onPageChange: (event: unknown, newPage: number) => void
}) {
  const { count, page, rowsPerPage, onPageChange } = props
  const totalPages = Math.ceil(count / rowsPerPage) || 1
  const currentPage = page + 1

  return (
    <Box sx={{ flexShrink: 0, ml: 1 }}>
      <Pagination
        count={totalPages}
        page={currentPage}
        onChange={(_, p) => onPageChange(null, p - 1)}
        color="primary"
        showFirstButton
        showLastButton
        siblingCount={1}
        boundaryCount={1}
        size="medium"
        shape="rounded"
        sx={{ '& .MuiPagination-ul': { flexWrap: 'nowrap' } }}
      />
    </Box>
  )
}
