"""
可视化模块
使用Open3D进行点云的三维可视化
"""
import open3d as o3d
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import colorsys

from .config import Config
from .data_loader import DataLoader


class PointCloudVisualizer:
    """点云可视化器类"""
    
    def __init__(self):
        """初始化可视化器"""
        self.vis = None
        self.current_frame_id = None
        self.current_frame_type = Config.FRAME_TYPE_FRAME
        self.data_loader = DataLoader()
        self.geometries = {}  # 存储当前显示的几何体
        self.hidden_geometries = {}  # 存储被隐藏的几何体（用于重新显示）
        self.running = False  # 运行标志
        self.axis_points = {}  # 存储坐标轴上的可点击点信息
        self.on_axis_click = None  # 坐标轴点击回调函数
        self.on_point_click = None  # 点云点击回调函数
        self.picked_points = []  # 存储选中的点
        self.point_cloud_info = {}  # 存储点云信息（名称、类型等）
        self.original_colors = {}  # 存储点云的原始颜色
        self.original_point_sizes = {}  # 存储点云的原始大小
        self.on_hover = None  # 鼠标悬浮回调函数
        self.hovered_point = None  # 当前鼠标悬浮的点坐标
        self.on_point_hover = None  # 点悬浮回调函数
        self.mouse_x = None  # 鼠标X坐标
        self.mouse_y = None  # 鼠标Y坐标
        
        # 存储transformed dense_cloud的颜色映射
        # 格式: {frame_id: {cur_id: [r, g, b]}}
        self.transformed_dense_cloud_colors: Dict[int, Dict[int, List[float]]] = {}
        
        # 颜色配置（注意：红色[1.0, 0.0, 0.0]保留给未匹配的点云，不在默认颜色中使用）
        self.colors = {
            'dense_cloud': [0.0, 0.0, 1.0],  # 蓝色（默认，但实际使用id颜色或每个点不同颜色）
            'ground': [0.0, 1.0, 0.0],      # 绿色（保留作为默认，但实际使用id颜色）
            'plane': [0.0, 0.0, 1.0],       # 蓝色（保留作为默认，但实际使用id颜色，红色保留给未匹配）
            'axis_x': [1.0, 0.2, 0.2],     # 亮红色 - X轴（更鲜艳）
            'axis_y': [0.2, 1.0, 0.2],     # 亮绿色 - Y轴（更鲜艳）
            'axis_z': [0.2, 0.4, 1.0],     # 亮蓝色 - Z轴（更鲜艳）
            'axis_point': [1.0, 1.0, 0.0],  # 黄色 - 坐标轴标记点
            'grid': Config.COORDINATE_GRID_COLOR,  # 网格颜色
        }
        
        # 生成18种不同的颜色，按照id分配
        self.id_colors = self._generate_id_colors(18)
    
    def _generate_id_colors(self, num_colors: int) -> List[List[float]]:
        """
        生成指定数量的不同颜色，排除红色（红色保留给未匹配的点云）
        
        Args:
            num_colors: 需要生成的颜色数量
            
        Returns:
            颜色列表，每个颜色是RGB格式的列表
        """
        colors = []
        # 红色范围：hue在0-20度和340-360度之间，我们跳过这个范围
        red_range_start = 0  # 红色开始
        red_range_end = 20   # 红色结束（约20度）
        red_range_start2 = 340  # 红色开始（另一端）
        red_range_end2 = 360   # 红色结束
        
        # 计算可用色相范围（排除红色）
        available_range = 360 - (red_range_end - red_range_start) - (red_range_end2 - red_range_start2)
        
        for i in range(num_colors):
            # 在可用范围内均匀分布，跳过红色区域
            hue_ratio = i / num_colors  # 0到1之间的比例
            hue = red_range_end + hue_ratio * available_range  # 从红色结束处开始
            
            # 确保hue在0-360范围内
            hue = hue % 360.0
            
            saturation = 0.8  # 饱和度
            value = 0.9  # 亮度

            # 转换为RGB
            rgb = colorsys.hsv_to_rgb(hue / 360.0, saturation, value)
            colors.append(list(rgb))
        return colors
    
    def generate_distinct_colors(self, num_colors: int, 
                                 saturation: float = 0.8, 
                                 value: float = 0.9) -> np.ndarray:
        """
        生成指定数量的不同颜色，确保每个颜色都不同，排除红色（红色保留给未匹配的点云）
        
        使用HSV色彩空间生成均匀分布的颜色，通过调整色相(H)、饱和度(S)和亮度(V)
        来确保生成的颜色在视觉上有明显区别。
        
        Args:
            num_colors: 需要生成的颜色数量
            saturation: 饱和度，范围0.0-1.0，默认0.8
            value: 亮度，范围0.0-1.0，默认0.9
            
        Returns:
            numpy数组，形状为(num_colors, 3)，每行是一个RGB颜色值（范围0.0-1.0）
        """
        if num_colors <= 0:
            return np.array([]).reshape(0, 3)
        
        colors = []
        
        # 红色范围：hue在0-20度和340-360度之间（HSV中hue范围0-1对应0-360度）
        # 红色范围：约0-0.056和0.944-1.0
        red_range_start = 0.0
        red_range_end = 20.0 / 360.0  # 约0.056
        red_range_start2 = 340.0 / 360.0  # 约0.944
        red_range_end2 = 1.0
        
        # 计算可用色相范围（排除红色）
        available_range = 1.0 - (red_range_end - red_range_start) - (red_range_end2 - red_range_start2)
        
        if num_colors == 1:
            # 只有一个颜色时，返回一个非红色的鲜艳颜色（使用绿色）
            rgb = colorsys.hsv_to_rgb(120.0 / 360.0, saturation, value)  # 绿色
            colors.append(list(rgb))
        else:
            # 使用黄金角度（约137.5度）来生成均匀分布的颜色
            # 这样可以确保颜色在色相环上均匀分布
            golden_angle = 0.618033988749895  # 黄金比例 - 1
            
            for i in range(num_colors):
                # 使用黄金角度确保颜色分布均匀，但跳过红色范围
                hue_raw = (i * golden_angle) % 1.0
                
                # 如果落在红色范围内，调整到可用范围
                if hue_raw < red_range_end:
                    # 映射到红色范围之后
                    hue = red_range_end + (hue_raw / red_range_end) * (available_range / 2)
                elif hue_raw > red_range_start2:
                    # 映射到红色范围之前
                    hue = red_range_start2 - available_range / 2 + ((hue_raw - red_range_start2) / (red_range_end2 - red_range_start2)) * (available_range / 2)
                else:
                    # 在可用范围内，需要重新映射到整个可用范围
                    hue = red_range_end + ((hue_raw - red_range_end) / (red_range_start2 - red_range_end)) * available_range
                
                # 确保hue在0-1范围内
                hue = hue % 1.0
                
                # 对于大量颜色，可以稍微调整饱和度和亮度以增加变化
                if num_colors > 100:
                    # 在饱和度和亮度上添加小的变化
                    s = saturation * (0.7 + 0.3 * (i % 3) / 2.0)
                    v = value * (0.8 + 0.2 * (i % 5) / 4.0)
                else:
                    s = saturation
                    v = value
                
                # 转换为RGB
                rgb = colorsys.hsv_to_rgb(hue, s, v)
                colors.append(list(rgb))
        
        return np.array(colors, dtype=np.float32)
    
    def get_color_by_id(self, id: int) -> List[float]:
        """
        根据id获取颜色（循环使用18种颜色）
        
        Args:
            id: 点云的id（索引）
            
        Returns:
            RGB颜色列表
        """
        if id < 0:
            color = [0.5, 0.5, 0.5]  # 默认灰色
            print(f"[DEBUG] get_color_by_id: id={id} (负数), 返回默认灰色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            return color
        color = self.id_colors[id % len(self.id_colors)]
        print(f"[DEBUG] get_color_by_id: id={id}, 返回颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
        return color
    
    def create_visualizer(self) -> o3d.visualization.Visualizer:
        """创建可视化窗口"""
        vis = o3d.visualization.Visualizer()
        vis.create_window(
            window_name=Config.WINDOW_NAME,
            width=Config.WINDOW_WIDTH,
            height=Config.WINDOW_HEIGHT
        )
        
        # 设置渲染选项
        render_option = vis.get_render_option()
        render_option.background_color = np.array(Config.BACKGROUND_COLOR)
        render_option.point_size = Config.POINT_SIZE
        # 关闭光照，这样旋转时颜色不会因光照而改变
        render_option.light_on = False
        # 使用点云自己的颜色，不使用法线映射
        render_option.point_color_option = o3d.visualization.PointColorOption.Color
        
        # 立即添加坐标系（使用默认长度）
        if Config.COORDINATE_AXIS_ENABLED:
            geometries = self.create_coordinate_axes(Config.COORDINATE_AXIS_LENGTH)
            axis_names = [
                'coordinate_axis_x', 'coordinate_arrow_x',
                'coordinate_axis_y', 'coordinate_arrow_y',
                'coordinate_axis_z', 'coordinate_arrow_z',
                'coordinate_label_x', 'coordinate_label_y', 'coordinate_label_z'
            ]
            for geometry, name in zip(geometries, axis_names):
                vis.add_geometry(geometry, reset_bounding_box=False)
                self.geometries[name] = geometry
            
            # 添加网格
            if Config.COORDINATE_GRID_ENABLED:
                grid_geometries = self.create_coordinate_grid(Config.COORDINATE_AXIS_LENGTH)
                grid_names = ['coordinate_grid_xy', 'coordinate_grid_xz', 'coordinate_grid_yz']
                for geometry, name in zip(grid_geometries, grid_names):
                    vis.add_geometry(geometry, reset_bounding_box=False)
                    self.geometries[name] = geometry
            
            # 设置鼠标和键盘回调
            self._setup_mouse_callbacks(vis)
            # 更新视图以确保坐标系显示
            vis.poll_events()
            vis.update_renderer()
        
        return vis
    
    def add_geometry(self, geometry: o3d.geometry.Geometry, name: str, color: Optional[List[float]] = None):
        """
        添加几何体到可视化窗口
        
        Args:
            geometry: Open3D几何体对象
            name: 几何体名称（用于管理）
            color: RGB颜色，如果为None则使用默认颜色
        """
        if self.vis is None:
            return
        
        # 如果同名几何体已存在，先移除它（避免重复绘制）
        if name in self.geometries:
            self.remove_geometry(name)
        
        # 如果几何体是点云，设置颜色（数据文件不包含颜色信息，完全由代码设置）
        if isinstance(geometry, o3d.geometry.PointCloud):
            num_points = len(geometry.points)
            
            # 存储原始点大小（从render option获取）
            render_option = self.vis.get_render_option()
            self.original_point_sizes[name] = render_option.point_size
            
            # 设置颜色：如果提供了color参数则使用，否则检查点云是否已有颜色
            if color is not None:
                # 使用提供的颜色
                color_array = np.tile(np.array(color), (num_points, 1))
                color_array = np.clip(color_array, 0.0, 1.0)
                geometry.colors = o3d.utility.Vector3dVector(color_array)
                # 存储原始颜色（用于后续恢复）
                self.original_colors[name] = color_array.copy()
            else:
                # color为None时，检查点云是否已经有颜色
                if geometry.has_colors() and len(geometry.colors) == num_points:
                    # 点云已有颜色，保留并使用它
                    color_array = np.asarray(geometry.colors)
                    # 存储原始颜色
                    self.original_colors[name] = color_array.copy()
                else:
                    # 点云没有颜色，使用默认灰色
                    default_color = [0.5, 0.5, 0.5]
                    color_array = np.tile(np.array(default_color), (num_points, 1))
                    geometry.colors = o3d.utility.Vector3dVector(color_array)
                    # 存储原始颜色
                    self.original_colors[name] = color_array.copy()
        
        self.vis.add_geometry(geometry, reset_bounding_box=False)
        self.geometries[name] = geometry
    
    def remove_geometry(self, name: str):
        """从可视化窗口移除几何体"""
        if self.vis is None or name not in self.geometries:
            return
        
        self.vis.remove_geometry(self.geometries[name], reset_bounding_box=False)
        del self.geometries[name]
    
    def hide_geometry(self, name: str):
        """隐藏几何体（保留以便重新显示）"""
        if self.vis is None or name not in self.geometries:
            return
        
        geometry = self.geometries[name]
        # 保存点云信息以便重新显示
        info = self.point_cloud_info.get(name, {})
        
        # 保存完整的颜色数组（如果点云有颜色）
        color_array = None
        color = None
        
        # 首先尝试从点云对象本身获取颜色
        if isinstance(geometry, o3d.geometry.PointCloud) and geometry.has_colors():
            # 保存完整的颜色数组
            color_array = np.asarray(geometry.colors).copy()
        
        # 如果点云没有颜色，尝试从原始颜色中获取
        if color_array is None and name in self.original_colors:
            orig_colors = self.original_colors[name]
            if isinstance(orig_colors, np.ndarray) and len(orig_colors.shape) == 2 and len(orig_colors) > 0:
                # 检查是否所有点颜色相同
                first_color = orig_colors[0]
                if np.allclose(orig_colors, first_color, atol=1e-6):
                    # 所有点颜色相同，只保存单一颜色
                    color = first_color.tolist()
                else:
                    # 每个点颜色不同，保存完整数组
                    color_array = orig_colors.copy()
        
        # 如果都没有找到颜色，尝试根据类型获取默认颜色
        if color is None and color_array is None:
            if name == 'dense_cloud' or name == 'map_dense_cloud':
                color = self.colors['dense_cloud']
            elif name.startswith('ground_') or name.startswith('map_ground_'):
                # 从info中获取id，如果没有则从名称中提取
                id = info.get('id')
                if id is None:
                    try:
                        # 移除map_前缀（如果存在）
                        name_without_prefix = name.replace('map_', '')
                        id = int(name_without_prefix.split('_')[1])
                    except (ValueError, IndexError):
                        id = 0
                color = self.get_color_by_id(id)
            elif name.startswith('plane_') or name.startswith('map_plane_'):
                # 从info中获取id，如果没有则从名称中提取
                id = info.get('id')
                if id is None:
                    try:
                        # 移除map_前缀（如果存在）
                        name_without_prefix = name.replace('map_', '')
                        id = int(name_without_prefix.split('_')[1])
                    except (ValueError, IndexError):
                        id = 0
                color = self.get_color_by_id(id)
        
        self.hidden_geometries[name] = {
            'geometry': geometry,
            'info': info,
            'color': color,  # 单一颜色（如果所有点颜色相同）
            'color_array': color_array  # 完整颜色数组（如果每个点颜色不同）
        }
        
        self.vis.remove_geometry(geometry, reset_bounding_box=False)
        del self.geometries[name]
        if name in self.point_cloud_info:
            del self.point_cloud_info[name]
    
    def show_geometry(self, name: str):
        """显示之前隐藏的几何体"""
        if self.vis is None or name not in self.hidden_geometries:
            return
        
        hidden_data = self.hidden_geometries[name]
        geometry = hidden_data['geometry']
        info = hidden_data['info']
        color = hidden_data.get('color')  # 单一颜色
        color_array = hidden_data.get('color_array')  # 完整颜色数组
        
        # 如果有完整的颜色数组，直接设置到点云对象上
        if color_array is not None and isinstance(geometry, o3d.geometry.PointCloud):
            # 确保颜色数组的形状正确
            if isinstance(color_array, np.ndarray) and len(color_array.shape) == 2:
                geometry.colors = o3d.utility.Vector3dVector(color_array)
                # 重新添加到可视化器，传递None以使用点云对象上已设置的颜色
                self.add_geometry(geometry, name, None)
            else:
                # 颜色数组格式不正确，使用单一颜色
                self.add_geometry(geometry, name, color)
        else:
            # 没有颜色数组，使用单一颜色
            self.add_geometry(geometry, name, color)
        
        self.point_cloud_info[name] = info
        
        # 从隐藏列表中移除
        del self.hidden_geometries[name]
    
    def toggle_point_cloud_type(self, cloud_type: str) -> bool:
        """
        切换指定类型点云的显示/隐藏状态
        
        会同时处理map和frame的点云（map_ground_0和ground_0都会被切换）
        
        Args:
            cloud_type: 点云类型 ('ground', 'plane', 'dense_cloud')
            
        Returns:
            True表示当前显示，False表示当前隐藏
        """
        if self.vis is None:
            return False
        
        # 查找该类型的所有点云（包括map和frame）
        visible_names = []
        hidden_names = []
        
        if cloud_type == 'dense_cloud':
            # 查找dense_cloud（可能没有前缀，也可能有map_前缀）
            for name in list(self.geometries.keys()):
                if name == 'dense_cloud' or name == 'map_dense_cloud':
                    visible_names.append(name)
            for name in list(self.hidden_geometries.keys()):
                if name == 'dense_cloud' or name == 'map_dense_cloud':
                    hidden_names.append(name)
        else:
            # ground或plane可能有多个（ground_0, ground_1, ... 或 map_ground_0, map_ground_1, ...）
            # 匹配所有以ground_或map_ground_开头的名称
            for name in list(self.geometries.keys()):
                if name.startswith(cloud_type + '_') or name.startswith('map_' + cloud_type + '_'):
                    visible_names.append(name)
            for name in list(self.hidden_geometries.keys()):
                if name.startswith(cloud_type + '_') or name.startswith('map_' + cloud_type + '_'):
                    hidden_names.append(name)
        
        # 如果有可见的，则隐藏它们
        if visible_names:
            for name in visible_names:
                self.hide_geometry(name)
            return False
        # 如果有隐藏的，则显示它们
        elif hidden_names:
            for name in hidden_names:
                self.show_geometry(name)
            self.update_view()
            return True
        else:
            # 没有该类型的点云
            return False
    
    def is_point_cloud_type_visible(self, cloud_type: str) -> bool:
        """
        检查指定类型点云是否可见（包括map和frame的点云）
        
        Args:
            cloud_type: 点云类型 ('ground', 'plane', 'dense_cloud')
            
        Returns:
            True表示可见，False表示隐藏或不存在
        """
        if cloud_type == 'dense_cloud':
            return 'dense_cloud' in self.geometries or 'map_dense_cloud' in self.geometries
        else:
            # 检查是否有该类型的点云可见（包括map和frame）
            for name in self.geometries.keys():
                if name.startswith(cloud_type + '_') or name.startswith('map_' + cloud_type + '_'):
                    return True
            return False
    
    def clear_all_geometries(self):
        """清除所有几何体（保留坐标系和网格）"""
        if self.vis is None:
            return
        
        # 保留坐标系和网格，清除其他几何体
        coordinate_names = [
            'coordinate_axis_x', 'coordinate_arrow_x',
            'coordinate_axis_y', 'coordinate_arrow_y',
            'coordinate_axis_z', 'coordinate_arrow_z',
            'coordinate_label_x', 'coordinate_label_y', 'coordinate_label_z',
            'coordinate_grid_xy', 'coordinate_grid_xz', 'coordinate_grid_yz'
        ]
        for name in list(self.geometries.keys()):
            if name not in coordinate_names:
                self.remove_geometry(name)
        
        # 清除隐藏的几何体（切换帧时需要清除）
        self.hidden_geometries.clear()
    
    def create_coordinate_axes(self, length: float = None) -> List[o3d.geometry.Geometry]:
        """
        创建三维坐标系（包含箭头和可点击标记点）
        
        Args:
            length: 坐标轴长度，如果为None则使用Config中的默认值
            
        Returns:
            包含三个坐标轴几何体的列表 [X轴, Y轴, Z轴, X箭头, Y箭头, Z箭头]
        """
        if length is None:
            length = Config.COORDINATE_AXIS_LENGTH
        
        geometries = []
        origin = np.array([0.0, 0.0, 0.0])
        arrow_length = length * 0.15  # 箭头长度为轴长度的15%
        arrow_radius = length * 0.03  # 箭头半径
        point_radius = length * 0.05  # 标记点半径
        
        # 清空之前的标记点信息
        self.axis_points = {}
        
        # X轴 (红色) - 主轴线
        x_axis = o3d.geometry.LineSet()
        x_end = origin + np.array([length, 0.0, 0.0])
        x_points = np.array([origin, x_end])
        x_lines = np.array([[0, 1]])
        x_axis.points = o3d.utility.Vector3dVector(x_points)
        x_axis.lines = o3d.utility.Vector2iVector(x_lines)
        x_axis.colors = o3d.utility.Vector3dVector([self.colors['axis_x']])
        geometries.append(x_axis)
        
        # X轴箭头（圆锥）
        x_arrow = o3d.geometry.TriangleMesh.create_cone(
            radius=arrow_radius, height=arrow_length, resolution=20
        )
        x_arrow.translate(x_end)
        x_arrow.rotate(
            o3d.geometry.get_rotation_matrix_from_xyz([0, np.pi / 2, 0]),
            center=x_end
        )
        x_arrow.paint_uniform_color(self.colors['axis_x'])
        geometries.append(x_arrow)
        
        # 保留标记点信息（不显示，但可用于信息查询）
        self.axis_points['axis_point_x_origin'] = {
            'position': origin.copy(),
            'axis': 'X',
            'type': 'origin',
            'info': f'X轴原点\n坐标: (0.0, 0.0, 0.0)\n方向: 正X方向'
        }
        self.axis_points['axis_point_x_end'] = {
            'position': x_end.copy(),
            'axis': 'X',
            'type': 'end',
            'info': f'X轴端点\n坐标: ({length:.2f}, 0.0, 0.0)\n方向: 正X方向\n长度: {length:.2f}'
        }
        
        # Y轴 (绿色) - 主轴线
        y_axis = o3d.geometry.LineSet()
        y_end = origin + np.array([0.0, length, 0.0])
        y_points = np.array([origin, y_end])
        y_lines = np.array([[0, 1]])
        y_axis.points = o3d.utility.Vector3dVector(y_points)
        y_axis.lines = o3d.utility.Vector2iVector(y_lines)
        y_axis.colors = o3d.utility.Vector3dVector([self.colors['axis_y']])
        geometries.append(y_axis)
        
        # Y轴箭头（圆锥）
        y_arrow = o3d.geometry.TriangleMesh.create_cone(
            radius=arrow_radius, height=arrow_length, resolution=20
        )
        y_arrow.translate(y_end)
        y_arrow.rotate(
            o3d.geometry.get_rotation_matrix_from_xyz([-np.pi / 2, 0, 0]),
            center=y_end
        )
        y_arrow.paint_uniform_color(self.colors['axis_y'])
        geometries.append(y_arrow)
        
        # 保留标记点信息（不显示，但可用于信息查询）
        self.axis_points['axis_point_y_origin'] = {
            'position': origin.copy(),
            'axis': 'Y',
            'type': 'origin',
            'info': f'Y轴原点\n坐标: (0.0, 0.0, 0.0)\n方向: 正Y方向'
        }
        self.axis_points['axis_point_y_end'] = {
            'position': y_end.copy(),
            'axis': 'Y',
            'type': 'end',
            'info': f'Y轴端点\n坐标: (0.0, {length:.2f}, 0.0)\n方向: 正Y方向\n长度: {length:.2f}'
        }
        
        # Z轴 (蓝色) - 主轴线
        z_axis = o3d.geometry.LineSet()
        z_end = origin + np.array([0.0, 0.0, length])
        z_points = np.array([origin, z_end])
        z_lines = np.array([[0, 1]])
        z_axis.points = o3d.utility.Vector3dVector(z_points)
        z_axis.lines = o3d.utility.Vector2iVector(z_lines)
        z_axis.colors = o3d.utility.Vector3dVector([self.colors['axis_z']])
        geometries.append(z_axis)
        
        # Z轴箭头（圆锥）
        z_arrow = o3d.geometry.TriangleMesh.create_cone(
            radius=arrow_radius, height=arrow_length, resolution=20
        )
        z_arrow.translate(z_end)
        # Z轴箭头向上，不需要旋转
        z_arrow.paint_uniform_color(self.colors['axis_z'])
        geometries.append(z_arrow)
        
        # 保留标记点信息（不显示，但可用于信息查询）
        self.axis_points['axis_point_z_origin'] = {
            'position': origin.copy(),
            'axis': 'Z',
            'type': 'origin',
            'info': f'Z轴原点\n坐标: (0.0, 0.0, 0.0)\n方向: 正Z方向'
        }
        self.axis_points['axis_point_z_end'] = {
            'position': z_end.copy(),
            'axis': 'Z',
            'type': 'end',
            'info': f'Z轴端点\n坐标: (0.0, 0.0, {length:.2f})\n方向: 正Z方向\n长度: {length:.2f}'
        }
        
        # 创建坐标轴文字标记（使用LineSet创建X、Y、Z字母轮廓）
        label_offset = length * 0.25  # 标记位置偏移量（在箭头末端之后）
        label_size = length * 0.08  # 文字大小
        
        # X轴文字标记（红色）
        x_label_pos = x_end + np.array([label_offset, 0.0, 0.0])
        x_label = self._create_text_lineset("X", x_label_pos, label_size, self.colors['axis_x'])
        geometries.append(x_label)
        
        # Y轴文字标记（绿色）
        y_label_pos = y_end + np.array([0.0, label_offset, 0.0])
        y_label = self._create_text_lineset("Y", y_label_pos, label_size, self.colors['axis_y'])
        geometries.append(y_label)
        
        # Z轴文字标记（蓝色）
        z_label_pos = z_end + np.array([0.0, 0.0, label_offset])
        z_label = self._create_text_lineset("Z", z_label_pos, label_size, self.colors['axis_z'])
        geometries.append(z_label)
        
        return geometries
    
    def _create_text_lineset(self, text: str, position: np.ndarray, size: float, color: List[float]) -> o3d.geometry.LineSet:
        """
        创建文字轮廓的LineSet
        
        Args:
            text: 文字内容（"X", "Y", 或 "Z"）
            position: 文字位置（3D坐标）
            size: 文字大小
            color: 文字颜色
            
        Returns:
            LineSet对象
        """
        points = []
        lines = []
        line_idx = 0
        
        if text == "X":
            # X字母：两条交叉线
            # 左上到右下
            points.append(position + np.array([-size, size, 0]))
            points.append(position + np.array([size, -size, 0]))
            lines.append([line_idx, line_idx + 1])
            line_idx += 2
            # 左下到右上
            points.append(position + np.array([-size, -size, 0]))
            points.append(position + np.array([size, size, 0]))
            lines.append([line_idx, line_idx + 1])
            
        elif text == "Y":
            # Y字母：一个倒V形加一条竖线
            # 倒V的左上分支：从顶部到中间点
            points.append(position + np.array([-size * 0.5, size, 0]))
            points.append(position + np.array([0, size * 0.3, 0]))  # 中间汇聚点
            lines.append([line_idx, line_idx + 1])
            line_idx += 2
            # 倒V的右上分支：从顶部到中间点
            points.append(position + np.array([size * 0.5, size, 0]))
            points.append(position + np.array([0, size * 0.3, 0]))  # 中间汇聚点
            lines.append([line_idx, line_idx + 1])
            line_idx += 2
            # 竖线：从中间点到底部
            points.append(position + np.array([0, size * 0.3, 0]))  # 中间汇聚点
            points.append(position + np.array([0, -size, 0]))
            lines.append([line_idx, line_idx + 1])
            
        elif text == "Z":
            # Z字母：三条线（上横、斜线、下横）
            # 上横线
            points.append(position + np.array([-size, size, 0]))
            points.append(position + np.array([size, size, 0]))
            lines.append([line_idx, line_idx + 1])
            line_idx += 2
            # 斜线
            points.append(position + np.array([size, size, 0]))
            points.append(position + np.array([-size, -size, 0]))
            lines.append([line_idx, line_idx + 1])
            line_idx += 2
            # 下横线
            points.append(position + np.array([-size, -size, 0]))
            points.append(position + np.array([size, -size, 0]))
            lines.append([line_idx, line_idx + 1])
        
        # 创建LineSet
        lineset = o3d.geometry.LineSet()
        if len(points) > 0:
            lineset.points = o3d.utility.Vector3dVector(np.array(points))
            lineset.lines = o3d.utility.Vector2iVector(np.array(lines))
            lineset.colors = o3d.utility.Vector3dVector([color] * len(lines))
        
        return lineset
    
    def create_coordinate_grid(self, length: float = None) -> List[o3d.geometry.LineSet]:
        """
        创建坐标网格（在XY、XZ、YZ平面上）
        
        Args:
            length: 网格范围，如果为None则使用坐标轴长度
            
        Returns:
            包含网格线的LineSet列表
        """
        if not Config.COORDINATE_GRID_ENABLED:
            return []
        
        if length is None:
            length = Config.COORDINATE_AXIS_LENGTH
        
        grid_size = Config.COORDINATE_GRID_SIZE
        grid_lines = []
        
        # 计算网格范围（以原点为中心，向正负方向延伸）
        grid_range = length
        num_lines = int(grid_range / grid_size) * 2 + 1  # 包括原点
        
        # XY平面网格（Z=0）
        xy_grid = o3d.geometry.LineSet()
        xy_points = []
        xy_lines = []
        line_idx = 0
        
        # X方向的网格线（平行于Y轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            x = i * grid_size
            if abs(x) <= grid_range:
                # 添加一条从-y到+y的线
                xy_points.append([x, -grid_range, 0.0])
                xy_points.append([x, grid_range, 0.0])
                xy_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        # Y方向的网格线（平行于X轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            y = i * grid_size
            if abs(y) <= grid_range:
                # 添加一条从-x到+x的线
                xy_points.append([-grid_range, y, 0.0])
                xy_points.append([grid_range, y, 0.0])
                xy_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        if xy_points:
            xy_grid.points = o3d.utility.Vector3dVector(np.array(xy_points))
            xy_grid.lines = o3d.utility.Vector2iVector(np.array(xy_lines))
            xy_grid.colors = o3d.utility.Vector3dVector([self.colors['grid']] * len(xy_lines))
            grid_lines.append(xy_grid)
        
        # XZ平面网格（Y=0）
        xz_grid = o3d.geometry.LineSet()
        xz_points = []
        xz_lines = []
        line_idx = 0
        
        # X方向的网格线（平行于Z轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            x = i * grid_size
            if abs(x) <= grid_range:
                xz_points.append([x, 0.0, -grid_range])
                xz_points.append([x, 0.0, grid_range])
                xz_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        # Z方向的网格线（平行于X轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            z = i * grid_size
            if abs(z) <= grid_range:
                xz_points.append([-grid_range, 0.0, z])
                xz_points.append([grid_range, 0.0, z])
                xz_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        if xz_points:
            xz_grid.points = o3d.utility.Vector3dVector(np.array(xz_points))
            xz_grid.lines = o3d.utility.Vector2iVector(np.array(xz_lines))
            xz_grid.colors = o3d.utility.Vector3dVector([self.colors['grid']] * len(xz_lines))
            grid_lines.append(xz_grid)
        
        # YZ平面网格（X=0）
        yz_grid = o3d.geometry.LineSet()
        yz_points = []
        yz_lines = []
        line_idx = 0
        
        # Y方向的网格线（平行于Z轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            y = i * grid_size
            if abs(y) <= grid_range:
                yz_points.append([0.0, y, -grid_range])
                yz_points.append([0.0, y, grid_range])
                yz_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        # Z方向的网格线（平行于Y轴）
        for i in range(-num_lines//2, num_lines//2 + 1):
            z = i * grid_size
            if abs(z) <= grid_range:
                yz_points.append([0.0, -grid_range, z])
                yz_points.append([0.0, grid_range, z])
                yz_lines.append([line_idx * 2, line_idx * 2 + 1])
                line_idx += 1
        
        if yz_points:
            yz_grid.points = o3d.utility.Vector3dVector(np.array(yz_points))
            yz_grid.lines = o3d.utility.Vector2iVector(np.array(yz_lines))
            yz_grid.colors = o3d.utility.Vector3dVector([self.colors['grid']] * len(yz_lines))
            grid_lines.append(yz_grid)
        
        return grid_lines
    
    def add_coordinate_axes(self, length: float = None):
        """添加坐标系到可视化窗口"""
        if not Config.COORDINATE_AXIS_ENABLED:
            return
        
        if self.vis is None:
            return
        
        # 如果没有指定长度，尝试根据点云数据自动计算
        if length is None:
            length = self._calculate_axis_length()
            # 如果计算出的长度太小或为0，使用默认值
            if length <= 0:
                length = Config.COORDINATE_AXIS_LENGTH
        
        # 确保最小长度，让坐标系更显眼
        min_length = max(length, Config.COORDINATE_AXIS_LENGTH * 1.5)
        
        geometries = self.create_coordinate_axes(min_length)
        axis_names = [
            'coordinate_axis_x', 'coordinate_arrow_x',
            'coordinate_axis_y', 'coordinate_arrow_y',
            'coordinate_axis_z', 'coordinate_arrow_z',
            'coordinate_label_x', 'coordinate_label_y', 'coordinate_label_z'
        ]
        
        for geometry, name in zip(geometries, axis_names):
            # 如果已存在，先移除
            if name in self.geometries:
                self.remove_geometry(name)
            # 添加新的坐标轴、箭头或标记点
            self.vis.add_geometry(geometry, reset_bounding_box=False)
            self.geometries[name] = geometry
        
        # 添加网格
        if Config.COORDINATE_GRID_ENABLED:
            grid_geometries = self.create_coordinate_grid(min_length)
            grid_names = ['coordinate_grid_xy', 'coordinate_grid_xz', 'coordinate_grid_yz']
            
            for geometry, name in zip(grid_geometries, grid_names):
                # 如果已存在，先移除
                if name in self.geometries:
                    self.remove_geometry(name)
                # 添加网格
                self.vis.add_geometry(geometry, reset_bounding_box=False)
                self.geometries[name] = geometry
        
        # 设置鼠标回调函数
        self._setup_mouse_callbacks(self.vis)
        
        # 添加坐标系后立即更新视图
        self.vis.poll_events()
        self.vis.update_renderer()
    
    def _setup_mouse_callbacks(self, vis: o3d.visualization.Visualizer):
        """设置鼠标回调函数"""
        if vis is None:
            return
        
        # 注意：Open3D的Visualizer类不直接支持键盘回调
        # 如果需要键盘回调，需要使用VisualizerWithKeyCallback
        # 这里暂时跳过键盘回调，鼠标悬浮检测通过其他方式实现
        pass
    
    def set_mouse_position(self, x: int, y: int):
        """设置鼠标位置（从GUI系统调用）"""
        self.mouse_x = x
        self.mouse_y = y
    
    def _get_cloud_info(self, cloud_name: str) -> Dict:
        """获取点云信息"""
        info = {
            'name': cloud_name,
            'type': 'unknown',
            'point_count': 0,
            'has_normals': False,
            'has_colors': False
        }
        
        if cloud_name in self.geometries:
            geometry = self.geometries[cloud_name]
            if isinstance(geometry, o3d.geometry.PointCloud):
                info['point_count'] = len(geometry.points)
                info['has_normals'] = geometry.has_normals()
                info['has_colors'] = geometry.has_colors()
                
                # 获取点云类型
                if cloud_name.startswith('ground'):
                    info['type'] = 'ground'
                elif cloud_name.startswith('plane'):
                    info['type'] = 'plane'
                elif cloud_name == 'dense_cloud':
                    info['type'] = 'dense_cloud'
                
                # 获取点云元数据
                if cloud_name in self.point_cloud_info:
                    info.update(self.point_cloud_info[cloud_name])
        
        return info
    
    def _find_nearest_axis_point(self, point: np.ndarray, threshold: float = None) -> Optional[Dict]:
        """查找最近的坐标轴标记点"""
        if threshold is None:
            # 默认阈值设为坐标轴长度的10%
            threshold = Config.COORDINATE_AXIS_LENGTH * 0.1
        
        min_distance = float('inf')
        nearest_info = None
        
        for name, info in self.axis_points.items():
            distance = np.linalg.norm(point - info['position'])
            if distance < threshold and distance < min_distance:
                min_distance = distance
                nearest_info = info.copy()
                nearest_info['name'] = name
                nearest_info['distance'] = distance
        
        return nearest_info
    
    def pick_axis_point(self) -> Optional[Dict]:
        """使用Open3D的pick_points功能选择坐标轴标记点"""
        if self.vis is None:
            return None
        
        try:
            # 使用Open3D的交互式点选择功能
            print("请在3D窗口中点击坐标轴上的黄色标记点...")
            print("按ESC键取消选择")
            
            # 获取所有标记点的位置
            pick_points = []
            for name, info in self.axis_points.items():
                pick_points.append(info['position'])
            
            # 使用Open3D的pick_points功能
            # 注意：这需要在交互模式下使用
            picked = self.vis.get_picked_points()
            
            if len(picked) > 0:
                # 检查选中的点是否接近某个标记点
                clicked_point = np.array(picked[0])
                return self._find_nearest_axis_point(clicked_point)
            
            return None
        except Exception as e:
            print(f"选择坐标轴标记点时出错: {e}")
            return None
    
    def get_axis_points_info(self) -> Dict:
        """获取所有坐标轴标记点的信息"""
        return self.axis_points.copy()
    
    def pick_point_from_cloud(self) -> Optional[Dict]:
        """
        从点云中选择一个点
        
        Returns:
            选中点的信息字典，包含坐标、所属点云等信息
        """
        if self.vis is None:
            return None
        
        try:
            # 使用Open3D的pick_points功能
            # 注意：这需要在交互模式下使用，用户需要在3D窗口中点击
            print("\n=== 点云选择模式 ===")
            print("请在3D窗口中点击点云上的任意点")
            print("按ESC键取消选择")
            
            # 获取所有点云
            all_point_clouds = []
            point_cloud_names = []
            
            for name, geometry in self.geometries.items():
                if isinstance(geometry, o3d.geometry.PointCloud) and 'coordinate' not in name:
                    all_point_clouds.append(geometry)
                    point_cloud_names.append(name)
            
            if not all_point_clouds:
                print("没有可选择的点云")
                return None
            
            # 使用Open3D的交互式点选择
            # 创建一个临时的可视化器用于点选择
            pick_vis = o3d.visualization.Visualizer()
            pick_vis.create_window(window_name="选择点云点 (点击后按Q确认)", width=800, height=600)
            
            # 添加所有点云
            for pcd in all_point_clouds:
                pick_vis.add_geometry(pcd)
            
            # 运行选择模式
            pick_vis.run()
            
            # 获取选中的点
            picked_indices = pick_vis.get_picked_points()
            pick_vis.destroy_window()
            
            if len(picked_indices) == 0:
                print("未选择任何点")
                return None
            
            # 找到选中点所属的点云
            picked_idx = picked_indices[0]
            point_info = None
            
            # 遍历所有点云，找到包含该点的点云
            current_idx = 0
            for i, (name, geometry) in enumerate(self.geometries.items()):
                if isinstance(geometry, o3d.geometry.PointCloud) and 'coordinate' not in name:
                    point_count = len(geometry.points)
                    if current_idx <= picked_idx < current_idx + point_count:
                        # 找到所属点云
                        local_idx = picked_idx - current_idx
                        point = np.asarray(geometry.points)[local_idx]
                        
                        point_info = {
                            'point': point,
                            'point_index': local_idx,
                            'global_index': picked_idx,
                            'cloud_name': name,
                            'cloud_type': self.point_cloud_info.get(name, {}).get('type', 'unknown'),
                            'cloud_point_count': point_count,
                            'has_normals': geometry.has_normals(),
                            'has_colors': geometry.has_colors()
                        }
                        
                        # 如果有法向量，添加法向量信息
                        if geometry.has_normals():
                            normal = np.asarray(geometry.normals)[local_idx]
                            point_info['normal'] = normal
                        
                        # 如果有颜色，添加颜色信息
                        if geometry.has_colors():
                            color = np.asarray(geometry.colors)[local_idx]
                            point_info['color'] = color
                        
                        break
                    
                    current_idx += point_count
            
            return point_info
            
        except Exception as e:
            print(f"选择点时出错: {e}")
            return None
    
    def find_nearest_point(self, query_point: np.ndarray, max_distance: float = 0.1) -> Optional[Dict]:
        """
        查找距离查询点最近的点云点
        
        Args:
            query_point: 查询点的3D坐标
            max_distance: 最大搜索距离
            
        Returns:
            最近点的信息字典
        """
        if self.vis is None:
            return None
        
        min_distance = float('inf')
        nearest_info = None
        
        for name, geometry in self.geometries.items():
            if isinstance(geometry, o3d.geometry.PointCloud) and 'coordinate' not in name:
                points = np.asarray(geometry.points)
                if len(points) == 0:
                    continue
                
                # 计算所有点到查询点的距离
                distances = np.linalg.norm(points - query_point, axis=1)
                min_idx = np.argmin(distances)
                min_dist = distances[min_idx]
                
                if min_dist < max_distance and min_dist < min_distance:
                    min_distance = min_dist
                    point = points[min_idx]
                    
                    nearest_info = {
                        'point': point,
                        'point_index': int(min_idx),
                        'cloud_name': name,
                        'cloud_type': self.point_cloud_info.get(name, {}).get('type', 'unknown'),
                        'cloud_point_count': len(points),
                        'distance': float(min_dist),
                        'has_normals': geometry.has_normals(),
                        'has_colors': geometry.has_colors()
                    }
                    
                    # 如果有法向量，添加法向量信息
                    if geometry.has_normals():
                        normals = np.asarray(geometry.normals)
                        nearest_info['normal'] = normals[min_idx]
                    
                    # 如果有颜色，添加颜色信息
                    if geometry.has_colors():
                        colors = np.asarray(geometry.colors)
                        nearest_info['color'] = colors[min_idx]
        
        return nearest_info
    
    def _calculate_axis_length(self) -> float:
        """根据当前点云数据计算合适的坐标轴长度"""
        if not self.geometries:
            return Config.COORDINATE_AXIS_LENGTH
        
        # 获取所有点云的边界框
        max_length = 0.0
        for name, geometry in self.geometries.items():
            # 跳过坐标系本身
            if 'coordinate' in name:
                continue
            if isinstance(geometry, o3d.geometry.PointCloud):
                if len(geometry.points) > 0:
                    bbox = geometry.get_axis_aligned_bounding_box()
                    extent = bbox.get_extent()
                    max_length = max(max_length, np.max(extent))
        
        # 坐标轴长度设为最大边界的15%（更显眼）
        if max_length > 0:
            return max(max_length * 0.15, Config.COORDINATE_AXIS_LENGTH)
        else:
            return Config.COORDINATE_AXIS_LENGTH
    
    def remove_coordinate_axes(self):
        """移除坐标系和网格"""
        axis_names = [
            'coordinate_axis_x', 'coordinate_arrow_x',
            'coordinate_axis_y', 'coordinate_arrow_y',
            'coordinate_axis_z', 'coordinate_arrow_z',
            'coordinate_label_x', 'coordinate_label_y', 'coordinate_label_z',
            'coordinate_grid_xy', 'coordinate_grid_xz', 'coordinate_grid_yz'
        ]
        for name in axis_names:
            if name in self.geometries:
                self.remove_geometry(name)
        self.axis_points.clear()
    
    def _load_and_display_transformed_frame_clouds(self, frame_id: int, frame_data: Dict,
                                                   x_offset: float, y_offset: float, z_offset: float,
                                                   transformed_frame_id_to_color_ground: Dict,
                                                   transformed_frame_id_to_color_plane: Dict):
        """
        加载并显示变换后的frame点云
        
        Args:
            frame_id: 帧ID
            frame_data: frame数据字典
            x_offset: x轴偏移量
            y_offset: y轴偏移量
            z_offset: z轴偏移量
            transformed_frame_id_to_color_ground: 输出参数，存储ground点云id到颜色的映射
            transformed_frame_id_to_color_plane: 输出参数，存储plane点云id到颜色的映射
        """
        # 从debug.txt读取变换矩阵
        T = self.data_loader.get_transform_matrix_from_debug(frame_id, 'T_opt_w_b')
        if T is None:
            print(f"无法从debug.txt读取变换矩阵 T_opt_w_b")
            return
        
        # 处理dense_cloud
        if frame_data['dense_cloud'] is not None:
            pcd = frame_data['dense_cloud']
            points = np.asarray(pcd.points)
            
            # 应用位姿变换
            points_homogeneous = np.ones((len(points), 4))
            points_homogeneous[:, :3] = points
            transformed_points_homogeneous = (T @ points_homogeneous.T).T
            transformed_points = transformed_points_homogeneous[:, :3]
            
            # 应用偏移
            transformed_points[:, 0] += x_offset
            transformed_points[:, 1] += y_offset
            transformed_points[:, 2] += z_offset
            
            # 创建变换后的点云
            transformed_pcd = o3d.geometry.PointCloud()
            transformed_pcd.points = o3d.utility.Vector3dVector(transformed_points)
            
            # 设置统一的法向量
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(transformed_points), 1))
            transformed_pcd.normals = o3d.utility.Vector3dVector(normals)
            
            # 为每个点生成不同的颜色
            num_points = len(transformed_points)
            distinct_colors = self.generate_distinct_colors(num_points)
            transformed_pcd.colors = o3d.utility.Vector3dVector(distinct_colors)
            
            # 存储颜色映射
            if frame_id not in self.transformed_dense_cloud_colors:
                self.transformed_dense_cloud_colors[frame_id] = {}
            for i, color in enumerate(distinct_colors):
                self.transformed_dense_cloud_colors[frame_id][i] = color.tolist() if isinstance(color, np.ndarray) else list(color)
            
            # 显示变换后的dense_cloud
            geometry_name = f"transformed_cloud_{frame_id}_T_opt_w_b_dense_cloud"
            self.add_geometry(transformed_pcd, geometry_name, None)
            
            # 存储点云信息
            self.point_cloud_info[geometry_name] = {
                'type': 'transformed_cloud',
                'frame_id': frame_id,
                'transform_name': 'T_opt_w_b',
                'file_name': 'dense_cloud',
                'x_offset': x_offset,
                'y_offset': y_offset,
                'z_offset': z_offset
            }
            
            print(f"已加载并变换dense_cloud: {geometry_name} (点数: {num_points})")
        
        # 处理ground点云
        for ground in frame_data['grounds']:
            ground_name = ground.get('name', '')
            pcd = ground['point_cloud']
            
            # 提取file_id
            file_id = None
            for pid, info in self.data_loader.ply_file_map.items():
                if info.get('name') == ground_name and info.get('type') == 'ground':
                    file_id = pid
                    break
            if file_id is None:
                file_id = self.data_loader._extract_file_id(ground_name)
            
            # 确保file_id是整数类型
            if file_id is None:
                file_id = 0
            elif isinstance(file_id, str):
                try:
                    file_id = int(file_id)
                except ValueError:
                    file_id = 0
            else:
                # 如果已经是数字类型，确保是整数
                file_id = int(file_id)
            
            # 应用位姿变换
            points = np.asarray(pcd.points)
            points_homogeneous = np.ones((len(points), 4))
            points_homogeneous[:, :3] = points
            transformed_points_homogeneous = (T @ points_homogeneous.T).T
            transformed_points = transformed_points_homogeneous[:, :3]
            
            # 应用偏移
            transformed_points[:, 0] += x_offset
            transformed_points[:, 1] += y_offset
            transformed_points[:, 2] += z_offset
            
            # 创建变换后的点云
            transformed_pcd = o3d.geometry.PointCloud()
            transformed_pcd.points = o3d.utility.Vector3dVector(transformed_points)
            
            # 设置统一的法向量
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(transformed_points), 1))
            transformed_pcd.normals = o3d.utility.Vector3dVector(normals)
            
            # 使用ID颜色（确保file_id是整数）
            file_id_int = int(file_id)
            color = self.get_color_by_id(file_id_int)
            transformed_frame_id_to_color_ground[file_id_int] = color
            
            # 显示变换后的ground点云
            geometry_name = f"transformed_cloud_{frame_id}_T_opt_w_b_ground_{file_id_int}"
            self.add_geometry(transformed_pcd, geometry_name, color)
            
            # 存储点云信息
            self.point_cloud_info[geometry_name] = {
                'type': 'transformed_cloud',
                'frame_id': frame_id,
                'transform_name': 'T_opt_w_b',
                'file_name': f'ground_{file_id_int}',
                'x_offset': x_offset,
                'y_offset': y_offset,
                'z_offset': z_offset,
                'id': file_id_int
            }
            
            print(f"已加载并变换ground_{file_id_int}: {geometry_name} (点数: {len(transformed_points)})")
        
        # 处理plane点云
        for plane in frame_data['planes']:
            plane_name = plane.get('name', '')
            pcd = plane['point_cloud']
            
            # 提取file_id
            file_id = None
            for pid, info in self.data_loader.ply_file_map.items():
                if info.get('name') == plane_name and info.get('type') == 'plane':
                    file_id = pid
                    break
            if file_id is None:
                file_id = self.data_loader._extract_file_id(plane_name)
            
            # 确保file_id是整数类型
            if file_id is None:
                file_id = 0
            elif isinstance(file_id, str):
                try:
                    file_id = int(file_id)
                except ValueError:
                    file_id = 0
            else:
                # 如果已经是数字类型，确保是整数
                file_id = int(file_id)
            
            # 应用位姿变换
            points = np.asarray(pcd.points)
            points_homogeneous = np.ones((len(points), 4))
            points_homogeneous[:, :3] = points
            transformed_points_homogeneous = (T @ points_homogeneous.T).T
            transformed_points = transformed_points_homogeneous[:, :3]
            
            # 应用偏移
            transformed_points[:, 0] += x_offset
            transformed_points[:, 1] += y_offset
            transformed_points[:, 2] += z_offset
            
            # 创建变换后的点云
            transformed_pcd = o3d.geometry.PointCloud()
            transformed_pcd.points = o3d.utility.Vector3dVector(transformed_points)
            
            # 设置统一的法向量
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(transformed_points), 1))
            transformed_pcd.normals = o3d.utility.Vector3dVector(normals)
            
            # 使用ID颜色（确保file_id是整数）
            file_id_int = int(file_id)
            color = self.get_color_by_id(file_id_int)
            transformed_frame_id_to_color_plane[file_id_int] = color
            
            # 显示变换后的plane点云
            geometry_name = f"transformed_cloud_{frame_id}_T_opt_w_b_plane_{file_id_int}"
            self.add_geometry(transformed_pcd, geometry_name, color)
            
            # 存储点云信息
            self.point_cloud_info[geometry_name] = {
                'type': 'transformed_cloud',
                'frame_id': frame_id,
                'transform_name': 'T_opt_w_b',
                'file_name': f'plane_{file_id_int}',
                'x_offset': x_offset,
                'y_offset': y_offset,
                'z_offset': z_offset,
                'id': file_id_int
            }
            
            print(f"已加载并变换plane_{file_id_int}: {geometry_name} (点数: {len(transformed_points)})")
    
    def load_and_display_frame(self, frame_id: int, frame_type: str = Config.FRAME_TYPE_FRAME,
                               x_offset: float = 0.0, y_offset: float = 0.0, z_offset: float = 10.0):
        """
        加载并显示指定帧的数据
        
        根据需求：
        - 第0帧：只显示map点云
        - 后续帧：先显示变换后的frame点云，再显示map点云（根据匹配关系设置颜色）
        
        Args:
            frame_id: 帧ID
            frame_type: 帧类型（frame或map）
            x_offset: x轴偏移量（用于位姿变换）
            y_offset: y轴偏移量（用于位姿变换）
            z_offset: z轴偏移量（用于位姿变换）
        """
        # 检查窗口是否关闭，如果关闭则重新创建
        if self.vis is not None:
            try:
                # 尝试poll_events，如果窗口关闭会返回False或抛出异常
                self.vis.poll_events()
            except:
                # 窗口已关闭或异常，需要重新创建
                self.vis = None
                self.geometries.clear()
        
        # 清除当前显示（保留坐标系）
        self.clear_all_geometries()
        
        # 清空之前的ply文件map（切换帧时）
        self.data_loader.clear_ply_file_map()
        
        # 第0帧特殊处理：只显示map点云
        if frame_id == 0:
            # 加载map数据
            map_data = self.data_loader.load_frame_data(frame_id, Config.FRAME_TYPE_MAP)
            
            # 创建窗口（如果不存在）
            if self.vis is None:
                self.vis = self.create_visualizer()
            else:
                if 'coordinate_axis_x' not in self.geometries:
                    self.add_coordinate_axes()
            
            # 显示map点云（使用ID颜色）
            self._display_point_clouds(map_data, Config.FRAME_TYPE_MAP, None, None)
            
            # 更新视图
            self.vis.poll_events()
            self.vis.update_renderer()
            
            self.current_frame_id = frame_id
            self.current_frame_type = Config.FRAME_TYPE_MAP
            print(f"已加载帧 {frame_id} (只显示map点云)")
            return
        
        # 后续帧处理（第1帧及以后）
        # 存储变换后frame点云的颜色映射
        transformed_frame_id_to_color_ground = {}  # 变换后frame中ground点云id到颜色的映射
        transformed_frame_id_to_color_plane = {}  # 变换后frame中plane点云id到颜色的映射
        match_mapping_ground = {}  # ground的cur_id (frame) -> other_id (map)的映射
        match_mapping_plane = {}  # plane的cur_id (frame) -> other_id (map)的映射
        map_id_to_color = {}  # map中点云id到颜色的映射（根据匹配的变换后frame点云颜色设置）
        dense_pt_match_mapping = {}  # dense_cloud的cur_id (frame) -> other_id (map)的映射
        
        if frame_type == Config.FRAME_TYPE_FRAME:
            # 步骤1: 加载frame数据
            frame_data = self.data_loader.load_frame_data(frame_id, Config.FRAME_TYPE_FRAME)
            
            # 步骤2: 应用位姿变换并首先绘制变换后的frame点云
            # 检查是否有debug.txt和变换矩阵
            debug_info = self.data_loader.load_debug_info(frame_id, use_dynamic_class=False)
            if debug_info and 'T_opt_w_b' in debug_info:
                # 应用位姿变换并显示变换后的frame点云
                self._load_and_display_transformed_frame_clouds(
                    frame_id, frame_data, x_offset, y_offset, z_offset,
                    transformed_frame_id_to_color_ground, transformed_frame_id_to_color_plane
                )
            else:
                # 如果没有变换矩阵，直接显示原始frame点云（使用ID颜色）
                print(f"[WARNING] 帧 {frame_id} 没有debug.txt或T_opt_w_b，直接显示原始frame点云")
                self._display_point_clouds(frame_data, Config.FRAME_TYPE_FRAME, None, None)
                # 记录颜色（用于后续匹配）
                for ground in frame_data['grounds']:
                    ground_name = ground.get('name', '')
                    file_id = None
                    for pid, info in self.data_loader.ply_file_map.items():
                        if info.get('name') == ground_name and info.get('type') == 'ground':
                            file_id = pid
                            break
                    if file_id is None:
                        file_id = self.data_loader._extract_file_id(ground_name)
                    if file_id is not None:
                        if isinstance(file_id, str):
                            try:
                                file_id = int(file_id)
                            except ValueError:
                                continue
                        color = self.get_color_by_id(file_id)
                        transformed_frame_id_to_color_ground[file_id] = color
                
                for plane in frame_data['planes']:
                    plane_name = plane.get('name', '')
                    file_id = None
                    for pid, info in self.data_loader.ply_file_map.items():
                        if info.get('name') == plane_name and info.get('type') == 'plane':
                            file_id = pid
                            break
                    if file_id is None:
                        file_id = self.data_loader._extract_file_id(plane_name)
                    if file_id is not None:
                        if isinstance(file_id, str):
                            try:
                                file_id = int(file_id)
                            except ValueError:
                                continue
                        color = self.get_color_by_id(file_id)
                        transformed_frame_id_to_color_plane[file_id] = color
            
            # 步骤3: 加载match.json，建立匹配关系
            self.data_loader.clear_ply_file_map()
            match_info = self.data_loader.load_match_info(frame_id, use_dynamic_class=False)
            print(f"[DEBUG] match_info类型: {type(match_info)}, match_info是否为None: {match_info is None}")
            if match_info:
                def extract_id_from_obj(obj):
                    """从对象中提取id，支持对象格式{"a": 1, "b": 3}和整数格式"""
                    if isinstance(obj, dict):
                        # 对象格式: {"a": 1, "b": 3}，返回(a, b)
                        a = obj.get('a')
                        b = obj.get('b')
                        return (a, b) if a is not None and b is not None else None
                    elif isinstance(obj, int):
                        # 整数格式，直接返回
                        return obj
                    else:
                        return None
                
                # 只支持 plane_match_infos 格式
                match_list = []
                if hasattr(match_info, 'plane_match_infos'):
                    match_list = match_info.plane_match_infos
                    print(f"[DEBUG] 从动态类属性获取plane_match_infos，数量: {len(match_list) if match_list else 0}")
                elif isinstance(match_info, dict) and 'plane_match_infos' in match_info:
                    match_list = match_info['plane_match_infos']
                    print(f"[DEBUG] 从字典获取plane_match_infos，数量: {len(match_list) if match_list else 0}")
                else:
                    print(f"[DEBUG] WARNING: 无法找到plane_match_infos")
                    if hasattr(match_info, '__dict__'):
                        print(f"[DEBUG] match_info的属性: {dir(match_info)}")
                    elif isinstance(match_info, dict):
                        print(f"[DEBUG] match_info的keys: {list(match_info.keys())}")
                
                print(f"[DEBUG] 开始解析 {len(match_list)} 个匹配项")
                for idx, match in enumerate(match_list):
                    # 处理动态类实例或字典两种情况
                    if hasattr(match, 'cur_id'):
                        cur_id_raw = match.cur_id
                        other_id_raw = match.other_id
                    elif isinstance(match, dict):
                        cur_id_raw = match.get('cur_id')
                        other_id_raw = match.get('other_id')
                    else:
                        print(f"[DEBUG] 匹配项 {idx}: 无法获取cur_id和other_id，match类型: {type(match)}")
                        continue
                    
                    # 提取cur_id和other_id
                    cur_id_info = extract_id_from_obj(cur_id_raw)
                    other_id_info = extract_id_from_obj(other_id_raw)
                    
                    if cur_id_info is None or other_id_info is None:
                        print(f"[DEBUG] 匹配项 {idx}: cur_id_raw={cur_id_raw}, other_id_raw={other_id_raw}, 提取失败")
                        continue
                    
                    # 处理cur_id为对象格式的情况 {"a": 1, "b": 3}
                    if isinstance(cur_id_info, tuple):
                        cur_type, cur_id = cur_id_info  # a=1表示plane, a=2表示ground
                    else:
                        # cur_id是整数，无法判断类型，跳过
                        continue
                    
                    # 处理other_id为对象格式的情况 {"a": 1, "b": 4}
                    if isinstance(other_id_info, tuple):
                        other_type, other_id = other_id_info
                    elif isinstance(other_id_info, int):
                        other_id = other_id_info
                        other_type = None
                    else:
                        continue
                    
                    # 检查匹配是否有效（other_id >= 0，允许0作为有效ID）
                    if not isinstance(other_id, int) or other_id < 0:
                        continue
                    
                    # 确保cur_id和other_id都是整数类型
                    cur_id = int(cur_id)
                    other_id = int(other_id)
                    
                    # 根据cur_type分别存储到对应的匹配映射中
                    if cur_type == 1:  # plane
                        match_mapping_plane[cur_id] = other_id
                        print(f"[DEBUG] 解析plane匹配: cur_id={cur_id} (frame_plane_{cur_id}), other_id={other_id} (map_plane_{other_id})")
                    elif cur_type == 2:  # ground
                        match_mapping_ground[cur_id] = other_id
                
                # 根据匹配关系，建立map点云的颜色映射（使用匹配的变换后frame点云颜色）
                for cur_id, other_id in match_mapping_ground.items():
                    # 确保cur_id和other_id都是整数类型
                    cur_id_int = int(cur_id)
                    other_id_int = int(other_id)
                    
                    if cur_id_int in transformed_frame_id_to_color_ground:
                        map_id_to_color[other_id_int] = transformed_frame_id_to_color_ground[cur_id_int]
                        print(f"[DEBUG] 建立ground匹配: transformed_frame_ground_{cur_id_int} -> map_ground_{other_id_int}, 颜色: RGB({transformed_frame_id_to_color_ground[cur_id_int][0]:.3f}, {transformed_frame_id_to_color_ground[cur_id_int][1]:.3f}, {transformed_frame_id_to_color_ground[cur_id_int][2]:.3f})")
                    else:
                        print(f"[DEBUG] WARNING: transformed_frame_ground_{cur_id_int}不在transformed_frame_id_to_color_ground中，无法建立map_ground_{other_id_int}的颜色映射")
                
                for cur_id, other_id in match_mapping_plane.items():
                    # 确保cur_id和other_id都是整数类型
                    cur_id_int = int(cur_id)
                    other_id_int = int(other_id)
                    
                    if cur_id_int in transformed_frame_id_to_color_plane:
                        map_id_to_color[other_id_int] = transformed_frame_id_to_color_plane[cur_id_int]
                        print(f"[DEBUG] 建立plane匹配: transformed_frame_plane_{cur_id_int} -> map_plane_{other_id_int}, 颜色: RGB({transformed_frame_id_to_color_plane[cur_id_int][0]:.3f}, {transformed_frame_id_to_color_plane[cur_id_int][1]:.3f}, {transformed_frame_id_to_color_plane[cur_id_int][2]:.3f})")
                    else:
                        print(f"[DEBUG] WARNING: transformed_frame_plane_{cur_id_int}不在transformed_frame_id_to_color_plane中，无法建立map_plane_{other_id_int}的颜色映射")
                        print(f"[DEBUG] transformed_frame_id_to_color_plane包含的keys: {list(transformed_frame_id_to_color_plane.keys())}")
                
                print(f"\n[DEBUG] 加载match.json: 找到 {len(match_mapping_ground)} 个ground匹配, {len(match_mapping_plane)} 个plane匹配")
                print(f"[DEBUG] 建立了 {len(map_id_to_color)} 个map点云颜色映射")
                print(f"[DEBUG] transformed_frame_id_to_color_plane包含的id: {list(transformed_frame_id_to_color_plane.keys())}")
                print(f"[DEBUG] match_mapping_plane: {match_mapping_plane}")
                print(f"[DEBUG] map_id_to_color包含的plane id: {[k for k in map_id_to_color.keys() if isinstance(k, int)]}")
            
            # 处理 dense_pt_match_infos
            dense_pt_match_mapping = {}  # dense_cloud的cur_id (frame) -> other_id (map)的映射
            if match_info:
                # 处理 dense_pt_match_infos
                if hasattr(match_info, 'dense_pt_match_infos'):
                    for match in match_info.dense_pt_match_infos:
                        if hasattr(match, 'cur_id') and hasattr(match, 'other_id'):
                            cur_id = match.cur_id
                            other_id = match.other_id
                            if isinstance(cur_id, int) and isinstance(other_id, int) and other_id >= 0:
                                dense_pt_match_mapping[cur_id] = other_id
                        elif isinstance(match, dict) and 'cur_id' in match and 'other_id' in match:
                            cur_id = match['cur_id']
                            other_id = match['other_id']
                            if isinstance(cur_id, int) and isinstance(other_id, int) and other_id >= 0:
                                dense_pt_match_mapping[cur_id] = other_id
                elif isinstance(match_info, dict) and 'dense_pt_match_infos' in match_info:
                    for match in match_info['dense_pt_match_infos']:
                        if isinstance(match, dict) and 'cur_id' in match and 'other_id' in match:
                            cur_id = match['cur_id']
                            other_id = match['other_id']
                            if isinstance(cur_id, int) and isinstance(other_id, int) and other_id >= 0:
                                dense_pt_match_mapping[cur_id] = other_id
                print(f"[DEBUG] 加载match.json: 找到 {len(dense_pt_match_mapping)} 个dense_cloud点匹配")
            
            # 如果需要匹配dense_cloud颜色，但transformed颜色还不存在，尝试从已加载的几何体中获取
            if (len(dense_pt_match_mapping) > 0 and 
                (frame_id not in self.transformed_dense_cloud_colors or 
                 len(self.transformed_dense_cloud_colors[frame_id]) == 0)):
                # 尝试从已加载的transformed dense_cloud几何体中获取颜色
                transformed_geometry_name = f"transformed_cloud_{frame_id}_T_opt_w_b_dense_cloud"
                if transformed_geometry_name in self.geometries:
                    transformed_pcd = self.geometries[transformed_geometry_name]
                    if isinstance(transformed_pcd, o3d.geometry.PointCloud) and transformed_pcd.has_colors():
                        colors_array = np.asarray(transformed_pcd.colors)
                        num_points = len(colors_array)
                        # 存储颜色映射
                        if frame_id not in self.transformed_dense_cloud_colors:
                            self.transformed_dense_cloud_colors[frame_id] = {}
                        for i in range(min(num_points, len(colors_array))):
                            self.transformed_dense_cloud_colors[frame_id][i] = colors_array[i].tolist()
                        print(f"[DEBUG] 从已加载的transformed dense_cloud几何体中获取了 {num_points} 个点的颜色")
                else:
                    # 如果几何体也不存在，尝试加载transformed dense_cloud（使用默认参数）
                    # 检查是否有debug.txt
                    debug_info = self.data_loader.load_debug_info(frame_id, use_dynamic_class=False)
                    if debug_info and 'T_opt_w_b' in debug_info:
                        print(f"[DEBUG] 尝试自动加载transformed dense_cloud以获取颜色...")
                        # 使用默认偏移量加载
                        try:
                            self.load_and_transform_point_cloud(frame_id, transform_name='T_opt_w_b', 
                                                               x_offset=0.0, y_offset=0.0, z_offset=10.0)
                            # 再次检查颜色是否已存储
                            if frame_id in self.transformed_dense_cloud_colors and len(self.transformed_dense_cloud_colors[frame_id]) > 0:
                                print(f"[DEBUG] 已自动加载transformed dense_cloud并获取了 {len(self.transformed_dense_cloud_colors[frame_id])} 个点的颜色")
                            else:
                                # 如果还是没有，尝试从刚加载的几何体中获取
                                if transformed_geometry_name in self.geometries:
                                    transformed_pcd = self.geometries[transformed_geometry_name]
                                    if isinstance(transformed_pcd, o3d.geometry.PointCloud) and transformed_pcd.has_colors():
                                        colors_array = np.asarray(transformed_pcd.colors)
                                        num_points = len(colors_array)
                                        if frame_id not in self.transformed_dense_cloud_colors:
                                            self.transformed_dense_cloud_colors[frame_id] = {}
                                        for i in range(num_points):
                                            self.transformed_dense_cloud_colors[frame_id][i] = colors_array[i].tolist()
                                        print(f"[DEBUG] 从刚加载的几何体中获取了 {num_points} 个点的颜色")
                        except Exception as e:
                            print(f"[DEBUG] 自动加载transformed dense_cloud失败: {e}")
                            import traceback
                            traceback.print_exc()
            
            # 步骤4: 加载map数据并显示map点云（使用匹配的变换后frame点云颜色）
            map_data = self.data_loader.load_frame_data(frame_id, Config.FRAME_TYPE_MAP)
            
            # 保存匹配和未匹配的map dense_cloud点id到txt文件
            if map_data['dense_cloud'] is not None and len(dense_pt_match_mapping) > 0:
                self._save_matched_and_unmatched_points(frame_id, map_data['dense_cloud'], dense_pt_match_mapping)
            
            # 显示map点云（使用匹配的变换后frame点云颜色，不匹配的用红色）
            self._display_point_clouds(map_data, Config.FRAME_TYPE_MAP, None, map_id_to_color, prefix="map_",
                                       dense_pt_match_mapping=dense_pt_match_mapping, frame_id=frame_id)
            
            # 绘制dense_cloud匹配点的连接线（按点类型分别创建）
            if len(dense_pt_match_mapping) > 0:
                self._draw_dense_pt_match_lines(frame_id, dense_pt_match_mapping, x_offset, y_offset, z_offset)
        else:
            # 如果不是FRAME类型，正常加载
            frame_data = self.data_loader.load_frame_data(frame_id, frame_type)
            
            if self.vis is None:
                self.vis = self.create_visualizer()
            else:
                if 'coordinate_axis_x' not in self.geometries:
                    self.add_coordinate_axes()
            
            self._display_point_clouds(frame_data, frame_type, None, None)
        
        # 创建窗口（如果不存在）
        if self.vis is None:
            self.vis = self.create_visualizer()
        else:
            if 'coordinate_axis_x' not in self.geometries:
                self.add_coordinate_axes()
        
        # 更新视图
        self.vis.poll_events()
        self.vis.update_renderer()
        
        self.current_frame_id = frame_id
        self.current_frame_type = frame_type
    
    def _display_point_clouds(self, frame_data: Dict, frame_type: str, 
                             match_mapping: Optional[Dict[str, Dict[int, int]]] = None,
                             map_id_to_color: Optional[Dict[int, List[float]]] = None,
                             prefix: str = "",
                             dense_pt_match_mapping: Optional[Dict[int, int]] = None,
                             frame_id: Optional[int] = None):
        """
        显示点云数据
        
        Args:
            frame_data: 帧数据字典
            frame_type: 帧类型（frame或map）
            match_mapping: 匹配映射字典，格式为 {'ground': {cur_id -> other_id}, 'plane': {cur_id -> other_id}}，
                          如果为None则不使用匹配
            map_id_to_color: map中点云id到颜色的映射，用于设置frame点云颜色
            prefix: 点云名称前缀（用于区分map和frame点云）
        """
        # 显示dense_cloud
        if frame_data['dense_cloud'] is not None:
            dense_name = f"{prefix}dense_cloud" if prefix else 'dense_cloud'
            print(f"\n[DEBUG] _display_point_clouds: 加载 dense_cloud")
            print(f"  - 名称: {dense_name}")
            
            pcd = frame_data['dense_cloud']
            num_points = len(pcd.points)
            
            # 如果是frame类型，设置统一的法向量
            if frame_type == Config.FRAME_TYPE_FRAME:
                uniform_normal = np.array([0.0, 0.0, 1.0])
                normals = np.tile(uniform_normal, (num_points, 1))
                pcd.normals = o3d.utility.Vector3dVector(normals)
            
            # 如果是map类型，且存在匹配关系和transformed颜色，根据匹配关系设置每个点的颜色
            print(f"[DEBUG] _display_point_clouds dense_cloud条件检查:")
            print(f"  - prefix: {prefix}")
            print(f"  - dense_pt_match_mapping is not None: {dense_pt_match_mapping is not None}")
            print(f"  - frame_id: {frame_id}")
            print(f"  - frame_id in transformed_dense_cloud_colors: {frame_id in self.transformed_dense_cloud_colors if frame_id is not None else False}")
            if frame_id is not None and frame_id in self.transformed_dense_cloud_colors:
                print(f"  - transformed_dense_cloud_colors[{frame_id}] 有 {len(self.transformed_dense_cloud_colors[frame_id])} 个颜色")
            
            if (prefix == "map_" and dense_pt_match_mapping is not None and 
                frame_id is not None and frame_id in self.transformed_dense_cloud_colors and
                len(self.transformed_dense_cloud_colors[frame_id]) > 0):
                
                transformed_colors = self.transformed_dense_cloud_colors[frame_id]
                # 创建颜色数组，初始化为红色（未匹配的点显示为红色）
                red_color = [1.0, 0.0, 0.0]  # 红色
                colors_array = np.tile(np.array(red_color), (num_points, 1))
                
                # 根据匹配关系设置颜色（匹配的点使用变换后frame点的颜色）
                matched_count = 0
                for cur_id, other_id in dense_pt_match_mapping.items():
                    if cur_id in transformed_colors and other_id >= 0 and other_id < num_points:
                        colors_array[other_id] = transformed_colors[cur_id]
                        matched_count += 1
                
                # 将颜色设置到点云对象上
                pcd.colors = o3d.utility.Vector3dVector(colors_array)
                unmatched_count = num_points - matched_count
                print(f"  - 根据匹配关系设置了 {matched_count} 个点的颜色（共 {num_points} 个点），未匹配 {unmatched_count} 个点显示为红色")
                self.add_geometry(pcd, dense_name, None)  # 传递None以使用点云对象上已设置的颜色
            else:
                # 如果不是map类型或没有匹配关系，使用默认颜色（非红色）
                dense_color = self.colors['dense_cloud']
                print(f"  - 使用默认颜色: RGB({dense_color[0]:.3f}, {dense_color[1]:.3f}, {dense_color[2]:.3f})")
                if prefix == "map_" and dense_pt_match_mapping is not None:
                    print(f"  - [WARNING] 无法应用匹配颜色: prefix={prefix}, match_mapping存在={dense_pt_match_mapping is not None}, frame_id={frame_id}, 颜色数据存在={frame_id in self.transformed_dense_cloud_colors if frame_id is not None else False}")
                self.add_geometry(pcd, dense_name, dense_color)
            
            # 存储点云信息
            self.point_cloud_info[dense_name] = {
                'type': 'dense_cloud',
                'frame_id': frame_data.get('frame_id'),
                'frame_type': frame_type
            }
        
        # 显示ground点云
        for ground in frame_data['grounds']:
            ground_name = ground.get('name', '')
            # 从ply_file_map中查找对应的id
            file_id = None
            for pid, info in self.data_loader.ply_file_map.items():
                if info.get('name') == ground_name and info.get('type') == 'ground':
                    file_id = pid
                    break

            # 如果找不到，尝试从文件名中提取id
            if file_id is None:
                file_id = self.data_loader._extract_file_id(ground_name)

            # 确保file_id是整数
            if file_id is None:
                file_id = 0
            elif isinstance(file_id, str):
                try:
                    file_id = int(file_id)
                except ValueError:
                    file_id = 0

            name = f"{prefix}ground_{file_id}" if prefix else f"ground_{file_id}"
            print(f"\n[DEBUG] _display_point_clouds: 加载 ground 点云")
            print(f"  - 文件名: {ground_name}")
            print(f"  - 显示名称: {name}")
            print(f"  - file_id: {file_id}")
            
            # 如果是frame类型，设置统一的法向量
            if frame_type == Config.FRAME_TYPE_FRAME:
                uniform_normal = np.array([0.0, 0.0, 1.0])
                normals = np.tile(uniform_normal, (len(ground['point_cloud'].points), 1))
                ground['point_cloud'].normals = o3d.utility.Vector3dVector(normals)
            
            # 根据match.json设置颜色
            pcd = ground['point_cloud']
            if prefix == "map_" and map_id_to_color is not None:
                # 显示map点云，使用匹配的frame点云颜色
                # 确保file_id是整数类型，与map_id_to_color的key类型一致
                file_id_int = int(file_id) if file_id is not None else 0
                
                # 尝试查找匹配的颜色（支持整数key）
                color = None
                if file_id_int in map_id_to_color:
                    color = map_id_to_color[file_id_int]
                    print(f"  - map点云匹配到frame点云，使用颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
                else:
                    # map点云未匹配，使用红色
                    color = [1.0, 0.0, 0.0]  # 红色
                    print(f"  - map点云未匹配，使用红色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
                    print(f"  - [DEBUG] map_id_to_color中的keys: {list(map_id_to_color.keys())}, file_id={file_id_int}, file_id类型={type(file_id_int)}")
            elif match_mapping is not None and map_id_to_color is not None and frame_type == Config.FRAME_TYPE_FRAME:
                # 显示frame点云，使用正常id颜色（不再根据匹配关系设置）
                color = self.get_color_by_id(file_id)
                color = [max(0.0, min(1.0, c)) for c in color]
                print(f"  - frame点云颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            else:
                # 使用文件实际id对应的颜色（正常显示）
                color = self.get_color_by_id(file_id)
                color = [max(0.0, min(1.0, c)) for c in color]
                print(f"  - 最终颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            
            self.add_geometry(pcd, name, color)
            
            # 存储点云信息
            self.point_cloud_info[name] = {
                'type': 'ground',
                'frame_id': frame_data.get('frame_id'),
                'frame_type': frame_type,
                'metadata': ground.get('metadata'),
                'original_name': ground_name,
                'id': file_id
            }
        
        # 显示plane点云
        for plane in frame_data['planes']:
            plane_name = plane.get('name', '')
            # 从ply_file_map中查找对应的id
            file_id = None
            for pid, info in self.data_loader.ply_file_map.items():
                if info.get('name') == plane_name and info.get('type') == 'plane':
                    file_id = pid
                    break

            # 如果找不到，尝试从文件名中提取id
            if file_id is None:
                file_id = self.data_loader._extract_file_id(plane_name)

            # 确保file_id是整数
            if file_id is None:
                file_id = 0
            elif isinstance(file_id, str):
                try:
                    file_id = int(file_id)
                except ValueError:
                    file_id = 0

            name = f"{prefix}plane_{file_id}" if prefix else f"plane_{file_id}"
            print(f"\n[DEBUG] _display_point_clouds: 加载 plane 点云")
            print(f"  - 文件名: {plane_name}")
            print(f"  - 显示名称: {name}")
            print(f"  - file_id: {file_id}")
            
            # 如果是frame类型，设置统一的法向量
            if frame_type == Config.FRAME_TYPE_FRAME:
                uniform_normal = np.array([0.0, 0.0, 1.0])
                normals = np.tile(uniform_normal, (len(plane['point_cloud'].points), 1))
                plane['point_cloud'].normals = o3d.utility.Vector3dVector(normals)
            
            # 根据match.json设置颜色
            pcd = plane['point_cloud']
            if prefix == "map_" and map_id_to_color is not None:
                # 显示map点云，使用匹配的frame点云颜色
                # 确保file_id是整数类型，与map_id_to_color的key类型一致
                file_id_int = int(file_id) if file_id is not None else 0
                
                # 尝试查找匹配的颜色（支持整数key）
                color = None
                if file_id_int in map_id_to_color:
                    color = map_id_to_color[file_id_int]
                    print(f"  - map点云匹配到frame点云，使用颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
                else:
                    # map点云未匹配，使用红色
                    color = [1.0, 0.0, 0.0]  # 红色
                    print(f"  - map点云未匹配，使用红色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
                    print(f"  - [DEBUG] map_id_to_color中的keys: {list(map_id_to_color.keys())}, file_id={file_id_int}, file_id类型={type(file_id_int)}")
                    print(f"  - [DEBUG] 尝试查找的key: {file_id_int}, key是否在map中: {file_id_int in map_id_to_color}")
            elif match_mapping is not None and map_id_to_color is not None and frame_type == Config.FRAME_TYPE_FRAME:
                # 显示frame点云，使用正常id颜色（不再根据匹配关系设置）
                color = self.get_color_by_id(file_id)
                color = [max(0.0, min(1.0, c)) for c in color]
                print(f"  - frame点云颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            else:
                # 使用文件实际id对应的颜色（正常显示）
                color = self.get_color_by_id(file_id)
                color = [max(0.0, min(1.0, c)) for c in color]
                print(f"  - 最终颜色: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            
            self.add_geometry(pcd, name, color)
            
            # 存储点云信息
            self.point_cloud_info[name] = {
                'type': 'plane',
                'frame_id': frame_data.get('frame_id'),
                'frame_type': frame_type,
                'metadata': plane.get('metadata'),
                'original_name': plane_name,
                'id': file_id
            }
    
    def update_view(self):
        """更新视图显示"""
        if self.vis is not None:
            self.vis.poll_events()
            self.vis.update_renderer()
    
    def is_window_open(self) -> bool:
        """检查窗口是否仍然打开"""
        if self.vis is None:
            return False
        try:
            # poll_events()返回True表示窗口仍然打开
            return self.vis.poll_events()
        except:
            return False
    
    def destroy(self):
        """销毁可视化窗口"""
        self.running = False
        if self.vis is not None:
            try:
                self.vis.destroy_window()
            except:
                pass  # 窗口可能已经关闭
            self.vis = None
            self.geometries.clear()
    
    def get_frame_info(self, frame_id: int) -> Dict:
        """获取帧的信息"""
        frame_data = self.data_loader.load_frame_data(frame_id, self.current_frame_type)
        return {
            'frame_id': frame_id,
            'frame_type': self.current_frame_type,
            'has_dense_cloud': frame_data['dense_cloud'] is not None,
            'num_grounds': len(frame_data['grounds']),
            'num_planes': len(frame_data['planes'])
        }
    
    def load_and_transform_point_cloud(self, frame_id: int, transform_name: str = 'T_opt_w_b', 
                                       x_offset: float = 0.0, y_offset: float = 0.0, z_offset: float = 10.0):
        """
        读取当前帧frame文件夹的所有ply文件，应用位姿变换矩阵，应用x、y、z轴偏移，并叠加显示到坐标系中
        
        Args:
            frame_id: 帧ID
            transform_name: 变换矩阵名称，默认为'T_opt_w_b'，也可以是'T_init_w_b'
            x_offset: x轴偏移量，默认0个单位
            y_offset: y轴偏移量，默认0个单位
            z_offset: z轴偏移量，默认10个单位
        """
        # 1. 从debug.txt读取变换矩阵T
        T = self.data_loader.get_transform_matrix_from_debug(frame_id, transform_name)
        if T is None:
            print(f"无法从debug.txt读取变换矩阵 {transform_name}")
            return
        
        # 2. 获取当前帧frame文件夹的所有ply文件
        frame_path = Config.get_frame_data_path(frame_id, Config.FRAME_TYPE_FRAME)
        
        if not frame_path.exists():
            print(f"帧文件夹不存在: {frame_path}")
            return
        
        # 查找所有ply文件
        ply_files = []
        for file_path in frame_path.iterdir():
            if file_path.is_file() and file_path.suffix == Config.PLY_EXTENSION:
                ply_files.append(file_path)
        
        if len(ply_files) == 0:
            print(f"帧文件夹中没有找到ply文件: {frame_path}")
            return
        
        # 先清除之前的所有变换点云（以frame_id和transform_name为标识）
        # 包括可见和隐藏的变换点云
        transformed_geometry_names = [
            name for name in self.geometries.keys() 
            if name.startswith(f"transformed_cloud_{frame_id}_{transform_name}_")
        ]
        for name in transformed_geometry_names:
            self.remove_geometry(name)
        
        # 清除隐藏的变换点云
        hidden_transformed_names = [
            name for name in self.hidden_geometries.keys()
            if name.startswith(f"transformed_cloud_{frame_id}_{transform_name}_")
        ]
        for name in hidden_transformed_names:
            # 从hidden_geometries中移除
            if name in self.hidden_geometries:
                del self.hidden_geometries[name]
            # 如果还在point_cloud_info中，也移除
            if name in self.point_cloud_info:
                del self.point_cloud_info[name]
        
        # 3. 遍历所有ply文件，对每个文件应用变换
        total_points = 0
        for ply_file in sorted(ply_files):
            # 加载点云
            pcd = self.data_loader.load_point_cloud(ply_file)
            if pcd is None or len(pcd.points) == 0:
                print(f"无法加载点云或点云为空: {ply_file}")
                continue
            
            # 将每个点使用位姿变换矩阵变换
            points = np.asarray(pcd.points)
            
            # 转换为齐次坐标
            points_homogeneous = np.ones((len(points), 4))
            points_homogeneous[:, :3] = points
            
            # 应用变换矩阵
            transformed_points_homogeneous = (T @ points_homogeneous.T).T
            transformed_points = transformed_points_homogeneous[:, :3]
            
            # 应用x、y、z轴偏移
            transformed_points[:, 0] += x_offset
            transformed_points[:, 1] += y_offset
            transformed_points[:, 2] += z_offset
            
            # 创建新的点云对象
            transformed_pcd = o3d.geometry.PointCloud()
            transformed_pcd.points = o3d.utility.Vector3dVector(transformed_points)
            
            # 注意：数据文件不包含颜色信息，颜色由add_geometry函数设置
            
            # 设置统一的法向量（固定值）
            uniform_normal = np.array([0.0, 0.0, 1.0])
            normals = np.tile(uniform_normal, (len(transformed_points), 1))
            transformed_pcd.normals = o3d.utility.Vector3dVector(normals)
            
            # 5. 叠加绘制到坐标系中，使用文件名作为标识
            file_stem = ply_file.stem  # 文件名（不含扩展名）
            geometry_name = f"transformed_cloud_{frame_id}_{transform_name}_{file_stem}"
            
            # 检查对应的原始点云类型是否可见（用于同步显示/隐藏）
            # 注意：在切换帧时，应该默认显示所有变换点云，不管map文件夹中是否有对应的同名文件
            # 因为frame文件夹和map文件夹中的点云ID可能不一致
            # 只有在用户手动隐藏了某个类型的点云时，才隐藏对应的变换点云
            
            # 检查map文件夹中是否有对应类型的点云（包括可见和隐藏的）
            has_corresponding_type = False
            if file_stem == 'dense_cloud':
                has_corresponding_type = 'dense_cloud' in self.geometries or 'dense_cloud' in self.hidden_geometries
            elif file_stem.startswith('ground_'):
                has_corresponding_type = any(name.startswith('ground_') for name in list(self.geometries.keys()) + list(self.hidden_geometries.keys())
                                           if not name.startswith('transformed_cloud_'))
            elif file_stem.startswith('plane_'):
                has_corresponding_type = any(name.startswith('plane_') for name in list(self.geometries.keys()) + list(self.hidden_geometries.keys())
                                            if not name.startswith('transformed_cloud_'))
            
            # 检查对应类型的点云是否可见
            original_type_visible = True
            if has_corresponding_type:
                # map中有对应类型的点云，检查是否可见
                if file_stem == 'dense_cloud':
                    original_type_visible = 'dense_cloud' in self.geometries
                elif file_stem.startswith('ground_'):
                    original_type_visible = any(name.startswith('ground_') for name in self.geometries.keys() 
                                               if not name.startswith('transformed_cloud_'))
                elif file_stem.startswith('plane_'):
                    original_type_visible = any(name.startswith('plane_') for name in self.geometries.keys() 
                                               if not name.startswith('transformed_cloud_'))
            # 如果map中没有对应类型的点云，original_type_visible保持为True，默认显示变换点云
            
            # 根据文件类型分配颜色
            transform_color = None
            use_per_point_colors = False  # 是否使用每个点不同的颜色
            
            if file_stem == 'dense_cloud':
                # dense_cloud：为每个点生成不同的颜色
                num_points = len(transformed_points)
                distinct_colors = self.generate_distinct_colors(num_points)
                # 将颜色设置到点云对象上
                transformed_pcd.colors = o3d.utility.Vector3dVector(distinct_colors)
                use_per_point_colors = True
                
                # 存储每个点的颜色映射（cur_id -> color），用于后续匹配map的dense_cloud
                if frame_id not in self.transformed_dense_cloud_colors:
                    self.transformed_dense_cloud_colors[frame_id] = {}
                # 将颜色数组转换为字典，key为点的索引（cur_id），value为颜色
                colors_dict = {}
                for i, color in enumerate(distinct_colors):
                    colors_dict[i] = color.tolist() if isinstance(color, np.ndarray) else list(color)
                self.transformed_dense_cloud_colors[frame_id] = colors_dict
                
                print(f"  - dense_cloud: 为 {num_points} 个点生成了不同的颜色，已存储颜色映射")
            elif file_stem.startswith('ground_'):
                # 从文件名中提取ground的id
                try:
                    ground_id = int(file_stem.split('_')[1])
                    transform_color = self.get_color_by_id(ground_id)
                except (ValueError, IndexError):
                    transform_color = self.get_color_by_id(0)
            elif file_stem.startswith('plane_'):
                # 从文件名中提取plane的id
                try:
                    plane_id = int(file_stem.split('_')[1])
                    transform_color = self.get_color_by_id(plane_id)
                except (ValueError, IndexError):
                    transform_color = self.get_color_by_id(0)
            else:
                # 未知类型，使用默认灰色
                transform_color = [0.5, 0.5, 0.5]
            
            # 如果使用了每个点不同的颜色，传递None给add_geometry（使用点云对象上已设置的颜色）
            # 否则使用统一的颜色
            if use_per_point_colors:
                self.add_geometry(transformed_pcd, geometry_name, None)
            else:
                # 确保颜色值在0-1范围内
                transform_color = [max(0.0, min(1.0, c)) for c in transform_color]
                self.add_geometry(transformed_pcd, geometry_name, transform_color)
            
            # 如果map中有对应类型的点云但被隐藏了，隐藏变换点云（用于同步显示/隐藏）
            # 如果map中没有对应类型的点云，默认显示变换点云
            if has_corresponding_type and not original_type_visible:
                self.hide_geometry(geometry_name)
            
            # 存储点云信息
            self.point_cloud_info[geometry_name] = {
                'type': 'transformed_cloud',
                'frame_id': frame_id,
                'transform_name': transform_name,
                'file_name': file_stem,
                'x_offset': x_offset,
                'y_offset': y_offset,
                'z_offset': z_offset,
                'original_point_count': len(points)
            }
            
            total_points += len(points)
            print(f"已加载并变换点云: {geometry_name} (文件: {ply_file.name}, 点数: {len(points)}, 可见: {original_type_visible})")
        
        # 更新视图
        self.update_view()
        
        print(f"变换完成: 共处理 {len(ply_files)} 个ply文件，总点数: {total_points}")
        print(f"  变换矩阵: {transform_name}")
        print(f"  偏移: X={x_offset}, Y={y_offset}, Z={z_offset}")
    
    def _save_matched_and_unmatched_points(self, frame_id: int, map_dense_cloud: o3d.geometry.PointCloud, 
                                           dense_pt_match_mapping: Dict[int, int]):
        """
        保存匹配和未匹配的map dense_cloud点id到txt文件
        
        Args:
            frame_id: 帧ID
            map_dense_cloud: map的dense_cloud点云
            dense_pt_match_mapping: 匹配映射字典，格式为 {cur_id (frame): other_id (map)}
        """
        if map_dense_cloud is None:
            return
        
        num_points = len(map_dense_cloud.points)
        
        # 获取所有匹配的map点id（other_id）
        matched_map_ids = set()
        for cur_id, other_id in dense_pt_match_mapping.items():
            if isinstance(other_id, int) and other_id >= 0 and other_id < num_points:
                matched_map_ids.add(other_id)
        
        # 获取所有map点id（0到num_points-1）
        all_map_ids = set(range(num_points))
        
        # 计算未匹配的点id
        unmatched_map_ids = all_map_ids - matched_map_ids
        
        # 按从大到小排序
        matched_ids_sorted = sorted(matched_map_ids, reverse=True)
        unmatched_ids_sorted = sorted(unmatched_map_ids, reverse=True)
        
        # 保存到txt文件
        frame_dir = Config.get_data_frame_path(frame_id)
        matched_file = frame_dir / f"matched_map_dense_cloud_points_{frame_id}.txt"
        unmatched_file = frame_dir / f"unmatched_map_dense_cloud_points_{frame_id}.txt"
        
        # 保存匹配的点id
        try:
            with open(matched_file, 'w', encoding='utf-8') as f:
                f.write(f"匹配的map dense_cloud点id（共 {len(matched_ids_sorted)} 个，按id从大到小排序）\n")
                f.write("=" * 50 + "\n")
                for point_id in matched_ids_sorted:
                    # 找到对应的frame点id
                    frame_id_for_point = None
                    for cur_id, other_id in dense_pt_match_mapping.items():
                        if other_id == point_id:
                            frame_id_for_point = cur_id
                            break
                    f.write(f"map_id: {point_id:6d} -> frame_id: {frame_id_for_point}\n")
            print(f"[INFO] 已保存匹配的点id到: {matched_file}")
            print(f"  - 匹配的点数: {len(matched_ids_sorted)}")
        except Exception as e:
            print(f"[ERROR] 保存匹配的点id失败: {e}")
        
        # 保存未匹配的点id
        try:
            with open(unmatched_file, 'w', encoding='utf-8') as f:
                f.write(f"未匹配的map dense_cloud点id（共 {len(unmatched_ids_sorted)} 个，按id从大到小排序）\n")
                f.write("=" * 50 + "\n")
                for point_id in unmatched_ids_sorted:
                    f.write(f"{point_id}\n")
            print(f"[INFO] 已保存未匹配的点id到: {unmatched_file}")
            print(f"  - 未匹配的点数: {len(unmatched_ids_sorted)}")
        except Exception as e:
            print(f"[ERROR] 保存未匹配的点id失败: {e}")
    
    def _draw_dense_pt_match_lines(self, frame_id: int, dense_pt_match_mapping: Dict[int, int],
                                   x_offset: float, y_offset: float, z_offset: float):
        """
        绘制dense_cloud匹配点的连接线（按点类型分别创建，便于分别控制显示/隐藏）
        
        Args:
            frame_id: 帧ID
            dense_pt_match_mapping: 匹配映射字典，格式为 {cur_id (frame): other_id (map)}
            x_offset: x轴偏移量
            y_offset: y轴偏移量
            z_offset: z轴偏移量
        """
        if self.vis is None:
            return
        
        # 获取transformed dense_cloud点云
        transformed_dense_name = f"transformed_cloud_{frame_id}_T_opt_w_b_dense_cloud"
        transformed_pcd = None
        
        if transformed_dense_name in self.geometries:
            transformed_pcd = self.geometries[transformed_dense_name]
        elif transformed_dense_name in self.hidden_geometries:
            transformed_pcd = self.hidden_geometries[transformed_dense_name]['geometry']
        
        # 获取map dense_cloud点云
        map_dense_name = "map_dense_cloud"
        map_pcd = None
        
        if map_dense_name in self.geometries:
            map_pcd = self.geometries[map_dense_name]
        elif map_dense_name in self.hidden_geometries:
            map_pcd = self.hidden_geometries[map_dense_name]['geometry']
        
        # 检查点云是否存在
        if transformed_pcd is None or map_pcd is None:
            print(f"[WARNING] 无法绘制连接线: transformed_dense_cloud或map_dense_cloud不存在")
            return
        
        if not isinstance(transformed_pcd, o3d.geometry.PointCloud) or not isinstance(map_pcd, o3d.geometry.PointCloud):
            print(f"[WARNING] 无法绘制连接线: 点云类型不正确")
            return
        
        # 获取点坐标
        transformed_points = np.asarray(transformed_pcd.points)
        map_points = np.asarray(map_pcd.points)
        
        # 根据点类型分类匹配关系
        # matched_to_dense: 在dense_pt_match_mapping中的点（这些点有对应的连接线）
        matched_to_dense_mapping = dense_pt_match_mapping.copy()
        
        # 为matched_to_dense类型创建连接线
        if len(matched_to_dense_mapping) > 0:
            self._create_lineset_for_point_type(
                frame_id, 'matched_to_dense', matched_to_dense_mapping,
                transformed_points, map_points
            )
        
        # 存储匹配映射信息，供GUI使用
        if not hasattr(self, 'dense_pt_match_mappings'):
            self.dense_pt_match_mappings = {}
        self.dense_pt_match_mappings[frame_id] = {
            'matched_to_dense': matched_to_dense_mapping
        }
        
        print(f"[INFO] 已绘制 {len(matched_to_dense_mapping)} 条dense_cloud匹配点连接线（matched_to_dense类型）")
    
    def _create_lineset_for_point_type(self, frame_id: int, point_type: str, 
                                      match_mapping: Dict[int, int],
                                      transformed_points: np.ndarray, 
                                      map_points: np.ndarray):
        """
        为指定点类型创建连接线LineSet
        
        Args:
            frame_id: 帧ID
            point_type: 点类型（'matched_to_dense', 'matched_to_plane', 'unmatched'）
            match_mapping: 匹配映射字典，格式为 {cur_id (frame): other_id (map)}
            transformed_points: transformed dense_cloud的点坐标数组
            map_points: map dense_cloud的点坐标数组
        """
        if len(match_mapping) == 0:
            return
        
        # 创建连接线的点和线段
        line_points = []
        line_indices = []
        
        point_idx = 0
        valid_matches = 0
        
        for cur_id, other_id in match_mapping.items():
            # 检查索引是否有效
            if cur_id < 0 or cur_id >= len(transformed_points):
                continue
            if other_id < 0 or other_id >= len(map_points):
                continue
            
            # 添加frame点
            frame_point = transformed_points[cur_id]
            line_points.append(frame_point)
            frame_point_idx = point_idx
            point_idx += 1
            
            # 添加map点
            map_point = map_points[other_id]
            line_points.append(map_point)
            map_point_idx = point_idx
            point_idx += 1
            
            # 添加线段（连接frame点和map点）
            line_indices.append([frame_point_idx, map_point_idx])
            valid_matches += 1
        
        if len(line_points) == 0:
            return
        
        # 创建LineSet
        lineset = o3d.geometry.LineSet()
        lineset.points = o3d.utility.Vector3dVector(np.array(line_points))
        lineset.lines = o3d.utility.Vector2iVector(np.array(line_indices))
        
        # 设置连接线颜色（使用黄色，便于区分）
        line_colors = np.tile(np.array([1.0, 1.0, 0.0]), (len(line_indices), 1))  # 黄色
        lineset.colors = o3d.utility.Vector3dVector(line_colors)
        
        # 添加到可视化器
        geometry_name = f"dense_pt_match_lines_{frame_id}_{point_type}"
        
        # 如果已存在，先移除
        if geometry_name in self.geometries:
            self.remove_geometry(geometry_name)
        
        self.add_geometry(lineset, geometry_name, None)
