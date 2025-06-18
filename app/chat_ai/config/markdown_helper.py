"""
Markdown格式处理模块 - 用于处理和显示AI回答的Markdown格式内容
"""
import re
import markdown
from bs4 import BeautifulSoup
import html
import pygments
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class MarkdownProcessor:
    """
    Markdown处理器类，专门用于处理和转换AI回答中的Markdown格式
    """
    
    def __init__(self):
        """初始化Markdown处理器"""
        # 配置markdown扩展
        self.markdown_extensions = [
            'markdown.extensions.tables',       # 表格支持
            'markdown.extensions.fenced_code',  # 代码块支持
            'markdown.extensions.codehilite',   # 代码高亮
            # 'markdown.extensions.nl2br',        # 换行支持 - 注释掉，避免过多换行
            'markdown.extensions.sane_lists',   # 列表优化
            'markdown.extensions.smarty',       # 智能标点
            'markdown.extensions.toc',          # 目录支持
        ]
        
        # 创建pygments格式化器，用于代码高亮
        self.html_formatter = HtmlFormatter(style='default', cssclass='codehilite')
        
        # 常见编程语言及其别名映射，用于代码高亮
        self.language_aliases = {
            'js': 'javascript',
            'py': 'python',
            'python3': 'python',
            'python2': 'python',
            'ts': 'typescript',
            'rb': 'ruby',
            'shell': 'bash',
            'sh': 'bash',
            'zsh': 'bash',
            'yml': 'yaml',
            'c++': 'cpp',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'java': 'java',
            'cs': 'csharp',
            'go': 'go',
            'rust': 'rust',
            'php': 'php',
            'swift': 'swift',
            'sql': 'sql',
            'kotlin': 'kotlin',
            'dart': 'dart',
            'text': 'text',
            '': 'text'
        }
    
    def convert_to_html(self, text):
        """
        将Markdown文本转换为HTML
        
        Args:
            text: Markdown格式的文本
            
        Returns:
            转换后的HTML文本
        """
        if not text:
            return ""
        
        # 预处理文本，清理多余的空白
        text = self._preprocess_text(text)
        
        # 预处理代码块，应用语法高亮
        text = self._preprocess_code_blocks(text)
        
        # 转换Markdown为HTML
        html_content = markdown.markdown(text, extensions=self.markdown_extensions)
        
        # 后处理HTML，对结果进行优化
        html_content = self._postprocess_html(html_content)
        
        return html_content
    
    def _preprocess_text(self, text):
        """
        预处理文本，清理多余的空白和换行
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 移除文本开头和结尾的空白
        text = text.strip()
        
        # 更激进地清理多余的空行：将多个连续空行替换为单个换行
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 处理bullet points和列表结构
        lines = text.split('\n')
        processed_lines = []
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # 标准化项目符号 - 将 • 转换为标准的 - 
            if stripped_line.startswith('•'):
                # 将 • 替换为 - 并确保正确的缩进
                new_line = re.sub(r'^(\s*)•\s*', '- ', line)
                processed_lines.append(new_line)
            # 处理数字列表格式
            elif re.match(r'^\d+\.\s+', stripped_line):
                processed_lines.append(line)
            # 处理dash列表格式
            elif re.match(r'^-\s+', stripped_line):
                processed_lines.append(line)
            # 处理包含冒号的标题行，确保后面的内容被正确识别为列表
            elif stripped_line.endswith(('：', ':')):
                processed_lines.append(line)
                # 如果下一行是bullet point或数字，确保格式正确
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('•') or re.match(r'^\d+\.\s+', next_line):
                        processed_lines.append('')  # 添加空行以确保列表格式
            else:
                processed_lines.append(line)
        
        text = '\n'.join(processed_lines)
        
        # 特殊处理：确保bullet points被正确识别为列表
        # 将所有的 • 开头的行转换为标准的markdown列表格式
        text = re.sub(r'^(\s*)•\s+(.+)$', r'\1- \2', text, flags=re.MULTILINE)
        
        # 清理列表项之间的多余空白
        # 处理数字列表项之间的空行
        text = re.sub(r'(\d+\.\s+[^\n]+)\n\n+(\d+\.\s+)', r'\1\n\2', text)
        
        # 处理破折号列表项之间的空行
        text = re.sub(r'(-\s+[^\n]+)\n\n+(-\s+)', r'\1\n\2', text)
        
        # 清理冒号后内容的空行
        text = re.sub(r'(：[^\n]*)\n\n+([^-\d])', r'\1\n\2', text)
        
        # 特殊处理：如果一行只有数字+点+冒号（如"1. 涉事商品："），
        # 确保它后面的列表项紧跟其后，但保留一个空行以确保markdown解析正确
        text = re.sub(r'(\d+\.\s+[^：\n]*：)\n\n+(-\s+)', r'\1\n\n\2', text)
        
        # 确保列表前有适当的空行
        text = re.sub(r'([^：\n])\n(-\s+)', r'\1\n\n\2', text)
        text = re.sub(r'([^：\n])\n(\d+\.\s+)', r'\1\n\n\2', text)
        
        # 移除行尾的空白字符
        lines = text.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        text = '\n'.join(cleaned_lines)
        
        return text
    
    def _preprocess_code_blocks(self, text):
        """
        预处理代码块，增强代码块的展示效果
        
        Args:
            text: Markdown文本
            
        Returns:
            预处理后的Markdown文本
        """
        # 处理围栏式代码块 ```language code```
        pattern = r'```(\w+)?\n([\s\S]*?)```'
        
        def replace_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            
            # 规范化语言名称
            lang = lang.lower().strip()
            lang = self.language_aliases.get(lang, lang)
            
            # 对代码内容进行处理：清理前后空白行，但保留缩进
            code_lines = code.split('\n')
            
            # 移除前后的空行
            while code_lines and not code_lines[0].strip():
                code_lines.pop(0)
            while code_lines and not code_lines[-1].strip():
                code_lines.pop()
                
            # 重新组装代码，保留缩进
            processed_code = '\n'.join(code_lines)
            
            # 确保代码块正确包装
            if lang:
                return f'```{lang}\n{processed_code}\n```'
            else:
                return f'```\n{processed_code}\n```'
        
        # 使用正则表达式替换代码块
        processed_text = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
        
        return processed_text
    
    def _postprocess_html(self, html_content):
        """
        对转换后的HTML进行后处理，增强显示效果
        
        Args:
            html_content: 转换后的HTML内容
            
        Returns:
            后处理优化后的HTML内容
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 处理代码块，简化结构避免过多留白
        for code_block in soup.find_all('pre'):
            # 给代码块添加基本样式类
            code_block['class'] = code_block.get('class', []) + ['markdown-code-block']
            
            # 处理代码内容
            code_tag = code_block.find('code')
            if code_tag:
                # 获取代码内容并清理多余空白
                code_text = code_tag.string if code_tag.string else ''
                if code_text:
                    # 移除前后空行但保留缩进
                    code_lines = code_text.split('\n')
                    
                    # 移除开头的空行
                    while code_lines and not code_lines[0].strip():
                        code_lines.pop(0)
                    
                    # 移除结尾的空行
                    while code_lines and not code_lines[-1].strip():
                        code_lines.pop()
                    
                    # 清理行尾空白但保留缩进
                    cleaned_lines = [line.rstrip() for line in code_lines]
                    code_tag.string = '\n'.join(cleaned_lines)
        
        # 更激进地处理列表，减少间距
        for list_tag in soup.find_all(['ol', 'ul']):
            # 添加紧凑样式类
            list_tag['class'] = list_tag.get('class', []) + ['markdown-list', 'compact-list']
            
            # 处理列表项
            for li in list_tag.find_all('li'):
                # 移除列表项内的多余段落标签，避免额外间距
                paragraphs = li.find_all('p')
                for p in paragraphs:
                    # 如果段落只有一行内容，直接替换为文本
                    if p.string and not p.find_all():
                        p.replace_with(p.string)
                    elif len(p.contents) == 1 and hasattr(p.contents[0], 'string'):
                        p.replace_with(p.contents[0])
                    else:
                        # 对于复杂的段落，也尽量移除
                        p.unwrap()
                
                # 处理特殊格式（如"房产："）
                text = li.get_text()
                if ':' in text or '：' in text:
                    if re.match(r'^([^：:]+)(：|:)(.*)$', text):
                        # 直接处理文本内容，不使用复杂的HTML结构
                        original_text = li.get_text()
                        match = re.match(r'^([^：:]+)(：|:)(.*)$', original_text)
                        if match:
                            prefix = match.group(1).strip()
                            colon = match.group(2)
                            suffix = match.group(3).strip()
                            li.clear()
                            li.append(soup.new_tag('strong'))
                            li.strong.string = prefix
                            li.append(colon)
                            if suffix:
                                li.append(suffix)
        
        # 移除所有段落标签，用换行代替
        for p in soup.find_all('p'):
            if p.parent and p.parent.name not in ['li', 'blockquote']:
                # 如果段落不在列表项或引用块中，移除段落标签
                p.unwrap()
        
        # 清理HTML中的多余空白 - 更激进的处理
        html_str = str(soup)
        
        # 移除所有连续的空白行（超过1个）
        html_str = re.sub(r'(\n\s*){2,}', '\n', html_str)
        
        # 移除标签之间的多余空白
        html_str = re.sub(r'>\s+<', '><', html_str)
        
        # 特殊处理：为不同类型的相邻列表添加间距标记
        # 只在ul后面紧跟ol的情况下添加间距类（表示不同内容块）
        html_str = re.sub(r'</ul><ol class="([^"]*)"([^>]*?)>', r'</ul><ol class="\1 list-spacing"\2>', html_str)
        # ol后面紧跟ul表示同一内容块的延续，不添加间距类
        
        # 特别处理列表项之间的空白
        html_str = re.sub(r'</li>\s*<li>', '</li><li>', html_str)
        
        # 移除列表项内部的换行符，使列表更紧凑
        html_str = re.sub(r'<li>\s*\n\s*([^<\n]+)\s*\n\s*</li>', r'<li>\1</li>', html_str)
        
        # 移除段落间多余的空白
        html_str = re.sub(r'</p>\s*<p>', '</p><p>', html_str)
        
        # 移除列表前后的多余空白
        html_str = re.sub(r'</p>\s*<[ou]l', '</p><ol', html_str)
        html_str = re.sub(r'</[ou]l>\s*<p>', '</ol><p>', html_str)
        
        # 移除开头和结尾的空白
        html_str = html_str.strip()
        
        # 将连续的换行符压缩
        html_str = re.sub(r'\n+', '\n', html_str)
        
        # 处理标题和列表之间的空白
        html_str = re.sub(r'</h[1-6]>\s*<[ou]l', '</h1><ol', html_str)
        html_str = re.sub(r'</[ou]l>\s*<h[1-6]', '</ol><h1', html_str)
        
        return html_str
    
    def get_highlight_css(self):
        """
        获取代码高亮所需的CSS样式
        
        Returns:
            代码高亮CSS样式字符串
        """
        # 不再直接返回内联样式，而是指示使用外部CSS文件
        # 这会将Markdown的样式与HTML分离，更加符合Web开发最佳实践
        return """
        /* 此处返回空字符串，因为我们现在使用外部CSS文件 */
        /* 所有样式都已移至 /static/css/chat/markdown.css */
        """
    
    def extract_code_blocks(self, markdown_text):
        """
        从Markdown文本中提取所有代码块
        
        Args:
            markdown_text: Markdown格式的文本
            
        Returns:
            代码块列表，每个元素是 (语言, 代码内容) 的元组
        """
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, markdown_text, re.DOTALL)
        return [(lang or 'text', code) for lang, code in matches]
    
    def highlight_text(self, text, is_code=False, language=''):
        """
        高亮显示文本内容
        
        Args:
            text: 要高亮的文本
            is_code: 是否为代码
            language: 如果是代码，指定语言
            
        Returns:
            高亮后的HTML
        """
        if not is_code:
            return html.escape(text)
        
        try:
            # 规范化语言名称
            language = language.lower().strip()
            language = self.language_aliases.get(language, language)
            
            # 获取对应的词法分析器
            lexer = get_lexer_by_name(language, stripall=True)
            
            # Python代码特殊处理：增强关键字和函数的可读性
            if language == 'python':
                text = self._enhance_python_code(text)
            
            # 高亮代码
            return pygments.highlight(text, lexer, self.html_formatter)
        except Exception:
            # 如果无法获取对应的词法分析器，则使用纯文本格式
            return f'<pre><code>{html.escape(text)}</code></pre>'

    def _highlight_code(self, code, lang):
        """
        根据语言对代码进行语法高亮处理
        
        Args:
            code: 代码内容
            lang: 语言标识
            
        Returns:
            高亮后的HTML代码
        """
        try:
            # 规范化语言名称
            lang = lang.lower().strip()
            lang = self.language_aliases.get(lang, lang)
            
            # 获取对应的词法分析器
            lexer = get_lexer_by_name(lang, stripall=True)
            
            # Python代码特殊处理：增强关键字和函数的可读性
            if lang == 'python':
                code = self._enhance_python_code(code)
            
            # 高亮代码
            highlighted_code = pygments.highlight(code, lexer, self.html_formatter)
            return highlighted_code
        except Exception as e:
            print(f"代码高亮处理错误: {e}")
            # 如果无法获取对应的词法分析器，则使用纯文本格式
            return f'<pre><code>{html.escape(code)}</code></pre>'
            
    def _enhance_python_code(self, code):
        """
        增强Python代码的可读性
        
        Args:
            code: Python代码
            
        Returns:
            增强后的Python代码
        """
        # 确保代码中的缩进使用空格而非制表符
        code = code.replace('\t', '    ')
        
        # 可以在这里添加更多Python代码的特殊处理
        # 例如：格式化注释、突出显示函数名等
        
        return code


# 创建一个全局实例，便于直接导入使用
markdown_processor = MarkdownProcessor() 