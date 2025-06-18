import os
import sys
# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dfy_langchain.document_loaders.mypdfloader import RapidOCRPDFLoader
from dfy_langchain.document_loaders.mydocloader import RapidOCRDocLoader
from dfy_langchain.document_loaders.myimgloader import RapidOCRLoader
from dfy_langchain.document_loaders.mypptloader import RapidOCRPPTLoader
from dfy_langchain.document_loaders.FilteredCSVloader import FilteredCSVLoader
from dfy_langchain.document_loaders.FilteredExcelLoader import FilteredExcelLoader
from langchain_community.document_loaders import TextLoader


class UnstructuredLoader:
    """
    集成各种文档加载器的统一接口，支持多种文件格式:
    - PDF (.pdf): 使用PDFWithSemanticLoader
    - Word文档 (.doc, .docx): 使用RapidOCRDocLoader
    - 图像 (.jpg, .jpeg, .png): 使用RapidOCRLoader
    - PPT (.pptx): 使用RapidOCRPPTLoader
    - CSV (.csv): 使用FilteredCSVLoader
    - Excel (.xlsx): 使用FilteredExcelLoader
    - 文本文件 (.txt): 使用TextLoader
    """
    
    # 支持的文件类型映射
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'pdf',
        '.doc': 'doc',
        '.docx': 'doc',
        '.jpg': 'img',
        '.jpeg': 'img',
        '.png': 'img',
        '.pptx': 'ppt',
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.txt': 'txt'  # 添加txt文件支持
    }
    
    def __init__(self, file_path: str ):
        """初始化加载器，可以处理单个文件或目录"""
        self.file_path = file_path
        # 存储不同类型文档的文档片段
        self.docs_by_type = {
            'pdf': [],
            'doc': [],
            'img': [],
            'ppt': [],
            'csv': [],
            'excel': [],
            'txt': []  # 添加txt类型存储
        }
    
    def load_file(self):
        """加载文件或目录中的所有文件"""
        # 检查是否是目录
        if os.path.isdir(self.file_path):
            return self._load_directory()
        else:
            return self._load_single_file(self.file_path)
    
    def _load_directory(self):
        """加载目录中的所有支持的文件"""
        all_docs = []
        file_paths = os.listdir(self.file_path)
        absolute_file_paths = [os.path.join(self.file_path, file) for file in file_paths]

    
        
        for file_path in absolute_file_paths:
            if os.path.isfile(file_path):
                try:
                    docs = self._load_single_file(file_path)
                    all_docs.extend(docs)
                except Exception as e:
                    print(f"警告: 加载文件 {file_path} 失败: {str(e)}")
        
        return all_docs
    
    def _load_single_file(self, file_path):
        """加载单个文件，根据文件扩展名选择合适的加载器"""
        # 获取文件扩展名
        _, file_extension = os.path.splitext(file_path.lower())
        
        # 检查是否支持该文件类型
        if file_extension not in self.SUPPORTED_EXTENSIONS:
            print(f"警告: 不支持的文件类型: {file_path}，将跳过此文件")
            return [], "unknown"  # 确保返回一致的格式
        
        # 获取文件类型
        file_type = self.SUPPORTED_EXTENSIONS[file_extension]
        
        try:
            docs = []
            # 根据文件类型选择加载器
            if file_type == 'pdf':
                loader = RapidOCRPDFLoader(file_path)
                docs = loader.load()
                self.docs_by_type['pdf'].extend(docs)
            elif file_type == 'doc':
                loader = RapidOCRDocLoader(file_path)
                docs = loader.load()
                self.docs_by_type['doc'].extend(docs)
            elif file_type == 'img':
                loader = RapidOCRLoader(file_path)
                docs = loader.load()
                self.docs_by_type['img'].extend(docs)
            elif file_type == 'ppt':
                loader = RapidOCRPPTLoader(file_path)
                docs = loader.load()
                self.docs_by_type['ppt'].extend(docs)
            elif file_type == 'csv':
                loader = FilteredCSVLoader(file_path)
                docs = loader.load()
                self.docs_by_type['csv'].extend(docs)
            elif file_type == 'excel':
                loader = FilteredExcelLoader(file_path)
                docs = loader.load()
                self.docs_by_type['excel'].extend(docs)
            elif file_type == 'txt':
                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
                self.docs_by_type['txt'].extend(docs)
                
            return docs, file_type  # 确保总是返回一致的格式
        except Exception as e:
            print(f"错误: 处理文件 {file_path} 时出错: {str(e)}")
            return [], file_type  # 即使出错也返回一致的格式
    
    @property
    def pdf_docs(self):
        return self.docs_by_type['pdf']
    
    @property
    def doc_docs(self):
        return self.docs_by_type['doc']
    
    @property
    def img_docs(self):
        return self.docs_by_type['img']
    
    @property
    def ppt_docs(self):
        return self.docs_by_type['ppt']
    
    @property
    def csv_docs(self):
        return self.docs_by_type['csv']
    
    @property
    def excel_docs(self):
        return self.docs_by_type['excel']


if __name__ == "__main__":
    # 如果直接运行此脚本，需要调整导入路径以便找到相关模块
    loader = UnstructuredLoader(r"D:\ai\web_new\data\knowledge_base\测试\content\处罚决定书四川华筑联投置业有限公司.docx")
    docs = loader.load_file()
    print(docs)
    print(f"总共加载了 {len(docs)} 个文档片段")
    # 打印每种类型的文档数量
    print(f"PDF文档: {len(loader.pdf_docs)} 个片段")
    print(f"Word文档(.doc/.docx): {len(loader.doc_docs)} 个片段")
    print(f"图片: {len(loader.img_docs)} 个片段")
    print(f"PPT: {len(loader.ppt_docs)} 个片段")
    print(f"CSV: {len(loader.csv_docs)} 个片段")
    print(f"Excel: {len(loader.excel_docs)} 个片段")
    


