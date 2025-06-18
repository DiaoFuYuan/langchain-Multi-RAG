import os
import mimetypes
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FileUtilsService:
    """文件工具服务"""
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """
        根据文件名获取文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            文件类型
        """
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # 映射常见文件类型
        type_map = {
            '.txt': '文本文件',
            '.pdf': 'PDF文档',
            '.doc': 'Word文档',
            '.docx': 'Word文档',
            '.xls': 'Excel表格',
            '.xlsx': 'Excel表格',
            '.ppt': 'PowerPoint',
            '.pptx': 'PowerPoint',
            '.csv': 'CSV文件',
            '.json': 'JSON文件',
            '.xml': 'XML文件',
            '.html': 'HTML文件',
            '.htm': 'HTML文件',
            '.md': 'Markdown文件',
            '.py': 'Python文件',
            '.js': 'JavaScript文件',
            '.css': 'CSS文件',
            '.jpg': '图片',
            '.jpeg': '图片',
            '.png': '图片',
            '.gif': '图片',
            '.bmp': '图片',
            '.svg': '图片',
            '.mp3': '音频文件',
            '.wav': '音频文件',
            '.mp4': '视频文件',
            '.avi': '视频文件',
            '.zip': '压缩文件',
            '.rar': '压缩文件',
            '.7z': '压缩文件',
        }
        
        return type_map.get(ext, f'{ext[1:].upper()}文件' if ext else '未知文件')
    
    @staticmethod
    def format_file_size(size_in_bytes: int) -> str:
        """
        格式化文件大小显示
        
        Args:
            size_in_bytes: 文件大小（字节）
            
        Returns:
            格式化后的文件大小字符串
        """
        if size_in_bytes == 0:
            return "0 B"
        
        # 定义单位
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        size = float(size_in_bytes)
        
        # 循环除以1024直到合适的单位
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        # 格式化输出
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    @staticmethod
    def get_mime_type(filename: str) -> str:
        """
        获取文件的MIME类型
        
        Args:
            filename: 文件名
            
        Returns:
            MIME类型
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def is_supported_file_type(filename: str) -> bool:
        """
        检查文件类型是否支持
        
        Args:
            filename: 文件名
            
        Returns:
            是否支持该文件类型
        """
        supported_extensions = {
            '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.ppt', '.pptx', '.csv', '.json', '.xml', '.html',
            '.htm', '.md'
        }
        
        _, ext = os.path.splitext(filename)
        return ext.lower() in supported_extensions
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            文件扩展名（不含点号）
        """
        _, ext = os.path.splitext(filename)
        return ext.lower().lstrip('.')
    
    @staticmethod
    def validate_filename(filename: str) -> Dict[str, Any]:
        """
        验证文件名的有效性
        
        Args:
            filename: 文件名
            
        Returns:
            验证结果
        """
        if not filename:
            return {
                "valid": False,
                "message": "文件名不能为空"
            }
        
        if len(filename) > 255:
            return {
                "valid": False,
                "message": "文件名过长（超过255个字符）"
            }
        
        # 检查非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in illegal_chars:
            if char in filename:
                return {
                    "valid": False,
                    "message": f"文件名包含非法字符: {char}"
                }
        
        # 检查是否为保留名称（Windows）
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return {
                "valid": False,
                "message": f"文件名不能使用保留名称: {name_without_ext}"
            }
        
        return {
            "valid": True,
            "message": "文件名有效"
        }
    
    @staticmethod
    def get_file_info(file_path: Path) -> Dict[str, Any]:
        """
        获取文件的详细信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        try:
            if not file_path.exists():
                return {
                    "exists": False,
                    "message": "文件不存在"
                }
            
            stat = file_path.stat()
            filename = file_path.name
            
            return {
                "exists": True,
                "filename": filename,
                "size": stat.st_size,
                "size_formatted": FileUtilsService.format_file_size(stat.st_size),
                "file_type": FileUtilsService.get_file_type(filename),
                "extension": FileUtilsService.get_file_extension(filename),
                "mime_type": FileUtilsService.get_mime_type(filename),
                "is_supported": FileUtilsService.is_supported_file_type(filename),
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "accessed_time": stat.st_atime
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return {
                "exists": False,
                "message": f"获取文件信息失败: {str(e)}"
            } 