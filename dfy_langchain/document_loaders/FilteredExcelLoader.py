## 指定制定列的Excel文件加载器

import os
from typing import Dict, List, Optional, Any, Union
import pandas as pd

from langchain_core.documents import Document
from langchain_community.document_loaders.base import BaseLoader


class FilteredExcelLoader(BaseLoader):
    """
    用于加载Excel文件并过滤指定列的加载器
    支持.xlsx和.xls格式的Excel文件
    """
    
    def __init__(
        self,
        file_path: str,
        columns_to_read: Optional[List[str]] = None,
        source_column: Optional[str] = None,
        metadata_columns: List[str] = [],
        sheet_name: Optional[Union[str, int, List[Union[str, int]]]] = 0,
        excel_kwargs: Optional[Dict] = None,
    ):
        """
        初始化Excel文件加载器
        
        Args:
            file_path: Excel文件路径
            columns_to_read: 需要读取的列名列表，如果为None则读取所有列
            source_column: 指定作为文档来源的列名，如果为None则使用文件路径
            metadata_columns: 需要添加到文档元数据的列名列表
            sheet_name: 要读取的工作表名称或索引，默认为第一个工作表
            excel_kwargs: 传递给pandas.read_excel的额外参数
        """
        self.file_path = file_path
        self.columns_to_read = columns_to_read
        self.source_column = source_column
        self.metadata_columns = metadata_columns
        self.sheet_name = sheet_name
        self.excel_kwargs = excel_kwargs or {}
    
    def load(self) -> List[Document]:
        """加载Excel文件并转换为文档对象"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        try:
            # 使用pandas读取Excel文件
            df = pd.read_excel(
                self.file_path, 
                sheet_name=self.sheet_name,
                **self.excel_kwargs
            )
            
            # 如果读取了多个工作表（sheet_name为None或列表时）
            if isinstance(df, dict):
                all_docs = []
                for sheet_name, sheet_df in df.items():
                    docs = self._process_dataframe(sheet_df, sheet_name)
                    all_docs.extend(docs)
                return all_docs
            
            # 单个工作表的情况
            return self._process_dataframe(df)
            
        except Exception as e:
            raise RuntimeError(f"加载Excel文件 {self.file_path} 时出错: {str(e)}")
    
    def _process_dataframe(self, df: pd.DataFrame, sheet_name: Optional[str] = None) -> List[Document]:
        """处理DataFrame并转换为Document对象列表"""
        docs = []
        
        # 如果未指定columns_to_read，则使用DataFrame的所有列
        columns_to_process = self.columns_to_read if self.columns_to_read is not None else df.columns.tolist()
        
        # 检查指定的列是否存在
        missing_cols = [col for col in columns_to_process if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Excel文件中缺少以下列: {', '.join(missing_cols)}")
        
        # 处理每一行,刁福元 2025-06-10 10:00:00
        for i, row in df.iterrows():
            content = []
            
            # 提取指定列的内容
            for col in columns_to_process:
                value = row[col]
                # 处理NaN值
                if pd.notna(value):
                    content.append(f"{col}:{str(value)}")
                else:
                    content.append(f"{col}:")
            
            content = "\n".join(content)
            
            # 提取源信息
            source = (
                row.get(self.source_column) 
                if self.source_column is not None and self.source_column in row
                else self.file_path
            )
            
            # 创建元数据
            metadata = {"source": source, "row": i}
            if sheet_name:
                metadata["sheet_name"] = sheet_name
                
            # 添加指定的元数据列
            for col in self.metadata_columns:
                if col in row and pd.notna(row[col]):
                    metadata[col] = str(row[col])
            
            # 创建文档对象
            doc = Document(page_content=content, metadata=metadata)
            docs.append(doc)
        
        return docs


if __name__ == "__main__":
    # 使用示例
    loader = FilteredExcelLoader(
        file_path="test.xlsx", 
        columns_to_read=["姓名", "年龄", "职业"],
        metadata_columns=["部门"]
    )
    docs = loader.load()
    print(docs)
    
    # 不指定columns_to_read的使用示例
    loader2 = FilteredExcelLoader(
        file_path="test.xlsx",
        metadata_columns=["部门"]
    )
    docs2 = loader2.load()
    print(docs2) 