#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志处理脚本 - 解析 foretify 处理日志并分类失败原因
"""

import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ProcessStatus(Enum):
    """处理状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class CaseResult:
    """单个 case 的处理结果"""
    case_name: str
    status: str
    file_path: str
    error_reason: Optional[str] = None
    error_category: Optional[str] = None
    line_number: Optional[int] = None


class LogParser:
    """日志解析器"""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.raw_content = ""
        self.case_results: List[CaseResult] = []
        
        # 正则表达式模式
        self.pattern_file = re.compile(r'处理文件:\s*(.+\.osc)')
        self.pattern_success = re.compile(r'✅\s*文件\s+(\S+\.osc)\s+处理成功')
        self.pattern_failed = re.compile(r'❌\s*文件\s+(\S+\.osc)\s+处理失败')
        self.pattern_error = re.compile(r'错误详情:\s*(.+)')
        self.pattern_line = re.compile(r'line\s+(\d+)')
    
    def load_log(self) -> bool:
        """加载日志文件"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                self.raw_content = f.read()
            return True
        except Exception as e:
            print(f"加载日志文件失败：{e}")
            return False
    
    def split_cases(self) -> List[str]:
        """按处理文件标记切分日志块"""
        # 找到所有 "处理文件:" 的位置
        pattern = re.compile(r'处理文件:\s*(.+\.osc)')
        matches = list(pattern.finditer(self.raw_content))
        
        cases = []
        for i, match in enumerate(matches):
            start = match.start()
            # 找到下一个 "处理文件:" 或文件结尾
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(self.raw_content)
            
            case_block = self.raw_content[start:end]
            cases.append(case_block)
        
        return cases
    
    def parse_case(self, case_block: str) -> Optional[CaseResult]:
        """解析单个 case 块"""
        # 提取文件路径
        file_match = self.pattern_file.search(case_block)
        if not file_match:
            return None
        
        file_path = file_match.group(1).strip()
        
        # 从文件路径中提取 case 名称（文件名不含扩展名）
        import os
        case_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 判断处理状态
        if self.pattern_success.search(case_block):
            status = ProcessStatus.SUCCESS.value
            error_reason = None
        elif self.pattern_failed.search(case_block):
            status = ProcessStatus.FAILED.value
            # 提取错误详情
            error_match = self.pattern_error.search(case_block)
            if error_match:
                # 提取 "错误详情:" 之后的所有内容
                error_start = error_match.start()
                error_text = case_block[error_start:]
                # 提取所有 [ERROR] 行
                error_lines = re.findall(r'\[ERROR\][^\n]+', error_text)
                error_reason = "\n".join(error_lines) if error_lines else "未知错误"
            else:
                error_reason = "未知错误"
        else:
            status = ProcessStatus.UNKNOWN.value
            error_reason = None
        
        # 提取行号
        line_match = self.pattern_line.search(error_reason) if error_reason else None
        line_number = int(line_match.group(1)) if line_match else None
        
        return CaseResult(
            case_name=case_name,
            status=status,
            file_path=file_path,
            error_reason=error_reason,
            line_number=line_number
        )
    
    def parse_all(self) -> List[CaseResult]:
        """解析所有 case"""
        if not self.raw_content:
            if not self.load_log():
                return []
        
        case_blocks = self.split_cases()
        for block in case_blocks:
            result = self.parse_case(block)
            if result:
                self.case_results.append(result)
        
        return self.case_results
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.case_results)
        success = sum(1 for r in self.case_results if r.status == ProcessStatus.SUCCESS.value)
        failed = sum(1 for r in self.case_results if r.status == ProcessStatus.FAILED.value)
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": f"{success/total*100:.2f}%" if total > 0 else "0%"
        }


class ErrorClassifier:
    """错误原因分类器（支持 OpenAI 格式 LLM API）"""
    
    ERROR_CATEGORIES = {
        "文件导入失败": ["Cannot read file", "Failed to locate file", "Imported by"],
        "解析错误": ["Parsing error", "token recognition error", "no viable alternative"],
        "类型不匹配": ["Operator '==' is not applicable", "type of", "not 'range of length'"],
        "变量未定义": ["Could not locate", "Failed to resolve path expression", "not found in scope"],
        "继承类型缺失": ["Inherited type", "not found"],
        "语法错误": ["is not legal in this context", "Failed to resolve type reference", "unresolved due to ambiguity", "'do' is not legal", "'keep' is not legal"],
        "场景引用错误": ["Could not locate scenario"],
        "道路元素错误": ["road element", "roundabout_entry"],
        "其他": []
    }
    
    def __init__(self, use_llm: bool = False, api_key: str = "", api_url: str = "", model: str = "qwen-plus"):
        """
        初始化分类器
        
        Args:
            use_llm: 是否使用大模型 API
            api_key: 大模型 API 密钥
            api_url: 大模型 API 地址
            model: 模型名称
        """
        self.use_llm = use_llm
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
    
    def classify_by_rules(self, error_reason: str) -> str:
        """基于规则分类"""
        if not error_reason:
            return "未知"
        
        for category, keywords in self.ERROR_CATEGORIES.items():
            if category == "其他":
                continue
            for keyword in keywords:
                if keyword.lower() in error_reason.lower():
                    return category
        
        return "其他"
    
    def remove_think_tags(self, text):
        import re
        # 使用正则表达式移除 
        if '<think>'  in text:
            return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        elif '</think>'  in text:
            return re.sub(r'.*?</think>', '', text, flags=re.DOTALL)
        return text

    def classify_by_llm(self, error_reason: str) -> str:
        """使用 OpenAI 格式调用大模型 API 分类"""
        if not self.api_key or not self.api_url:
            return self.classify_by_rules(error_reason)
        
        try:
            import requests
            
            # OpenAI 标准格式请求
            prompt = f"""请对以下 OSC 场景文件处理错误进行分类，分类选项包括：
