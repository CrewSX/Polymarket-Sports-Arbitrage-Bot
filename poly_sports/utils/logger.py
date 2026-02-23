"""Logger module with colorful output and emoji icons"""
import os
import sys
import platform
import socket
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import aiohttp
import aiofiles

LogLevel = Literal['trace', 'debug', 'info', 'warn', 'error', 'fatal']


class Logger:
    """A beautiful, colorful logger with emoji icons and timestamp support"""
    
    def __init__(self):
        self.colors = {
            'reset': '\033[0m',
            'trace': '\033[90m',
            'debug': '\033[36m',
            'info': '\033[32m',
            'warn': '\033[33m',
            'error': '\033[31m',
            'fatal': '\033[35m',
        }
        
        self.level_icons = {
            'trace': '🔍',
            'debug': '🐛',
            'info': 'ℹ️',
            'warn': '⚠️',
            'error': '❌',
            'fatal': '💀',
        }
    
    def format_timestamp(self) -> str:
        """Format current timestamp as ISO 8601"""
        return datetime.now().isoformat()
    
    def format_message(
        self, 
        level: LogLevel, 
        message: str, 
        timestamp: bool = True, 
        colorize: bool = True
    ) -> str:
        """Format a log message with timestamp, icon, and color"""
        color = self.colors[level] if colorize else ''
        reset = self.colors['reset'] if colorize else ''
        icon = self.level_icons[level]
        time_str = f"[{self.format_timestamp()}]" if timestamp else ''
        level_str = level.upper().ljust(5)
        
        return f"{color}{time_str} {icon} {level_str}{reset} {message}"
    
    def trace(self, message: str, *args) -> None:
        """Log a trace message"""
        formatted = self.format_message('trace', message)
        print(formatted, *args, file=sys.stdout)
    
    def debug(self, message: str, *args) -> None:
        """Log a debug message"""
        formatted = self.format_message('debug', message)
        print(formatted, *args, file=sys.stdout)
    
    def info(self, message: str, *args) -> None:
        """Log an info message"""
        formatted = self.format_message('info', message)
        print(formatted, *args, file=sys.stdout)
    
    def warn(self, message: str, *args) -> None:
        """Log a warning message"""
        formatted = self.format_message('warn', message)
        print(formatted, *args, file=sys.stderr)
    
    def error(self, message: str, *args) -> None:
        """Log an error message"""
        formatted = self.format_message('error', message)
        print(formatted, *args, file=sys.stderr)
    
    def fatal(self, message: str, *args) -> None:
        """Log a fatal message"""
        formatted = self.format_message('fatal', message)
        print(formatted, *args, file=sys.stderr)
    
    def log(self, level: LogLevel, message: str, *args) -> None:
        """Generic log method that accepts a log level"""
        method_map = {
            'trace': self.trace,
            'debug': self.debug,
            'info': self.info,
            'warn': self.warn,
            'error': self.error,
            'fatal': self.fatal,
        }
        method = method_map.get(level)
        if method:
            method(message, *args)


# Initialize logger instance
logger = Logger()

