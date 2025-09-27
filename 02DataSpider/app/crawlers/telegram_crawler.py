# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - Telegram消息监听器
基于Telethon实现Telegram频道和群组的消息监听
"""

import sys
import os
import re
import json
import asyncio
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

from telethon import TelegramClient, events
from telethon.tl.types import (
    Channel,
    Chat,
    User,
    MessageMediaPhoto,
    MessageMediaDocument,
    PeerChannel,
    PeerChat,
    PeerUser,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    FloodWaitError,
    ChannelPrivateError,
)

from ..config import ConfigManager
from ..utils import Logger
from ..zmq_client import ZMQPublisher, NewsMessage
from .base_crawler import BaseCrawler, CrawlerStatus


class MessageType(Enum):
    """消息类型枚举"""

    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    STICKER = "sticker"
    FORWARD = "forward"


class ChannelType(Enum):
    """频道类型枚举"""

    CHANNEL = "channel"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    BOT = "bot"


@dataclass
class TelegramMessage:
    """Telegram消息数据结构"""

    id: int
    text: str
    sender_id: Optional[int]
    sender_username: Optional[str]
    chat_id: int
    chat_title: str
    chat_username: Optional[str]
    date: datetime
    message_type: MessageType
    media_url: Optional[str] = None
    forward_from: Optional[str] = None
    reply_to_msg_id: Optional[int] = None
    views: Optional[int] = None
    forwards: Optional[int] = None
    reactions: Dict[str, int] = None

    def __post_init__(self):
        if self.reactions is None:
            self.reactions = {}


@dataclass
class ChannelConfig:
    """频道配置"""

    username: str
    channel_id: Optional[int] = None
    keywords: List[str] = None
    exclude_keywords: List[str] = None
    min_views: int = 0
    enabled: bool = True
    category: str = "general"
    priority: int = 1

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.exclude_keywords is None:
            self.exclude_keywords = []


class MessageFilter:
    """消息过滤器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        # 过滤配置
        filter_config = config.get_config("telegram.filters", {})
        self.min_message_length = filter_config.get("min_message_length", 10)
        self.max_message_length = filter_config.get("max_message_length", 10000)
        self.global_keywords = filter_config.get("global_keywords", [])
        self.global_exclude_keywords = filter_config.get("global_exclude_keywords", [])
        self.spam_patterns = filter_config.get("spam_patterns", [])

        # 编译正则表达式
        self.spam_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.spam_patterns
        ]

        self.logger.info("消息过滤器初始化完成")

    def should_process_message(
        self, message: TelegramMessage, channel_config: ChannelConfig
    ) -> bool:
        """判断是否应该处理消息

        Args:
            message: Telegram消息
            channel_config: 频道配置

        Returns:
            是否应该处理
        """
        try:
            # 检查消息长度
            if len(message.text) < self.min_message_length:
                return False

            if len(message.text) > self.max_message_length:
                return False

            # 检查观看次数
            if message.views and message.views < channel_config.min_views:
                return False

            # 检查垃圾信息模式
            if self._is_spam(message.text):
                return False

            # 检查排除关键词
            if self._contains_exclude_keywords(message.text, channel_config):
                return False

            # 检查包含关键词
            if not self._contains_keywords(message.text, channel_config):
                return False

            return True

        except Exception as e:
            self.logger.error(f"消息过滤异常: {e}")
            return False

    def _is_spam(self, text: str) -> bool:
        """检查是否为垃圾信息"""
        for regex in self.spam_regex:
            if regex.search(text):
                return True
        return False

    def _contains_exclude_keywords(
        self, text: str, channel_config: ChannelConfig
    ) -> bool:
        """检查是否包含排除关键词"""
        text_lower = text.lower()

        # 检查全局排除关键词
        for keyword in self.global_exclude_keywords:
            if keyword.lower() in text_lower:
                return True

        # 检查频道特定排除关键词
        for keyword in channel_config.exclude_keywords:
            if keyword.lower() in text_lower:
                return True

        return False

    def _contains_keywords(self, text: str, channel_config: ChannelConfig) -> bool:
        """检查是否包含关键词"""
        # 如果没有配置关键词，则通过
        all_keywords = self.global_keywords + channel_config.keywords
        if not all_keywords:
            return True

        text_lower = text.lower()

        # 检查是否包含任一关键词
        for keyword in all_keywords:
            if keyword.lower() in text_lower:
                return True

        return False