- 文件导入失败
- 解析错误
- 类型不匹配
- 变量未定义
- 继承类型缺失
- 语法错误
- 场景引用错误
- 道路元素错误
- 其他

错误信息：{error_reason}

请直接返回分类名称，不要其他内容。"""
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenAI 标准请求格式
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个日志错误分类助手，请将错误信息分类到指定的类别中。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
                "stream": False
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            #print(result)
            # OpenAI 标准响应格式解析
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                content = self.remove_think_tags(content)
                return content.strip()
            
            return self.classify_by_rules(error_reason)
            
        except Exception as e:
            print(f"大模型分类失败，回退到规则分类：{e}")
            return self.classify_by_rules(error_reason)
    
    def classify(self, error_reason: str) -> str:
        """分类入口"""
        if self.use_llm:
            return self.classify_by_llm(error_reason)
        return self.classify_by_rules(error_reason)


def export_results(results: List[CaseResult], output_file: str, format: str = "json", sort_by: str = "case_name"):
    """
    导出结果
    
    Args:
        results: 结果列表
        output_file: 输出文件路径
        format: 输出格式 (json/csv)
        sort_by: 排序字段 (case_name/status)
    """
    # 对结果进行排序
    sorted_results = sorted(results, key=lambda x: getattr(x, sort_by, "case_name"))
    data = [asdict(r) for r in sorted_results]
    
    if format == "json":
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif format == "csv":
        import csv
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys() if data else [])
            writer.writeheader()
            writer.writerows(data)
    
    print(f"结果已导出到：{output_file}（已按 {sort_by} 排序）")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="处理 foretify 日志文件")
    parser.add_argument("--log", type=str, default="/home/user05/foretify_checker/log_jsonl.txt", help="日志文件路径")
    parser.add_argument("--output", type=str, default="result.json", help="输出文件路径")
    parser.add_argument("--format", type=str, choices=["json", "csv"], default="json", help="输出格式")
    parser.add_argument("--sort-by", type=str, choices=["case_name", "status"], default="case_name", help="排序字段")
    parser.add_argument("--use-llm", default=False, action="store_true", help="使用大模型 API 分类")
    parser.add_argument("--api-key", type=str, default="EMPTY", help="大模型 API 密钥")
    parser.add_argument("--api-url", type=str, default="http://10.160.199.235:8005/v1/chat/completions", help="大模型 API 地址")
    parser.add_argument("--model", type=str, default="reject-model", help="模型名称")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("开始解析日志文件...")
    print("=" * 60)
    
    log_parser = LogParser(args.log)
    results = log_parser.parse_all()
    
    print(f"\n共解析 {len(results)} 个 case")
    print("正在进行错误分类...")
    
    classifier = ErrorClassifier(
        use_llm=args.use_llm,
        api_key=args.api_key,
        api_url=args.api_url,
        model=args.model
    )
    
    for result in results:
        if result.status == ProcessStatus.FAILED.value and result.error_reason:
            result.error_category = classifier.classify(result.error_reason)
    
    stats = log_parser.get_statistics()
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    print(f"总 case 数：{stats['total']}")
    print(f"成功：{stats['success']}")
    print(f"失败：{stats['failed']}")
    print(f"成功率：{stats['success_rate']}")
    
    if any(r.error_category for r in results):
        print("\n错误分类统计:")
        category_count = {}
        for r in results:
            if r.error_category:
                category_count[r.error_category] = category_count.get(r.error_category, 0) + 1
        for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
    
    export_results(results, args.output, args.format, args.sort_by)
    
    failed_cases = [r for r in results if r.status == ProcessStatus.FAILED.value]
    if failed_cases:
        print("\n" + "=" * 60)
        print("失败 Case 详情")
        print("=" * 60)
        for case in failed_cases[:10]:
            print(f"\n📁 Case: {case.case_name}")
            print(f"   分类：{case.error_category}")
            print(f"   原因：{case.error_reason[:100]}..." if case.error_reason and len(case.error_reason) > 100 else f"   原因：{case.error_reason}")


if __name__ == "__main__":
    main()