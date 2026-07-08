import React, { useState, useRef } from "react"
import { UploadCloud, FileSpreadsheet, Loader2, CheckCircle2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog"
import { Button } from "./ui/button"
import { api } from "@/api/client"

interface UploadDialogProps {
  onUploadSuccess: (projectId: number) => void
}

export function UploadDialog({ onUploadSuccess }: UploadDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0])
    }
  }

  const handleFileSelection = (selectedFile: File) => {
    setError(null)
    if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
      setError("Please select a valid Excel file (.xlsx or .xls)")
      return
    }
    setFile(selectedFile)
  }

  const handleUpload = async () => {
    if (!file) return
    
    setIsUploading(true)
    setError(null)
    
    try {
      const response = await api.uploadProject(file)
      setSuccess(true)
      setTimeout(() => {
        setIsOpen(false)
        setSuccess(false)
        setFile(null)
        onUploadSuccess(response.project_id)
      }, 1500)
    } catch (err: any) {
      setError(err.message || "Failed to upload project plan")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2 shadow-lg shadow-primary/20">
          <UploadCloud className="w-4 h-4" />
          Upload Project Plan
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Project Plan</DialogTitle>
          <DialogDescription>
            Upload an Excel (.xlsx) file to create a new project and map its schema.
          </DialogDescription>
        </DialogHeader>
        
        {!success ? (
          <div className="space-y-4">
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
                isDragging 
                  ? "border-primary bg-primary/10 scale-[1.02]" 
                  : file 
                    ? "border-primary/50 bg-primary/5" 
                    : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileChange} 
                className="hidden" 
                accept=".xlsx,.xls" 
              />
              
              <div className="flex flex-col items-center gap-3">
                <div className={`p-3 rounded-full ${file ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
                  <FileSpreadsheet className="w-8 h-8" />
                </div>
                
                {file ? (
                  <div className="space-y-1">
                    <p className="font-medium text-foreground">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="font-medium text-foreground">Click or drag file to this area</p>
                    <p className="text-xs text-muted-foreground">Supports .xlsx and .xls formats</p>
                  </div>
                )}
              </div>
            </div>
            
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md border border-destructive/20 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button variant="ghost" onClick={() => setIsOpen(false)} disabled={isUploading}>
                Cancel
              </Button>
              <Button onClick={handleUpload} disabled={!file || isUploading} className="min-w-[120px]">
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  "Upload File"
                )}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 space-y-4">
            <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center animate-in zoom-in duration-300">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div className="text-center">
              <h3 className="text-xl font-semibold">Upload Complete!</h3>
              <p className="text-muted-foreground mt-1 text-sm">Schema mapped successfully. Redirecting...</p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// Add AlertTriangle import since it's used in the error message
import { AlertTriangle } from "lucide-react"
