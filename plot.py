import json
import matplotlib.pyplot as plt
from collections import Counter


import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
matplotlib.rcParams['axes.unicode_minus'] = False

# 读取 JSON 文件
with open('/home/user05/foretify_checker/result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 统计 error_category
error_categories = [
    item['error_category'] 
    for item in data 
    if item['error_category'] is not None and len(item['error_category'])<10
]

# 计算各错误类型的数量和比率
category_counts = Counter(error_categories)
total_errors = sum(category_counts.values())

# 计算比率
category_ratios = {
    category: count / total_errors * 100 
    for category, count in category_counts.items()
}

# 创建柱状图
plt.figure(figsize=(12, 6))
# sort the category_counts
category_counts = dict(sorted(category_counts.items(), key=lambda x: x[0], reverse=True))
categories = list(category_counts.keys())
counts = list(category_counts.values())
ratios = [f'{count/total_errors*100:.1f}%' for count in counts]

bars = plt.bar(categories, counts, color='steelblue', edgecolor='black')

# 在柱子上添加数值和比率标签
for bar, count, ratio in zip(bars, counts, ratios):
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width()/2., 
        height + 0.5,
        f'{count}\n({ratio})',
        ha='center', 
        va='bottom',
        fontsize=10
    )

# 设置图表样式
plt.title('错误类型分布统计', fontsize=14, fontweight='bold')
plt.xlabel('错误类型', fontsize=12)
plt.ylabel('错误数量', fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.grid(axis='y', alpha=0.3)

# 保存图表
plt.savefig('error_category_distribution.png', dpi=300, bbox_inches='tight')
# plt.show()

# 打印统计信息
print("=" * 50)
print("错误类型统计报告")
print("=" * 50)
print(f"总测试用例数：{len(data)}")
print(f"成功用例数：{sum(1 for item in data if item['status'] == 'success')}")
print(f"失败用例数：{total_errors}")
print(f"成功率：{sum(1 for item in data if item['status'] == 'success')/len(data)*100:.2f}%")
print("=" * 50)
print("\n各错误类型分布：")
for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
    ratio = count / total_errors * 100
    print(f"  {category}: {count} ({ratio:.2f}%)")