class TelegramCrawler(BaseCrawler):
    """Telegram消息爬虫

    基于Telethon实现Telegram频道和群组的消息监听
    """

    def __init__(
        self,
        config: ConfigManager,
        logger: Logger = None,
        publisher: ZMQPublisher = None,
    ):
        """初始化Telegram爬虫

        Args:
            config: 配置管理器
            logger: 日志记录器
            publisher: ZMQ发布器
        """
        super().__init__(config, logger, publisher)

        # Telegram配置
        self.telegram_config = config.get_config("telegram", {})
        self.api_id = self.telegram_config.get("api_id")
        self.api_hash = self.telegram_config.get("api_hash")
        self.phone_number = self.telegram_config.get("phone_number")
        self.session_name = self.telegram_config.get("session_name", "telegram_crawler")

        # 启用开关（支持字符串布尔）
        self.enabled = self.telegram_config.get("enabled", False)
        if isinstance(self.enabled, str):
            self.enabled = self.enabled.strip().lower() in ("1", "true", "yes", "on")

        # 仅在启用时强制校验凭证
        if self.enabled and (not self.api_id or not self.api_hash):
            # 优雅降级：当启用但缺少凭证时，自动禁用Telegram模块以避免服务启动失败
            self.logger.warning(
                "检测到 telegram.enabled=true 但未配置 TELEGRAM_API_ID/TELEGRAM_API_HASH，将禁用 Telegram 爬虫以保障服务可用性"
            )
            self.enabled = False
        elif not self.enabled and (not self.api_id or not self.api_hash):
            self.logger.info("Telegram 功能被禁用且未配置 API 凭证，将跳过 Telegram 初始化")

        # 频道配置
        self.channels: List[ChannelConfig] = []
        self._load_channel_configs()

        # 消息过滤器
        self.message_filter = MessageFilter(config, self.logger)

        # Telegram客户端
        self.client: Optional[TelegramClient] = None

        # 消息处理器
        self.message_handlers: List[Callable] = []

        # 统计信息
        self.telegram_stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_filtered": 0,
            "channels_monitored": 0,
            "last_message_time": None,
            "connection_errors": 0,
        }

        self.logger.info(f"Telegram爬虫初始化完成，监听 {len(self.channels)} 个频道")

    def _load_channel_configs(self) -> None:
        """加载频道配置"""
        channels_config = self.telegram_config.get("channels", [])

        for channel_data in channels_config:
            if isinstance(channel_data, str):
                # 简单字符串格式
                config = ChannelConfig(username=channel_data)
            elif isinstance(channel_data, dict):
                # 详细配置格式
                config = ChannelConfig(**channel_data)
            else:
                self.logger.warning(f"无效的频道配置: {channel_data}")
                continue

            if config.enabled:
                self.channels.append(config)

        # 默认频道（如果配置为空）
        if not self.channels:
            default_channels = [
                ChannelConfig(
                    username="@cryptonews",
                    keywords=["bitcoin", "ethereum", "crypto"],
                    category="crypto",
                ),
                ChannelConfig(
                    username="@financialnews",
                    keywords=["market", "trading", "finance"],
                    category="finance",
                ),
            ]
            self.channels.extend(default_channels)

    async def initialize_client(self) -> bool:
        """初始化Telegram客户端

        Returns:
            是否初始化成功
        """
        # 禁用时不初始化客户端
        if not getattr(self, "enabled", True):
            self.logger.info("Telegram 爬虫已禁用，跳过客户端初始化")
            return False

        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)

            # 连接客户端
            await self.client.connect()

            # 检查是否已授权
            if not await self.client.is_user_authorized():
                if self.phone_number:
                    await self._authorize_client()
                else:
                    self.logger.error("客户端未授权且未提供手机号")
                    return False

            # 获取当前用户信息
            me = await self.client.get_me()
            self.logger.info(f"Telegram客户端初始化成功，用户: {me.username or me.first_name}")

            return True

        except Exception as e:
            self.logger.error(f"Telegram客户端初始化失败: {e}")
            return False

    async def _authorize_client(self) -> None:
        """授权客户端"""
        try:
            # 发送验证码
            await self.client.send_code_request(self.phone_number)

            # 这里需要手动输入验证码（在实际部署中可能需要其他方式）
            self.logger.info(f"验证码已发送到 {self.phone_number}")
            self.logger.warning("请手动完成Telegram授权流程")

        except Exception as e:
            self.logger.error(f"Telegram授权失败: {e}")
            raise

    async def start_monitoring(self) -> None:
        """开始监听消息"""
        # 禁用时直接返回
        if not getattr(self, "enabled", True):
            self.logger.info("Telegram 爬虫已禁用（telegram.enabled=false），跳过启动")
            self.status = CrawlerStatus.IDLE
            return

        if not self.client:
            if not await self.initialize_client():
                return

        self.status = CrawlerStatus.RUNNING
        self.start_time = datetime.utcnow()

        self.logger.info("开始监听Telegram消息")

        try:
            # 注册消息处理器
            @self.client.on(events.NewMessage)
            async def message_handler(event):
                await self._handle_new_message(event)

            # 加入监听的频道
            await self._join_channels()

            # 开始监听
            self.logger.info("Telegram消息监听已启动")
            await self.client.run_until_disconnected()

        except Exception as e:
            self.status = CrawlerStatus.ERROR
            self.telegram_stats["connection_errors"] += 1
            self.logger.error(f"Telegram监听异常: {e}")
        finally:
            self.status = CrawlerStatus.IDLE
            self.stop_time = datetime.utcnow()
            self.logger.info("Telegram消息监听结束")

    async def _join_channels(self) -> None:
        """加入监听的频道"""
        joined_count = 0

        for channel_config in self.channels:
            try:
                # 获取频道实体
                entity = await self.client.get_entity(channel_config.username)

                # 如果是私有频道，尝试加入
                if isinstance(entity, Channel) and not entity.broadcast:
                    try:
                        await self.client(JoinChannelRequest(entity))
                        self.logger.info(f"已加入频道: {channel_config.username}")
                    except Exception as e:
                        self.logger.warning(f"无法加入频道 {channel_config.username}: {e}")

                # 更新频道ID
                channel_config.channel_id = entity.id
                joined_count += 1

            except ChannelPrivateError:
                self.logger.warning(f"频道 {channel_config.username} 为私有频道")
            except Exception as e:
                self.logger.error(f"获取频道 {channel_config.username} 失败: {e}")

        self.telegram_stats["channels_monitored"] = joined_count
        self.logger.info(f"成功监听 {joined_count} 个频道")

    async def _handle_new_message(self, event) -> None:
        """处理新消息

        Args:
            event: Telegram消息事件
        """
        try:
            self.telegram_stats["messages_received"] += 1
            self.telegram_stats["last_message_time"] = datetime.utcnow().isoformat()

            # 解析消息
            telegram_message = await self._parse_message(event)
            if not telegram_message:
                return

            # 查找对应的频道配置
            channel_config = self._find_channel_config(telegram_message.chat_id)
            if not channel_config:
                return

            # 过滤消息
            if not self.message_filter.should_process_message(
                telegram_message, channel_config
            ):
                self.telegram_stats["messages_filtered"] += 1
                return

            # 处理消息
            await self._process_message(telegram_message, channel_config)

            self.telegram_stats["messages_processed"] += 1
            self.stats["items_scraped"] += 1

        except Exception as e:
            self.logger.error(f"处理Telegram消息异常: {e}")

    async def _parse_message(self, event) -> Optional[TelegramMessage]:
        """解析Telegram消息

        Args:
            event: Telegram消息事件

        Returns:
            解析的消息对象
        """
        try:
            message = event.message

            # 获取发送者信息
            sender = await message.get_sender()
            sender_id = sender.id if sender else None
            sender_username = getattr(sender, "username", None)

            # 获取聊天信息
            chat = await message.get_chat()
            chat_title = getattr(chat, "title", "") or getattr(chat, "first_name", "")
            chat_username = getattr(chat, "username", None)

            # 确定消息类型
            message_type = MessageType.TEXT
            media_url = None

            if message.media:
                if isinstance(message.media, MessageMediaPhoto):
                    message_type = MessageType.PHOTO
                elif isinstance(message.media, MessageMediaDocument):
                    if message.media.document.mime_type.startswith("video/"):
                        message_type = MessageType.VIDEO
                    elif message.media.document.mime_type.startswith("audio/"):
                        message_type = MessageType.AUDIO
                    else:
                        message_type = MessageType.DOCUMENT

            # 检查是否为转发消息
            forward_from = None
            if message.forward:
                if message.forward.from_name:
                    forward_from = message.forward.from_name
                elif message.forward.chat:
                    forward_from = getattr(message.forward.chat, "title", "Unknown")
                if forward_from:
                    message_type = MessageType.FORWARD

            # 获取反应数据
            reactions = {}
            if hasattr(message, "reactions") and message.reactions:
                for reaction in message.reactions.results:
                    emoji = (
                        reaction.reaction.emoticon
                        if hasattr(reaction.reaction, "emoticon")
                        else str(reaction.reaction)
                    )
                    reactions[emoji] = reaction.count

            return TelegramMessage(
                id=message.id,
                text=message.text or "",
                sender_id=sender_id,
                sender_username=sender_username,
                chat_id=message.chat_id,
                chat_title=chat_title,
                chat_username=chat_username,
                date=message.date,
                message_type=message_type,
                media_url=media_url,
                forward_from=forward_from,
                reply_to_msg_id=message.reply_to_msg_id,
                views=getattr(message, "views", None),
                forwards=getattr(message, "forwards", None),
                reactions=reactions,
            )

        except Exception as e:
            self.logger.error(f"解析Telegram消息失败: {e}")
            return None

    def _find_channel_config(self, chat_id: int) -> Optional[ChannelConfig]:
        """查找频道配置

        Args:
            chat_id: 聊天ID

        Returns:
            频道配置或None
        """
        for config in self.channels:
            if config.channel_id == chat_id:
                return config
        return None

    async def _process_message(
        self, telegram_message: TelegramMessage, channel_config: ChannelConfig
    ) -> None:
        """处理消息

        Args:
            telegram_message: Telegram消息
            channel_config: 频道配置
        """
        try:
            # 创建新闻消息
            news_message = NewsMessage(
                id=f"tg_{telegram_message.chat_id}_{telegram_message.id}",
                title=self._extract_title(telegram_message.text),
                content=telegram_message.text,
                source=f"telegram_{channel_config.username}",
                url=self._generate_message_url(telegram_message),
                timestamp=telegram_message.date.isoformat(),
                category=channel_config.category,
                sentiment=None,  # 将在后续处理中分析
                keywords=self._extract_keywords(telegram_message.text),
                metadata={
                    "telegram_message_id": telegram_message.id,
                    "telegram_chat_id": telegram_message.chat_id,
                    "telegram_chat_title": telegram_message.chat_title,
                    "telegram_sender_id": telegram_message.sender_id,
                    "telegram_sender_username": telegram_message.sender_username,
                    "telegram_message_type": telegram_message.message_type.value,
                    "telegram_views": telegram_message.views,
                    "telegram_forwards": telegram_message.forwards,
                    "telegram_reactions": telegram_message.reactions,
                    "telegram_forward_from": telegram_message.forward_from,
                    "channel_priority": channel_config.priority,
                    "extraction_time": datetime.utcnow().isoformat(),
                },
            )

            # 发布到ZMQ
            if self.publisher:
                self.publisher.publish_message(news_message)

            # 调用自定义处理器
            for handler in self.message_handlers:
                try:
                    await handler(telegram_message, channel_config)
                except Exception as e:
                    self.logger.error(f"自定义消息处理器异常: {e}")

            self.logger.info(
                f"处理Telegram消息: {telegram_message.chat_title} | "
                f"ID: {telegram_message.id} | "
                f"类型: {telegram_message.message_type.value}"
            )

        except Exception as e:
            self.logger.error(f"处理Telegram消息失败: {e}")

    def _extract_title(self, text: str) -> str:
        """从消息文本中提取标题

        Args:
            text: 消息文本

        Returns:
            提取的标题
        """
        if not text:
            return "Telegram消息"

        # 取第一行作为标题
        lines = text.split("\n")
        title = lines[0].strip()

        # 限制标题长度
        if len(title) > 100:
            title = title[:97] + "..."

        return title or "Telegram消息"

    def _generate_message_url(self, telegram_message: TelegramMessage) -> Optional[str]:
        """生成消息URL

        Args:
            telegram_message: Telegram消息

        Returns:
            消息URL
        """
        if telegram_message.chat_username:
            return f"https://t.me/{telegram_message.chat_username.lstrip('@')}/{telegram_message.id}"
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词

        Args:
            text: 文本内容

        Returns:
            关键词列表
        """
        if not text:
            return []

        # 金融和加密货币相关关键词
        financial_keywords = [
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "cryptocurrency",
            "blockchain",
            "defi",
            "nft",
            "trading",
            "market",
            "price",
            "bull",
            "bear",
            "pump",
            "dump",
            "moon",
            "lambo",
            "hodl",
            "altcoin",
            "shitcoin",
            "gem",
            "signal",
            "analysis",
            "breakout",
            "support",
            "resistance",
            "volume",
            "listing",
            "binance",
            "coinbase",
            "exchange",
            "announcement",
            "news",
        ]

        text_lower = text.lower()
        found_keywords = []

        for keyword in financial_keywords:
            # 使用正则表达式进行边界匹配，确保只匹配完整的单词
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, text_lower):
                found_keywords.append(keyword)

        # 提取hashtags
        hashtags = re.findall(r"#\w+", text)
        found_keywords.extend([tag.lower() for tag in hashtags])

        return list(set(found_keywords))  # 去重

    def should_process_message(self, message) -> bool:
        """判断是否应该处理消息（简化版本用于测试）

        Args:
            message: 消息对象

        Returns:
            是否应该处理
        """
        try:
            # 获取消息文本
            text = getattr(message, "text", "")
            if not text:
                return False

            # 检查是否包含关键词
            keywords = self.telegram_config.get("keywords", [])
            if not keywords:
                return True

            text_lower = text.lower()
            for keyword in keywords:
                # 使用正则表达式进行边界匹配，确保只匹配完整的单词
                pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                if re.search(pattern, text_lower):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"消息过滤异常: {e}")
            return False

    def extract_keywords_from_message(self, message) -> List[str]:
        """从消息中提取关键词（用于测试）

        Args:
            message: 消息对象

        Returns:
            关键词列表
        """
        try:
            text = getattr(message, "text", "")
            return self._extract_keywords(text)
        except Exception as e:
            self.logger.error(f"关键词提取异常: {e}")
            return []

    def extract_message_data(self, message, chat):
        """提取消息数据（用于测试）"""
        return {
            "message_id": message.id,
            "text": message.text,
            "timestamp": message.date,
            "sender_id": getattr(message, "sender_id", None),
            "chat_id": chat.id,
            "chat_title": chat.title,
            "chat_username": getattr(chat, "username", None),
            "views": getattr(message, "views", None),
            "forwards": getattr(message, "forwards", None),
            "keywords": self.extract_keywords_from_message(message),
        }

    def add_message_handler(self, handler: Callable) -> None:
        """添加自定义消息处理器

        Args:
            handler: 消息处理函数
        """
        self.message_handlers.append(handler)
        self.logger.info(f"添加消息处理器: {handler.__name__}")

    def get_start_urls(self) -> List[str]:
        """获取起始URL列表（Telegram爬虫不使用URL）

        Returns:
            空列表
        """
        return []

    def parse_response(self, response) -> List[Dict[str, Any]]:
        """解析响应内容（Telegram爬虫不使用HTTP响应）

        Args:
            response: 响应对象

        Returns:
            空列表
        """
        return []

    def extract_links(self, response) -> List[str]:
        """提取页面链接（Telegram爬虫不使用链接）

        Args:
            response: 响应对象

        Returns:
            空列表
        """
        return []

    def start_crawling(self) -> None:
        """开始爬取（异步版本）"""
        try:
            # 运行异步监听
            asyncio.run(self.start_monitoring())
        except Exception as e:
            self.logger.error(f"启动Telegram爬虫失败: {e}")

    async def stop_monitoring(self) -> None:
        """停止监听"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("Telegram客户端已断开连接")

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息（扩展版本）

        Returns:
            统计信息字典
        """
        stats = super().get_stats()

        # 添加Telegram特定统计
        stats.update(self.telegram_stats)

        # 计算消息处理率
        if self.telegram_stats["messages_received"] > 0:
            stats["message_processing_rate"] = (
                self.telegram_stats["messages_processed"]
                / self.telegram_stats["messages_received"]
            )
        else:
            stats["message_processing_rate"] = 0.0

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查（扩展版本）

        Returns:
            健康状态信息
        """
        health = super().health_check()

        # 添加Telegram特定健康检查
        if self.client and self.client.is_connected():
            connection_status = "connected"
        else:
            connection_status = "disconnected"

        health.update(
            {
                "telegram_connection": connection_status,
                "channels_monitored": self.telegram_stats["channels_monitored"],
                "messages_received": self.telegram_stats["messages_received"],
                "messages_processed": self.telegram_stats["messages_processed"],
                "connection_errors": self.telegram_stats["connection_errors"],
            }
        )

        return health

    def __del__(self):
        """析构函数"""
        if hasattr(self, "client") and self.client:
            try:
                asyncio.run(self.stop_monitoring())
            except Exception:
                pass


if __name__ == "__main__":
    # 测试Telegram爬虫
    from ..config import ConfigManager
    from ..utils import Logger
    from ..zmq_client import ZMQPublisher

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建ZMQ发布器（可选）
    try:
        publisher = ZMQPublisher(config, logger)
    except Exception as e:
        logger.warning(f"无法创建ZMQ发布器: {e}")
        publisher = None

    # 创建Telegram爬虫
    crawler = TelegramCrawler(config, logger, publisher)

    # 测试爬取
    print("开始测试Telegram爬虫...")
    print("注意：需要先配置Telegram API凭据")

    try:
        crawler.start_crawling()
    except Exception as e:
        print(f"测试失败: {e}")

    # 显示统计信息
    stats = crawler.get_stats()
    print(f"\n爬虫统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # 健康检查
    health = crawler.health_check()
    print(f"\n健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
