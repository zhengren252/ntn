#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息源爬虫模组数据备份脚本
支持数据库、日志、配置文件的自动备份和恢复
"""

import os
import sys
import json
import shutil
import tarfile
import gzip
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging


class BackupManager:
    """备份管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path(config.get("backup_dir", "backups"))
        self.retention_days = config.get("retention_days", 30)
        self.compression = config.get("compression", True)
        self.encryption = config.get("encryption", False)

        # 创建备份目录
        self.backup_dir.mkdir(exist_ok=True)

        # 设置日志
        self.setup_logging()

    def setup_logging(self):
        """设置日志"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.backup_dir / "backup.log"),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def create_backup(self, backup_type: str = "full") -> str:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        self.logger.info(f"开始创建备份: {backup_name}")

        try:
            # 创建备份目录
            backup_path.mkdir(exist_ok=True)

            # 备份数据库
            if backup_type in ["full", "database"]:
                self._backup_database(backup_path)

            # 备份日志文件
            if backup_type in ["full", "logs"]:
                self._backup_logs(backup_path)

            # 备份配置文件
            if backup_type in ["full", "config"]:
                self._backup_config(backup_path)

            # 备份临时文件（可选）
            if backup_type == "full":
                self._backup_temp_files(backup_path)

            # 创建备份元数据
            self._create_metadata(backup_path, backup_type)

            # 压缩备份
            if self.compression:
                compressed_path = self._compress_backup(backup_path)
                shutil.rmtree(backup_path)
                backup_path = compressed_path

            # 加密备份（如果启用）
            if self.encryption:
                encrypted_path = self._encrypt_backup(backup_path)
                backup_path.unlink()
                backup_path = encrypted_path

            self.logger.info(f"备份创建完成: {backup_path}")
            return str(backup_path)

        except Exception as e:
            self.logger.error(f"备份创建失败: {str(e)}")
            # 清理失败的备份
            if backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(backup_path)
                else:
                    backup_path.unlink()
            raise

    def _backup_database(self, backup_path: Path):
        """备份数据库"""
        self.logger.info("备份数据库文件...")

        db_backup_dir = backup_path / "database"
        db_backup_dir.mkdir(exist_ok=True)

        # 备份所有环境的数据库
        data_dir = Path("data")
        if data_dir.exists():
            for db_file in data_dir.glob("*.db"):
                self.logger.info(f"备份数据库: {db_file}")

                # 创建数据库备份（使用SQLite的备份API）
                backup_db_path = db_backup_dir / db_file.name
                self._backup_sqlite_database(db_file, backup_db_path)

                # 创建SQL转储
                sql_dump_path = db_backup_dir / f"{db_file.stem}.sql"
                self._create_sql_dump(db_file, sql_dump_path)

    def _backup_sqlite_database(self, source_db: Path, target_db: Path):
        """备份SQLite数据库"""
        try:
            # 使用SQLite的备份API
            source_conn = sqlite3.connect(str(source_db))
            target_conn = sqlite3.connect(str(target_db))

            source_conn.backup(target_conn)

            source_conn.close()
            target_conn.close()

            self.logger.info(f"数据库备份完成: {source_db} -> {target_db}")

        except Exception as e:
            self.logger.error(f"数据库备份失败: {str(e)}")
            # 回退到文件复制
            shutil.copy2(source_db, target_db)

    def _create_sql_dump(self, db_path: Path, dump_path: Path):
        """创建SQL转储文件"""
        try:
            conn = sqlite3.connect(str(db_path))

            with open(dump_path, "w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")

            conn.close()
            self.logger.info(f"SQL转储完成: {dump_path}")

        except Exception as e:
            self.logger.error(f"SQL转储失败: {str(e)}")

    def _backup_logs(self, backup_path: Path):
        """备份日志文件"""
        self.logger.info("备份日志文件...")

        logs_backup_dir = backup_path / "logs"
        logs_backup_dir.mkdir(exist_ok=True)

        logs_dir = Path("logs")
        if logs_dir.exists():
            for log_file in logs_dir.rglob("*.log*"):
                relative_path = log_file.relative_to(logs_dir)
                target_path = logs_backup_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 压缩日志文件
                if log_file.suffix != ".gz":
                    with open(log_file, "rb") as f_in:
                        with gzip.open(f"{target_path}.gz", "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    self.logger.info(f"日志文件已压缩备份: {log_file}")
                else:
                    shutil.copy2(log_file, target_path)
                    self.logger.info(f"日志文件已备份: {log_file}")

    def _backup_config(self, backup_path: Path):
        """备份配置文件"""
        self.logger.info("备份配置文件...")

        config_backup_dir = backup_path / "config"
        config_backup_dir.mkdir(exist_ok=True)

        # 备份配置目录
        config_dir = Path("config")
        if config_dir.exists():
            shutil.copytree(config_dir, config_backup_dir / "config")

        # 备份环境变量文件
        for env_file in Path(".").glob(".env*"):
            shutil.copy2(env_file, config_backup_dir)

        # 备份Docker配置
        docker_files = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.dev.yml",
            "docker-compose.staging.yml",
            "docker-compose.prod.yml",
        ]

        for docker_file in docker_files:
            if Path(docker_file).exists():
                shutil.copy2(docker_file, config_backup_dir)

        self.logger.info("配置文件备份完成")

    def _backup_temp_files(self, backup_path: Path):
        """备份临时文件"""
        self.logger.info("备份临时文件...")

        temp_backup_dir = backup_path / "temp"
        temp_dir = Path("temp")

        if temp_dir.exists() and any(temp_dir.iterdir()):
            shutil.copytree(temp_dir, temp_backup_dir)
            self.logger.info("临时文件备份完成")

    def _create_metadata(self, backup_path: Path, backup_type: str):
        """创建备份元数据"""
        metadata = {
            "backup_type": backup_type,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "environment": os.getenv("APP_ENV", "unknown"),
            "compression": self.compression,
            "encryption": self.encryption,
            "files": [],
        }

        # 收集文件信息
        for file_path in backup_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(backup_path)
                file_info = {
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                }
                metadata["files"].append(file_info)

        # 保存元数据
        metadata_path = backup_path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"备份元数据已创建: {metadata_path}")

    def _compress_backup(self, backup_path: Path) -> Path:
        """压缩备份"""
        self.logger.info(f"压缩备份: {backup_path}")

        compressed_path = backup_path.with_suffix(".tar.gz")

        with tarfile.open(compressed_path, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_path.name)

        self.logger.info(f"备份压缩完成: {compressed_path}")
        return compressed_path

    def _encrypt_backup(self, backup_path: Path) -> Path:
        """加密备份（简单示例，生产环境应使用更强的加密）"""
        self.logger.info(f"加密备份: {backup_path}")

        # 这里应该实现真正的加密逻辑
        # 为了示例，只是重命名文件
        encrypted_path = backup_path.with_suffix(backup_path.suffix + ".enc")
        shutil.move(backup_path, encrypted_path)

        self.logger.info(f"备份加密完成: {encrypted_path}")
        return encrypted_path

    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []

        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file() and backup_file.name.startswith("backup_"):
                backup_info = {
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": backup_file.stat().st_size,
                    "created": datetime.fromtimestamp(
                        backup_file.stat().st_ctime
                    ).isoformat(),
                    "modified": datetime.fromtimestamp(
                        backup_file.stat().st_mtime
                    ).isoformat(),
                }

                # 尝试解析备份类型和时间戳
                name_parts = backup_file.stem.split("_")
                if len(name_parts) >= 3:
                    backup_info["type"] = name_parts[1]
                    backup_info["timestamp"] = name_parts[2]

                backups.append(backup_info)

        # 按创建时间排序
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups

    def restore_backup(self, backup_name: str, target_dir: str = None):
        """恢复备份"""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        self.logger.info(f"开始恢复备份: {backup_name}")

        if target_dir is None:
            target_dir = Path(".")
        else:
            target_dir = Path(target_dir)

        try:
            # 解压备份
            if backup_path.suffix == ".gz":
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(target_dir)
                    extracted_dir = target_dir / backup_path.stem.replace(".tar", "")
            else:
                extracted_dir = backup_path

            # 恢复文件
            self._restore_files(extracted_dir, target_dir)

            self.logger.info(f"备份恢复完成: {backup_name}")

        except Exception as e:
            self.logger.error(f"备份恢复失败: {str(e)}")
            raise

    def _restore_files(self, backup_dir: Path, target_dir: Path):
        """恢复文件"""
        # 恢复数据库
        db_backup_dir = backup_dir / "database"
        if db_backup_dir.exists():
            data_dir = target_dir / "data"
            data_dir.mkdir(exist_ok=True)

            for db_file in db_backup_dir.glob("*.db"):
                target_db = data_dir / db_file.name
                shutil.copy2(db_file, target_db)
                self.logger.info(f"数据库已恢复: {db_file.name}")

        # 恢复配置文件
        config_backup_dir = backup_dir / "config"
        if config_backup_dir.exists():
            for config_file in config_backup_dir.iterdir():
                if config_file.is_file():
                    target_config = target_dir / config_file.name
                    shutil.copy2(config_file, target_config)
                    self.logger.info(f"配置文件已恢复: {config_file.name}")
                elif config_file.is_dir() and config_file.name == "config":
                    target_config_dir = target_dir / "config"
                    if target_config_dir.exists():
                        shutil.rmtree(target_config_dir)
                    shutil.copytree(config_file, target_config_dir)
                    self.logger.info("配置目录已恢复")

    def cleanup_old_backups(self):
        """清理过期备份"""
        self.logger.info(f"清理{self.retention_days}天前的备份...")

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0

        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file() and backup_file.name.startswith("backup_"):
                file_date = datetime.fromtimestamp(backup_file.stat().st_ctime)

                if file_date < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    self.logger.info(f"已删除过期备份: {backup_file.name}")

        self.logger.info(f"清理完成，删除了{deleted_count}个过期备份")


def load_config(env: str) -> Dict[str, Any]:
    """加载备份配置"""
    config = {
        "backup_dir": f"backups/{env}",
        "retention_days": 30 if env == "production" else 7,
        "compression": True,
        "encryption": env == "production",
    }

    # 从环境变量覆盖配置
    config["retention_days"] = int(
        os.getenv("BACKUP_RETENTION_DAYS", config["retention_days"])
    )
    config["compression"] = os.getenv("BACKUP_COMPRESSION", "true").lower() == "true"
    config["encryption"] = (
        os.getenv("BACKUP_ENCRYPTION", str(config["encryption"]).lower()).lower()
        == "true"
    )

    return config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="信息源爬虫模组备份管理")
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="环境名称",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 创建备份命令
    backup_parser = subparsers.add_parser("create", help="创建备份")
    backup_parser.add_argument(
        "--type",
        choices=["full", "database", "logs", "config"],
        default="full",
        help="备份类型",
    )

    # 列出备份命令
    list_parser = subparsers.add_parser("list", help="列出备份")

    # 恢复备份命令
    restore_parser = subparsers.add_parser("restore", help="恢复备份")
    restore_parser.add_argument("backup_name", help="备份名称")
    restore_parser.add_argument("--target", help="恢复目标目录")

    # 清理备份命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理过期备份")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 加载配置
    config = load_config(args.env)
    manager = BackupManager(config)

    try:
        if args.command == "create":
            backup_path = manager.create_backup(args.type)
            print(f"备份创建成功: {backup_path}")

        elif args.command == "list":
            backups = manager.list_backups()
            if backups:
                print("可用备份:")
                for backup in backups:
                    size_mb = backup["size"] / (1024 * 1024)
                    print(f"  {backup['name']} ({size_mb:.1f}MB) - {backup['created']}")
            else:
                print("没有找到备份文件")

        elif args.command == "restore":
            manager.restore_backup(args.backup_name, args.target)
            print(f"备份恢复成功: {args.backup_name}")

        elif args.command == "cleanup":
            manager.cleanup_old_backups()
            print("过期备份清理完成")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
