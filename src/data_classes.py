"""
数据类模块
定义用于存储从data文件夹读取的数据的数据类
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import open3d as o3d
import numpy as np


@dataclass
class Point3D:
    """3D点数据类"""
    a: float  # x坐标
    b: float  # y坐标
    c: float  # z坐标
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([self.a, self.b, self.c])
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Point3D':
        """从字典创建Point3D"""
        return cls(a=data['a'], b=data['b'], c=data['c'])


@dataclass
class Quaternion:
    """四元数数据类"""
    w: float
    x: float
    y: float
    z: float
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组 [w, x, y, z]"""
        return np.array([self.w, self.x, self.y, self.z])
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Quaternion':
        """从字典创建Quaternion"""
        return cls(w=data['w'], x=data['x'], y=data['y'], z=data['z'])


@dataclass
class Transform:
    """变换矩阵数据类（包含旋转和平移）"""
    q: Quaternion  # 旋转（四元数）
    t: Point3D    # 平移
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'q': {
                'w': self.q.w,
                'x': self.q.x,
                'y': self.q.y,
                'z': self.q.z
            },
            't': {
                'a': self.t.a,
                'b': self.t.b,
                'c': self.t.c
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transform':
        """从字典创建Transform"""
        return cls(
            q=Quaternion.from_dict(data['q']),
            t=Point3D.from_dict(data['t'])
        )


@dataclass
class PlaneParam:
    """平面参数数据类 (ax + by + cz + d = 0)"""
    a: float
    b: float
    c: float
    d: float
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组 [a, b, c, d]"""
        return np.array([self.a, self.b, self.c, self.d])
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'PlaneParam':
        """从字典创建PlaneParam"""
        return cls(a=data['a'], b=data['b'], c=data['c'], d=data['d'])


@dataclass
class PlaneMetadata:
    """平面元数据类（用于ground和plane的JSON文件）"""
    center: Point3D
    plane_param: PlaneParam
    radius: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'center': {
                'a': self.center.a,
                'b': self.center.b,
                'c': self.center.c
            },
            'plane_param': {
                'a': self.plane_param.a,
                'b': self.plane_param.b,
                'c': self.plane_param.c,
                'd': self.plane_param.d
            },
            'radius': self.radius
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaneMetadata':
        """从字典创建PlaneMetadata"""
        return cls(
            center=Point3D.from_dict(data['center']),
            plane_param=PlaneParam.from_dict(data['plane_param']),
            radius=data['radius']
        )


@dataclass
class AxisCost:
    """轴成本数据类"""
    a: float
    b: float
    c: float
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {'a': self.a, 'b': self.b, 'c': self.c}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'AxisCost':
        """从字典创建AxisCost"""
        return cls(a=data['a'], b=data['b'], c=data['c'])


@dataclass
class IterationInfo:
    """迭代信息数据类"""
    axis_cost_before: AxisCost
    axis_cost_after: AxisCost
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'axis_cost_before': self.axis_cost_before.to_dict(),
            'axis_cost_after': self.axis_cost_after.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IterationInfo':
        """从字典创建IterationInfo"""
        return cls(
            axis_cost_before=AxisCost.from_dict(data['axis_cost_before']),
            axis_cost_after=AxisCost.from_dict(data['axis_cost_after'])
        )


@dataclass
class DebugInfo:
    """Debug信息数据类（用于debug.txt）"""
    T_init_w_b: Transform  # 初始变换
    T_opt_w_b: Transform    # 优化后的变换
    iter_infos: List[IterationInfo]  # 迭代信息列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'T_init_w_b': self.T_init_w_b.to_dict(),
            'T_opt_w_b': self.T_opt_w_b.to_dict(),
            'iter_infos': [info.to_dict() for info in self.iter_infos]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DebugInfo':
        """从字典创建DebugInfo"""
        return cls(
            T_init_w_b=Transform.from_dict(data['T_init_w_b']),
            T_opt_w_b=Transform.from_dict(data['T_opt_w_b']),
            iter_infos=[IterationInfo.from_dict(info) for info in data['iter_infos']]
        )


@dataclass
class PointMatch:
    """点匹配数据类"""
    cur_id: int    # 当前点ID
    other_id: int  # 匹配的点ID
    
    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {'cur_id': self.cur_id, 'other_id': self.other_id}
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'PointMatch':
        """从字典创建PointMatch"""
        return cls(cur_id=data['cur_id'], other_id=data['other_id'])


@dataclass
class MatchInfo:
    """匹配信息数据类（用于match.json）"""
    dense_pt_match_infos: List[PointMatch]  # 密集点匹配信息列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'dense_pt_match_infos': [match.to_dict() for match in self.dense_pt_match_infos]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MatchInfo':
        """从字典创建MatchInfo"""
        return cls(
            dense_pt_match_infos=[PointMatch.from_dict(match) for match in data['dense_pt_match_infos']]
        )


@dataclass
class PointCloudData:
    """点云数据类（包含点云和元数据）"""
    point_cloud: o3d.geometry.PointCloud  # Open3D点云对象
    metadata: Optional[PlaneMetadata] = None  # 元数据（如果有）
    name: str = ""  # 名称（如 "ground_0", "plane_1" 等）
    
    def get_point_count(self) -> int:
        """获取点云中的点数"""
        return len(self.point_cloud.points) if self.point_cloud else 0


@dataclass
class FrameData:
    """帧数据类（包含一帧的所有数据）"""
    frame_id: int
    frame_type: str  # "frame" 或 "map"
    dense_cloud: Optional[o3d.geometry.PointCloud] = None  # 密集点云
    grounds: List[PointCloudData] = None  # Ground点云列表
    planes: List[PointCloudData] = None    # Plane点云列表
    debug_info: Optional[DebugInfo] = None  # Debug信息
    match_info: Optional[MatchInfo] = None # 匹配信息
    
    def __post_init__(self):
        """初始化后处理"""
        if self.grounds is None:
            self.grounds = []
        if self.planes is None:
            self.planes = []
    
    def get_total_point_count(self) -> int:
        """获取总点数"""
        count = 0
        if self.dense_cloud:
            count += len(self.dense_cloud.points)
        for ground in self.grounds:
            count += ground.get_point_count()
        for plane in self.planes:
            count += plane.get_point_count()
        return count
    
    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要"""
        return {
            'frame_id': self.frame_id,
            'frame_type': self.frame_type,
            'has_dense_cloud': self.dense_cloud is not None,
            'num_grounds': len(self.grounds),
            'num_planes': len(self.planes),
            'has_debug_info': self.debug_info is not None,
            'has_match_info': self.match_info is not None,
            'total_points': self.get_total_point_count()
        }

