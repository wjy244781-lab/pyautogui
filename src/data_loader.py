"""
数据加载模块
负责读取.ply点云文件和.json元数据文件
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import open3d as o3d
import numpy as np

from .config import Config
from .dynamic_classes import create_class_from_dict, load_json_to_dynamic_class


class DataLoader:
    """数据加载器类"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录路径，如果为None则使用Config中的默认路径
        """
        self.data_dir = data_dir or Config.DATA_DIR
        # 存储ply文件信息的字典，key为id（int或str），value为文件信息字典
        # 格式: {id: {'file_path': Path, 'point_cloud': PointCloud, 'metadata': Any, 'name': str, 'type': str, 'frame_id': int, 'frame_type': str}}
        self.ply_file_map: Dict[Any, Dict[str, Any]] = {}
    
    def _extract_file_id(self, file_name: str) -> Optional[Any]:
        """
        从文件名中提取id
        
        Args:
            file_name: 文件名（不含扩展名），例如 'ground_0', 'plane_1', 'dense_cloud'
            
        Returns:
            id值，如果是数字则返回int，否则返回str。如果无法提取则返回None
        """
        if file_name == 'dense_cloud':
            return 'dense_cloud'
        
        # 尝试提取下划线后的数字
        if '_' in file_name:
            parts = file_name.split('_')
            if len(parts) >= 2:
                try:
                    # 提取最后一个部分作为id
                    id_str = parts[-1]
                    return int(id_str)
                except ValueError:
                    # 如果不是数字，返回整个名称
                    return file_name
        
        return file_name
    
    def load_point_cloud(self, file_path: Path) -> Optional[o3d.geometry.PointCloud]:
        """
        加载点云文件
        
        Args:
            file_path: .ply文件路径
            
        Returns:
            PointCloud对象，如果加载失败则返回None
        """
        if not file_path.exists() or file_path.suffix != Config.PLY_EXTENSION:
            return None
        
        try:
            pcd = o3d.io.read_point_cloud(str(file_path))
            if len(pcd.points) == 0:
                return None
            return pcd
        except Exception as e:
            print(f"加载点云文件失败 {file_path}: {e}")
            return None
    
    def load_json_metadata(self, file_path: Path, use_dynamic_class: bool = True) -> Optional[Any]:
        """
        加载JSON元数据文件
        
        Args:
            file_path: .json文件路径
            use_dynamic_class: 是否使用动态类，如果为False则返回普通字典
            
        Returns:
            动态类实例或字典对象，如果加载失败则返回None
        """
        if not file_path.exists() or file_path.suffix != Config.JSON_EXTENSION:
            return None
        
        try:
            if use_dynamic_class:
                # 使用动态类生成
                return load_json_to_dynamic_class(str(file_path))
            else:
                # 返回普通字典
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载JSON文件失败 {file_path}: {e}")
            return None
    
    def get_frame_files(self, frame_id: int, frame_type: str = Config.FRAME_TYPE_FRAME) -> Dict[str, List[Path]]:
        """
        获取指定帧的所有文件列表
        
        Args:
            frame_id: 帧ID
            frame_type: 帧类型（frame或map）
            
        Returns:
            包含文件路径的字典，键为文件类型（dense_cloud, ground, plane），值为文件路径列表
        """
        frame_path = Config.get_frame_data_path(frame_id, frame_type)
        
        if not frame_path.exists():
            return {}
        
        files = {
            'dense_cloud': [],
            'ground': [],
            'plane': [],
            'json': []
        }
        
        # 遍历目录中的所有文件
        for file_path in frame_path.iterdir():
            if file_path.is_file():
                if file_path.suffix == Config.PLY_EXTENSION:
                    name = file_path.stem
                    if name == 'dense_cloud':
                        files['dense_cloud'].append(file_path)
                    elif name.startswith('ground_'):
                        files['ground'].append(file_path)
                    elif name.startswith('plane_'):
                        files['plane'].append(file_path)
                elif file_path.suffix == Config.JSON_EXTENSION:
                    files['json'].append(file_path)
        
        # 排序
        for key in files:
            files[key].sort()
        
        return files
    
    def load_frame_data(self, frame_id: int, frame_type: str = Config.FRAME_TYPE_FRAME) -> Dict:
        """
        加载指定帧的所有数据，并将每个ply文件信息存储到map中
        
        Args:
            frame_id: 帧ID
            frame_type: 帧类型（frame或map）
            
        Returns:
            包含点云和元数据的字典
        """
        files = self.get_frame_files(frame_id, frame_type)
        
        result = {
            'frame_id': frame_id,
            'frame_type': frame_type,
            'dense_cloud': None,
            'grounds': [],
            'planes': [],
            'metadata': {}
        }
        
        # 加载dense_cloud
        if files['dense_cloud']:
            dense_file = files['dense_cloud'][0]
            pcd = self.load_point_cloud(dense_file)
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(pcd.points), 1))
            pcd.normals = o3d.utility.Vector3dVector(normals)
            if pcd:
                result['dense_cloud'] = pcd
                # 存储到map中
                file_id = self._extract_file_id(dense_file.stem)
                if file_id is not None:
                    json_file = dense_file.with_suffix(Config.JSON_EXTENSION)
                    metadata = self.load_json_metadata(json_file, use_dynamic_class=True)
                    self.ply_file_map[file_id] = {
                        'file_path': dense_file,
                        'point_cloud': pcd,
                        'metadata': metadata,
                        'name': dense_file.stem,
                        'type': 'dense_cloud',
                        'frame_id': frame_id,
                        'frame_type': frame_type
                    }
        
        # 加载ground点云
        for ground_file in files['ground']:
            pcd = self.load_point_cloud(ground_file)
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(pcd.points), 1))
            pcd.normals = o3d.utility.Vector3dVector(normals)
            if pcd:
                # 尝试加载对应的JSON元数据（使用动态类）
                json_file = ground_file.with_suffix(Config.JSON_EXTENSION)
                metadata = self.load_json_metadata(json_file, use_dynamic_class=True)
                result['grounds'].append({
                    'point_cloud': pcd,
                    'metadata': metadata,
                    'name': ground_file.stem
                })
                # 存储到map中
                file_id = self._extract_file_id(ground_file.stem)
                if file_id is not None:
                    self.ply_file_map[file_id] = {
                        'file_path': ground_file,
                        'point_cloud': pcd,
                        'metadata': metadata,
                        'name': ground_file.stem,
                        'type': 'ground',
                        'frame_id': frame_id,
                        'frame_type': frame_type
                    }

        # 加载plane点云
        for plane_file in files['plane']:
            pcd = self.load_point_cloud(plane_file)
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(pcd.points), 1))
            pcd.normals = o3d.utility.Vector3dVector(normals)
            if pcd:
                # 尝试加载对应的JSON元数据（使用动态类）
                json_file = plane_file.with_suffix(Config.JSON_EXTENSION)
                metadata = self.load_json_metadata(json_file, use_dynamic_class=True)
                result['planes'].append({
                    'point_cloud': pcd,
                    'metadata': metadata,
                    'name': plane_file.stem
                })
                # 存储到map中
                file_id = self._extract_file_id(plane_file.stem)
                if file_id is not None:
                    self.ply_file_map[file_id] = {
                        'file_path': plane_file,
                        'point_cloud': pcd,
                        'metadata': metadata,
                        'name': plane_file.stem,
                        'type': 'plane',
                        'frame_id': frame_id,
                        'frame_type': frame_type
                    }
        
        return result
    
    def load_debug_info(self, frame_id: int, use_dynamic_class: bool = True) -> Optional[Any]:
        """加载debug.txt文件"""
        debug_path = Config.get_data_frame_path(frame_id) / "debug.txt"
        if not debug_path.exists():
            return None
        
        try:
            # 解析txt文件
            debug_data = self._parse_debug_txt(debug_path)
            if debug_data is None:
                return None
            
            # 如果使用动态类，转换为动态类实例
            if use_dynamic_class:
                from .dynamic_classes import create_class_from_dict
                return create_class_from_dict(debug_data, "DebugInfo")
            else:
                return debug_data
        except Exception as e:
            print(f"加载debug.txt文件失败: {e}")
            return None
    
    def _parse_debug_txt(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        解析debug.txt文件
        
        txt格式示例:
        T_init_w_b = t(xyz) = 0 0 0, q(wxyz) = 1 0 0 0
        T_opt_w_b = t(xyz) = 0.000848208 0.000717433 -0.000269789, q(wxyz) = 1 -2.15494e-05 -0.000117662 -4.96011e-05
        0iteration:
        axis cost before 3.85690 1.70589 4.69210
        axis cost after 3.83553 1.67809 4.67178
        1iteration:
        axis cost before 1.26962 0.52992 1.44890
        axis cost after 1.26748 0.53076 1.44804
        """
        import re
        
        result = {
            'T_init_w_b': None,
            'T_opt_w_b': None,
            'iter_infos': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_iter = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 解析T_init_w_b或T_opt_w_b
                if line.startswith('T_init_w_b') or line.startswith('T_opt_w_b'):
                    # 确定transform名称
                    if line.startswith('T_init_w_b'):
                        transform_name = 'T_init_w_b'
                    else:
                        transform_name = 'T_opt_w_b'
                    
                    # 提取t(xyz)和q(wxyz)
                    # 格式: t(xyz) = x y z, q(wxyz) = w x y z
                    t_match = re.search(r't\(xyz\)\s*=\s*([-\d.eE+\s]+)', line)
                    q_match = re.search(r'q\(wxyz\)\s*=\s*([-\d.eE+\s]+)', line)
                    
                    if t_match and q_match:
                        t_values = [float(x) for x in t_match.group(1).split()]
                        q_values = [float(x) for x in q_match.group(1).split()]
                        
                        if len(t_values) == 3 and len(q_values) == 4:
                            transform_dict = {
                                'q': {
                                    'w': q_values[0],
                                    'x': q_values[1],
                                    'y': q_values[2],
                                    'z': q_values[3]
                                },
                                't': {
                                    'a': t_values[0],
                                    'b': t_values[1],
                                    'c': t_values[2]
                                }
                            }
                            result[transform_name] = transform_dict
                
                # 解析iteration行
                elif re.match(r'^\d+iteration:', line):
                    iter_num = int(re.match(r'^(\d+)iteration:', line).group(1))
                    current_iter = {
                        'axis_cost_before': None,
                        'axis_cost_after': None
                    }
                    result['iter_infos'].append(current_iter)
                
                # 解析axis cost before/after
                elif 'axis cost before' in line:
                    if current_iter is not None:
                        values = [float(x) for x in line.replace('axis cost before', '').strip().split()]
                        if len(values) == 3:
                            current_iter['axis_cost_before'] = {
                                'a': values[0],
                                'b': values[1],
                                'c': values[2]
                            }
                
                elif 'axis cost after' in line:
                    if current_iter is not None:
                        values = [float(x) for x in line.replace('axis cost after', '').strip().split()]
                        if len(values) == 3:
                            current_iter['axis_cost_after'] = {
                                'a': values[0],
                                'b': values[1],
                                'c': values[2]
                            }
            
            # 检查是否成功解析
            if result['T_init_w_b'] is None or result['T_opt_w_b'] is None:
                print("警告: debug.txt文件格式不完整")
                return None
            
            return result
            
        except Exception as e:
            print(f"解析debug.txt文件失败: {e}")
            return None
    
    def load_match_info(self, frame_id: int, use_dynamic_class: bool = True) -> Optional[Any]:
        """加载match.json文件"""
        match_path = Config.get_data_frame_path(frame_id) / "match.json"
        return self.load_json_metadata(match_path, use_dynamic_class=use_dynamic_class)
    
    def quaternion_to_rotation_matrix(self, q: Dict[str, float]) -> np.ndarray:
        """
        将四元数转换为3x3旋转矩阵
        
        Args:
            q: 四元数字典，包含w, x, y, z
            
        Returns:
            3x3旋转矩阵
        """
        w, x, y, z = q.get('w', 0), q.get('x', 0), q.get('y', 0), q.get('z', 0)
        
        # 归一化四元数
        norm = np.sqrt(w*w + x*x + y*y + z*z)
        if norm > 0:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        
        # 转换为旋转矩阵
        R = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])
        return R
    
    def transform_to_matrix(self, transform_dict: Dict[str, Any]) -> np.ndarray:
        """
        将变换字典（包含四元数和平移向量）转换为4x4变换矩阵
        
        Args:
            transform_dict: 变换字典，包含'q'（四元数）和't'（平移向量）
            
        Returns:
            4x4齐次变换矩阵
        """
        q = transform_dict.get('q', {})
        t = transform_dict.get('t', {})
        
        # 获取旋转矩阵
        R = self.quaternion_to_rotation_matrix(q)
        
        # 获取平移向量
        translation = np.array([t.get('a', 0), t.get('b', 0), t.get('c', 0)])
        
        # 构建4x4变换矩阵
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = translation
        
        return T
    
    def get_transform_matrix_from_debug(self, frame_id: int, transform_name: str = 'T_opt_w_b') -> Optional[np.ndarray]:
        """
        从debug.txt中获取指定的变换矩阵
        
        Args:
            frame_id: 帧ID
            transform_name: 变换名称，默认为'T_opt_w_b'，也可以是'T_init_w_b'
            
        Returns:
            4x4变换矩阵，如果失败则返回None
        """
        debug_info = self.load_debug_info(frame_id, use_dynamic_class=False)
        if debug_info is None:
            return None
        
        if transform_name not in debug_info:
            print(f"警告: debug.txt中未找到 {transform_name}")
            return None
        
        transform_dict = debug_info[transform_name]
        return self.transform_to_matrix(transform_dict)
    
    def get_ply_info_by_id(self, file_id: Any) -> Optional[Dict[str, Any]]:
        """
        通过id获取ply文件信息
        
        Args:
            file_id: 文件id（int或str），例如 0, 1, 'dense_cloud'
            
        Returns:
            文件信息字典，包含以下键：
            - 'file_path': 文件路径
            - 'point_cloud': 点云对象
            - 'metadata': 元数据
            - 'name': 文件名（不含扩展名）
            - 'type': 文件类型（'ground', 'plane', 'dense_cloud'）
            - 'frame_id': 帧ID
            - 'frame_type': 帧类型
            如果id不存在则返回None
        """
        return self.ply_file_map.get(file_id)
    
    def get_all_ply_ids(self) -> List[Any]:
        """
        获取所有已加载的ply文件id列表
        
        Returns:
            id列表
        """
        return list(self.ply_file_map.keys())
    
    def clear_ply_file_map(self):
        """
        清空ply文件信息map（切换帧时调用）
        """
        self.ply_file_map.clear()

