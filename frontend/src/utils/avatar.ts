const API_BASE_URL = '/api/files'

export function getFileUrl(filename: string): string {
  return `${API_BASE_URL}/${filename}`
}