import os
import shutil

CORRUPTED_FILE = 'requirements.txt'
BACKUP_FILE = 'requirements.txt.corrupted'
NEW_FILE = 'requirements.txt.new'

# 定义所有需要处理的规则
# (package_name, action, new_line)
# action: 'remove', 'replace'
rules = [
    ('sqlite3', 'remove', None),
    ('zipline', 'remove', None),
    ('talib', 'remove', None),
    ('riskfolio-lib', 'replace', 'riskfolio-lib==7.0.1\n'),
    ('cvxpy', 'replace', 'cvxpy==1.5.2\n'),
]

print(f"--- 开始重建 {CORRUPTED_FILE} ---")

# 1. 安全备份
if os.path.exists(CORRUPTED_FILE):
    shutil.move(CORRUPTED_FILE, BACKUP_FILE)
    print(f"✅ 成功备份旧文件为 {BACKUP_FILE}")

# 2. 读取备份文件并处理
clean_lines = []
packages_to_process = {rule[0] for rule in rules}
processed_packages = set()

with open(BACKUP_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        # 检查是否是需要处理的行
        found_rule = None
        for rule in rules:
            if line.strip().startswith(rule[0]):
                found_rule = rule
                break

        if found_rule:
            pkg_name, action, new_line = found_rule
            if action == 'replace':
                clean_lines.append(new_line)
                print(f"🔄 已替换: {line.strip()} -> {new_line.strip()}")
            elif action == 'remove':
                print(f"❌ 已移除: {line.strip()}")
            processed_packages.add(pkg_name)
        else:
            clean_lines.append(line)

# 确保所有规则都被应用（即使原文件中没有）
for pkg_name, action, new_line in rules:
    if pkg_name not in processed_packages and action == 'replace':
        clean_lines.append(new_line)
        print(f"➕ 已添加缺失的修正: {new_line.strip()}")


# 3. 写入全新的、UTF-8 编码的文件
with open(CORRUPTED_FILE, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print(f"✅ 成功生成全新的 {CORRUPTED_FILE} 文件")
print("--- 重建完成 ---")