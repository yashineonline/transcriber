/// <reference types="vite/client" />

type FileSystemPermissionMode = 'read' | 'readwrite'

interface FileSystemWritableFileStream extends WritableStream {
  write(data: Blob | BufferSource | string): Promise<void>
  close(): Promise<void>
}

interface FileSystemFileHandle {
  kind: 'file'
  name: string
  createWritable(): Promise<FileSystemWritableFileStream>
}

interface FileSystemDirectoryHandle {
  kind: 'directory'
  name: string
  getFileHandle(name: string, options?: { create?: boolean }): Promise<FileSystemFileHandle>
  requestPermission?(descriptor?: { mode: FileSystemPermissionMode }): Promise<PermissionState>
  queryPermission?(descriptor?: { mode: FileSystemPermissionMode }): Promise<PermissionState>
}

interface Window {
  showDirectoryPicker?: (options?: { mode?: FileSystemPermissionMode }) => Promise<FileSystemDirectoryHandle>
}
