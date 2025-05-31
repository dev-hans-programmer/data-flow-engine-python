"""
File management API endpoints for data input/output
"""

import os
import shutil
from typing import List
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import aiofiles

from app.models import FileInfo, DataFormat, ApiResponse
from app.postgres_db import postgres_db as db
from app.data_processor import DataProcessor
from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)
router = APIRouter()
data_processor = DataProcessor()


@router.post("/files/upload", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    """Upload a data file"""
    try:
        # Validate file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size {file.size} exceeds maximum allowed size {settings.max_file_size}"
            )
        
        # Validate file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.allowed_file_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_file_types}"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_directory)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        import uuid
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = upload_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Determine data format
        format_mapping = {
            '.csv': DataFormat.CSV,
            '.json': DataFormat.JSON,
            '.parquet': DataFormat.PARQUET,
            '.xlsx': DataFormat.XLSX,
            '.xls': DataFormat.XLSX
        }
        data_format = format_mapping.get(file_extension)
        
        # Get file info
        file_info = FileInfo(
            name=file.filename,
            path=str(file_path),
            size=file_path.stat().st_size,
            format=data_format
        )
        
        # Try to get basic metadata about the file
        try:
            if data_format:
                df = await data_processor.load_data(str(file_path), data_format)
                summary = await data_processor.get_data_summary(df)
                file_info.metadata = {
                    "rows": summary["shape"][0],
                    "columns": summary["shape"][1],
                    "column_names": summary["columns"],
                    "data_types": summary["dtypes"],
                    "memory_usage": summary["memory_usage"]
                }
        except Exception as e:
            logger.warning(f"Could not generate metadata for file {file.filename}: {e}")
            file_info.metadata = {"error": "Could not analyze file structure"}
        
        # Store file info in database
        await db.store_file_info(file_info)
        
        logger.info(f"Uploaded file: {file.filename} -> {file_path}")
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=List[FileInfo])
async def list_files():
    """List all uploaded files"""
    try:
        files = await db.list_files()
        
        # Filter out files that no longer exist on disk
        existing_files = []
        for file_info in files:
            if Path(file_info.path).exists():
                existing_files.append(file_info)
            else:
                # Remove from database if file doesn't exist
                await db.delete_file_info(file_info.path)
        
        return existing_files
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}/info", response_model=FileInfo)
async def get_file_info(file_path: str):
    """Get information about a specific file"""
    try:
        file_info = await db.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file still exists
        if not Path(file_info.path).exists():
            await db.delete_file_info(file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/outputs/{file_path:path}/download")
async def download_output_file(file_path: str):
    """Download an output file"""
    try:
        output_dir = Path(settings.output_directory)
        file_full_path = output_dir / file_path
        
        # Debug logging
        logger.info(f"Download request - file_path: {file_path}")
        logger.info(f"Download request - output_dir: {output_dir}")
        logger.info(f"Download request - file_full_path: {file_full_path}")
        logger.info(f"Download request - file exists: {file_full_path.exists()}")
        
        if not file_full_path.exists() or not file_full_path.is_file():
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Security check: ensure file is within output directory
        try:
            file_full_path.resolve().relative_to(output_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        return FileResponse(
            path=str(file_full_path),
            filename=file_full_path.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading output file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}/download")
async def download_file(file_path: str):
    """Download a file"""
    try:
        file_info = await db.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_full_path = Path(file_info.path)
        if not file_full_path.exists():
            await db.delete_file_info(file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=str(file_full_path),
            filename=file_info.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_path:path}", response_model=ApiResponse)
async def delete_file(file_path: str):
    """Delete a file"""
    try:
        file_info = await db.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete file from disk
        file_full_path = Path(file_info.path)
        if file_full_path.exists():
            file_full_path.unlink()
        
        # Remove from database
        await db.delete_file_info(file_path)
        
        logger.info(f"Deleted file: {file_path}")
        return ApiResponse(success=True, message="File deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}/preview")
async def preview_file(
    file_path: str,
    rows: int = Query(10, ge=1, le=1000),
    columns: List[str] = Query(None)
):
    """Preview file contents"""
    try:
        file_info = await db.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_info.format:
            raise HTTPException(status_code=400, detail="Cannot preview file: unknown format")
        
        file_full_path = Path(file_info.path)
        if not file_full_path.exists():
            await db.delete_file_info(file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Load data
        df = await data_processor.load_data(str(file_full_path), file_info.format)
        
        # Select specific columns if requested
        if columns:
            available_columns = [col for col in columns if col in df.columns]
            if available_columns:
                df = df[available_columns]
        
        # Limit rows
        preview_df = df.head(rows)
        
        # Convert to dict for JSON response
        preview_data = {
            "file_path": file_path,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "preview_rows": len(preview_df),
            "columns": list(df.columns),
            "data": preview_df.to_dict(orient='records')
        }
        
        return preview_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}/summary")
async def get_file_summary(file_path: str):
    """Get detailed summary statistics for a file"""
    try:
        file_info = await db.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_info.format:
            raise HTTPException(status_code=400, detail="Cannot analyze file: unknown format")
        
        file_full_path = Path(file_info.path)
        if not file_full_path.exists():
            await db.delete_file_info(file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Load and analyze data
        df = await data_processor.load_data(str(file_full_path), file_info.format)
        summary = await data_processor.get_data_summary(df)
        
        return {
            "file_path": file_path,
            "file_info": file_info,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file summary {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/outputs")
async def list_output_files():
    """List all output files generated by pipeline executions"""
    try:
        output_dir = Path(settings.output_directory)
        if not output_dir.exists():
            return {"output_files": [], "count": 0}
        
        output_files = []
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                output_files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(output_dir)),
                    "full_path": str(file_path),
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime
                })
        
        # Sort by creation time (newest first)
        output_files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "output_files": output_files,
            "count": len(output_files)
        }
        
    except Exception as e:
        logger.error(f"Error listing output files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/outputs/{file_path:path}/download")
async def download_output_file(file_path: str):
    """Download an output file"""
    try:
        output_dir = Path(settings.output_directory)
        file_full_path = output_dir / file_path
        
        # Debug logging
        logger.info(f"Download request - file_path: {file_path}")
        logger.info(f"Download request - output_dir: {output_dir}")
        logger.info(f"Download request - file_full_path: {file_full_path}")
        logger.info(f"Download request - file exists: {file_full_path.exists()}")
        
        if not file_full_path.exists() or not file_full_path.is_file():
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Security check: ensure file is within output directory
        try:
            file_full_path.resolve().relative_to(output_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        return FileResponse(
            path=str(file_full_path),
            filename=file_full_path.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading output file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
