"""
配置文件模块
定义项目的配置参数和路径
"""
import os
from pathlib import Path


class Config:
    """项目配置类"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent
    
    # 数据目录
    DATA_DIR = PROJECT_ROOT / "data"
    
    # 默认数据源类型
    FRAME_TYPE_FRAME = "frame"
    FRAME_TYPE_MAP = "map"
    
    # 可视化配置
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080
    WINDOW_NAME = "点云可视化工具"
    
    # 点云显示配置
    POINT_SIZE = 3.0  # 点云大小（增大以便于查看）
    BACKGROUND_COLOR = [0.9, 0.9, 0.95]  # 浅灰白色背景（高对比度，便于查看点云）
    
    # 坐标系配置
    COORDINATE_AXIS_LENGTH = 8.0  # 坐标轴长度（默认值，会根据点云自动调整，已增大）
    COORDINATE_AXIS_RADIUS = 0.02  # 坐标轴半径（用于圆柱体）
    COORDINATE_AXIS_ENABLED = True  # 是否显示坐标系
    COORDINATE_GRID_ENABLED = False  # 是否显示网格（已禁用）
    COORDINATE_GRID_SIZE = 0.5  # 网格大小（每个网格单元的尺寸）
    COORDINATE_GRID_COLOR = [0.3, 0.3, 0.3]  # 网格颜色（深灰色）
    
    # 支持的文件类型
    PLY_EXTENSION = ".ply"
    JSON_EXTENSION = ".json"
    
    @classmethod
    def get_data_frame_path(cls, frame_id: int) -> Path:
        """获取指定帧的数据目录路径"""
        return cls.DATA_DIR / str(frame_id)
    
    @classmethod
    def get_frame_data_path(cls, frame_id: int, frame_type: str = FRAME_TYPE_FRAME) -> Path:
        """获取指定帧类型的数据路径"""
        return cls.get_data_frame_path(frame_id) / frame_type
    
    @classmethod
    def get_available_frames(cls) -> list[int]:
        """获取所有可用的帧ID列表"""
        if not cls.DATA_DIR.exists():
            return []
        
        frames = []
        for item in cls.DATA_DIR.iterdir():
            if item.is_dir() and item.name.isdigit():
                frames.append(int(item.name))
        
        return sorted(frames)

