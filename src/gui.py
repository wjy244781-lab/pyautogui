"""
GUI界面模块
提供图形用户界面，用于切换帧和控制可视化
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import open3d as o3d
from .config import Config
from .visualizer import PointCloudVisualizer


class PointCloudGUI:
    """点云可视化GUI类"""
    
    def __init__(self):
        """初始化GUI"""
        self.visualizer = PointCloudVisualizer()
        self.available_frames = Config.get_available_frames()
        self.current_frame_index = 0
        self.current_frame_type = Config.FRAME_TYPE_FRAME
        
        # 回调函数
        self.on_frame_changed: Optional[Callable] = None
        
        # GUI窗口
        self.root = None
        self.frame_label = None
        self.type_label = None
        self.debug_info_label = None
        self.hover_info_label = None  # 悬浮信息显示标签
        self.running = False
        
        # 匹配关系复选框存储
        self.match_checkboxes = {}  # {match_index: (var, match_data)}
    
    def create_control_panel(self):
        """创建控制面板"""
        self.root = tk.Tk()
        self.root.title("点云可视化控制面板")
        self.root.geometry("1400x800")  # 增加宽度以容纳左右分栏
        
        # 设置控制面板始终置顶，确保它始终显示在Open3D窗口之上
        # 这样即使点击Open3D窗口，控制面板也会保持在最前面
        self.root.attributes('-topmost', True)
        
        # 当窗口获得焦点时，确保它保持在最前面
        def ensure_on_top():
            try:
                if self.root.winfo_exists():
                    self.root.attributes('-topmost', True)
                    self.root.lift()
            except:
                pass
        
        # 绑定窗口事件，确保控制面板始终在最前面
        self.root.bind('<FocusIn>', lambda e: ensure_on_top())
        self.root.bind('<Map>', lambda e: ensure_on_top())  # 窗口显示时
        
        # 配置根窗口的网格权重
        self.root.columnconfigure(0, weight=0)  # 左侧控制面板不扩展
        self.root.columnconfigure(1, weight=1)  # 右侧Debug面板可扩展
        self.root.rowconfigure(0, weight=1)
        
        # 主框架 - 左右分栏容器
        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        main_container.columnconfigure(0, weight=0)  # 左侧控制面板
        main_container.columnconfigure(1, weight=1)  # 右侧Debug面板
        main_container.rowconfigure(0, weight=1)
        
        # 左侧控制面板框架
        left_panel = ttk.Frame(main_container, width=300)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.columnconfigure(0, weight=1)
        
        # 主框架（左侧控制按钮区域）
        main_frame = ttk.Frame(left_panel, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        
        # 帧信息显示
        info_frame = ttk.LabelFrame(main_frame, text="当前帧信息", padding="5")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.frame_label = ttk.Label(info_frame, text="帧: - / -")
        self.frame_label.grid(row=0, column=0, sticky=tk.W)
        
        self.type_label = ttk.Label(info_frame, text="类型: -")
        self.type_label.grid(row=1, column=0, sticky=tk.W)
        
        # Debug信息状态显示（简化版，仅显示状态）
        debug_status_frame = ttk.LabelFrame(main_frame, text="Debug信息状态", padding="5")
        debug_status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.debug_info_label = ttk.Label(
            debug_status_frame, 
            text="debug.txt: 无\nmatch.json: 无",
            font=("Arial", 9),
            foreground="gray"
        )
        self.debug_info_label.grid(row=0, column=0, sticky=tk.W)
        
        # 悬浮信息显示（暂时移除，为Debug面板让出空间）
        # hover_frame = ttk.LabelFrame(main_frame, text="点云悬浮信息", padding="5")
        # hover_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 初始化悬浮信息标签（虽然不显示，但保留以避免错误）
        self.hover_info_label = None
        self.point_coord_label = None
        
        # 设置悬浮回调
        self.visualizer.on_hover = self.on_cloud_hover
        self.visualizer.on_point_hover = self.on_point_hover
        
        # 控制按钮框架
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="5")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 上一帧按钮
        prev_button = ttk.Button(control_frame, text="上一帧 (←)", command=self.previous_frame)
        prev_button.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 下一帧按钮
        next_button = ttk.Button(control_frame, text="下一帧 (→)", command=self.next_frame)
        next_button.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 重置视图按钮
        reset_button = ttk.Button(control_frame, text="重置视图", command=self.reset_view)
        reset_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 点云显示/隐藏控制框架
        visibility_frame = ttk.LabelFrame(control_frame, text="点云显示控制", padding="5")
        visibility_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Ground点云显示/隐藏按钮
        self.ground_button = ttk.Button(
            visibility_frame, 
            text="隐藏Ground点云", 
            command=lambda: self.toggle_point_cloud_visibility('ground')
        )
        self.ground_button.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        
        # Plane点云显示/隐藏按钮
        self.plane_button = ttk.Button(
            visibility_frame, 
            text="隐藏Plane点云", 
            command=lambda: self.toggle_point_cloud_visibility('plane')
        )
        self.plane_button.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        
        # Dense Cloud点云显示/隐藏按钮
        self.dense_cloud_button = ttk.Button(
            visibility_frame, 
            text="隐藏Dense Cloud点云", 
            command=lambda: self.toggle_point_cloud_visibility('dense_cloud')
        )
        self.dense_cloud_button.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        
        # 变换点云控制框架
        transform_frame = ttk.LabelFrame(control_frame, text="变换点云控制", padding="5")
        transform_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 绑定偏移值变化事件，自动重新加载当前帧
        def on_offset_change(*args):
            """当偏移值改变时，自动重新加载当前帧"""
            if self.visualizer.vis is not None and self.available_frames:
                if self.current_frame_index < len(self.available_frames):
                    frame_id = self.available_frames[self.current_frame_index]
                    # 重新加载当前帧（会使用新的偏移量）
                    self.load_frame(frame_id)
        
        # X轴偏移
        x_offset_frame = ttk.Frame(transform_frame)
        x_offset_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Label(x_offset_frame, text="X轴偏移:").pack(side=tk.LEFT, padx=5)
        self.x_offset_var = tk.DoubleVar(value=0.0)
        x_offset_spinbox = tk.Spinbox(
            x_offset_frame,
            from_=-1000.0,
            to=1000.0,
            increment=0.1,
            textvariable=self.x_offset_var,
            width=10,
            format="%.1f"
        )
        x_offset_spinbox.pack(side=tk.LEFT, padx=5)
        # 绑定鼠标滚轮事件（支持鼠标悬停时滚动）
        def bind_wheel_events(widget, var):
            """为控件绑定滚轮事件"""
            widget.bind("<MouseWheel>", lambda e: self._on_spinbox_wheel(e, var, 0.1))
            widget.bind("<Button-4>", lambda e: self._on_spinbox_wheel_linux(e, var, 0.1))
            widget.bind("<Button-5>", lambda e: self._on_spinbox_wheel_linux(e, var, 0.1))
            # 当鼠标进入控件时，绑定滚轮事件到父窗口（这样即使没有焦点也能滚动）
            def on_enter(e):
                widget.focus_set()
            def on_leave(e):
                pass
            widget.bind("<Enter>", on_enter)
        
        bind_wheel_events(x_offset_spinbox, self.x_offset_var)
        self.x_offset_var.trace_add('write', on_offset_change)
        
        # Y轴偏移
        y_offset_frame = ttk.Frame(transform_frame)
        y_offset_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Label(y_offset_frame, text="Y轴偏移:").pack(side=tk.LEFT, padx=5)
        self.y_offset_var = tk.DoubleVar(value=0.0)
        y_offset_spinbox = tk.Spinbox(
            y_offset_frame,
            from_=-1000.0,
            to=1000.0,
            increment=0.1,
            textvariable=self.y_offset_var,
            width=10,
            format="%.1f"
        )
        y_offset_spinbox.pack(side=tk.LEFT, padx=5)
        bind_wheel_events(y_offset_spinbox, self.y_offset_var)
        self.y_offset_var.trace_add('write', on_offset_change)
        
        # Z轴偏移
        z_offset_frame = ttk.Frame(transform_frame)
        z_offset_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))
        ttk.Label(z_offset_frame, text="Z轴偏移:").pack(side=tk.LEFT, padx=5)
        self.z_offset_var = tk.DoubleVar(value=10.0)
        z_offset_spinbox = tk.Spinbox(
            z_offset_frame,
            from_=-1000.0,
            to=1000.0,
            increment=0.1,
            textvariable=self.z_offset_var,
            width=10,
            format="%.1f"
        )
        z_offset_spinbox.pack(side=tk.LEFT, padx=5)
        bind_wheel_events(z_offset_spinbox, self.z_offset_var)
        self.z_offset_var.trace_add('write', on_offset_change)
        
        # 配置列权重
        transform_frame.columnconfigure(0, weight=1)
        
        # 退出按钮
        exit_button = ttk.Button(control_frame, text="退出", command=self.on_closing)
        exit_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 右侧Debug信息面板
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # 创建Notebook（标签页）用于显示Debug和Match信息
        self.debug_notebook = ttk.Notebook(right_panel)
        self.debug_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Debug信息标签页
        self.debug_info_frame = ttk.Frame(self.debug_notebook, padding="10")
        self.debug_notebook.add(self.debug_info_frame, text="Debug信息")
        self.debug_info_frame.columnconfigure(0, weight=1)
        self.debug_info_frame.rowconfigure(0, weight=1)
        
        # Debug信息文本框（将在_update_debug_panel中创建）
        self.debug_scrollable_frame = self.debug_info_frame  # 为了兼容性，保持引用
        
        # Match信息标签页
        self.match_frame = ttk.Frame(self.debug_notebook, padding="10")
        self.debug_notebook.add(self.match_frame, text="Match信息")
        self.match_frame.columnconfigure(0, weight=1)
        self.match_frame.rowconfigure(0, weight=1)
        
        # 配置列权重
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        visibility_frame.columnconfigure(0, weight=1)
        visibility_frame.columnconfigure(1, weight=1)
        debug_status_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 初始化按钮状态
        self.update_visibility_buttons()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def update_info_labels(self):
        """更新信息标签"""
        if self.frame_label and self.type_label:
            frame_text = f"帧: {self.current_frame_index + 1} / {len(self.available_frames)}"
            self.frame_label.config(text=frame_text)
            self.type_label.config(text="类型: map")
        
        # 更新debug信息显示
        self.update_debug_info_display()
    
    def next_frame(self):
        """切换到下一帧"""
        if not self.available_frames:
            return
        
        self.current_frame_index = (self.current_frame_index + 1) % len(self.available_frames)
        frame_id = self.available_frames[self.current_frame_index]
        self.load_frame(frame_id)
        self.update_info_labels()
    
    def previous_frame(self):
        """切换到上一帧"""
        if not self.available_frames:
            return
        
        self.current_frame_index = (self.current_frame_index - 1) % len(self.available_frames)
        frame_id = self.available_frames[self.current_frame_index]
        self.load_frame(frame_id)
        self.update_info_labels()
    
    def reset_view(self):
        """重置视图"""
        # 如果窗口关闭，先重新创建
        if self.visualizer.vis is None:
            if self.available_frames:
                frame_id = self.available_frames[self.current_frame_index]
                self.load_frame(frame_id)
            else:
                return
        
        if self.visualizer.vis is not None:
            try:
                self.visualizer.vis.reset_view_point(True)
                self.visualizer.vis.poll_events()
                self.visualizer.vis.update_renderer()
            except Exception as e:
                print(f"重置视图时出错: {e}")
                # 如果出错，尝试重新创建窗口
                if self.available_frames:
                    frame_id = self.available_frames[self.current_frame_index]
                    self.load_frame(frame_id)
    
    def on_closing(self):
        """窗口关闭事件"""
        self.running = False
        if self.visualizer is not None:
            self.visualizer.running = False
            self.visualizer.destroy()
        if self.root:
            self.root.quit()
            self.root.destroy()
    
    def load_frame(self, frame_id: int):
        """加载指定帧"""
        if frame_id not in self.available_frames:
            print(f"帧 {frame_id} 不存在")
            return
        
        # 检查窗口是否关闭，如果关闭则重新创建
        if self.visualizer.vis is not None:
            try:
                # 尝试poll_events，如果窗口关闭会返回False
                if not self.visualizer.vis.poll_events():
                    # 窗口已关闭，需要重新创建
                    print("检测到窗口已关闭，正在重新打开...")
                    self.visualizer.vis = None
                    self.visualizer.geometries.clear()
                    # 重新启动更新循环
                    if not self.running:
                        self.running = True
                        self.update_visualizer()
            except:
                # 窗口可能已经销毁，重新创建
                print("检测到窗口异常，正在重新打开...")
                self.visualizer.vis = None
                self.visualizer.geometries.clear()
                if not self.running:
                    self.running = True
                    self.update_visualizer()
        
        # 记录窗口是否是新创建的
        was_window_new = self.visualizer.vis is None
        
        # 从输入框获取偏移值
        x_offset = self.x_offset_var.get()
        y_offset = self.y_offset_var.get()
        z_offset = self.z_offset_var.get()
        
        # 加载帧（传递偏移量参数，内部会处理变换点云的加载和显示）
        self.visualizer.load_and_display_frame(
            frame_id, 
            Config.FRAME_TYPE_FRAME,
            x_offset=x_offset,
            y_offset=y_offset,
            z_offset=z_offset
        )
        
        # 更新当前帧索引
        if frame_id in self.available_frames:
            self.current_frame_index = self.available_frames.index(frame_id)
        
        # 如果是新创建的窗口，自动重置视图以显示点云
        if was_window_new and self.visualizer.vis is not None:
            try:
                self.visualizer.vis.reset_view_point(True)
                self.visualizer.vis.poll_events()
                self.visualizer.vis.update_renderer()
            except Exception as e:
                print(f"自动重置视图时出错: {e}")
        
        # 调用回调函数
        if self.on_frame_changed:
            self.on_frame_changed(frame_id, Config.FRAME_TYPE_FRAME)
        # 更新debug信息显示
        self.update_debug_info_display()
        
        # 更新可见性按钮状态
        self.update_visibility_buttons()
        
        print(f"已加载帧 {frame_id} (frame类型)")
    
    def update_visualizer(self):
        """定期更新可视化窗口（在主线程中调用）"""
        if not self.running or self.root is None:
            return
            
        if self.visualizer.vis is not None:
            try:
                # 处理Open3D窗口事件并更新渲染
                # poll_events()返回False时表示窗口已关闭
                if not self.visualizer.vis.poll_events():
                    # 窗口已关闭，但不停止更新循环
                    # 这样当用户切换帧时可以重新打开窗口
                    self.visualizer.vis = None
                    self.visualizer.geometries.clear()
                    print("可视化窗口已关闭，切换帧时会自动重新打开")
                else:
                    # 检查鼠标悬浮（使用Open3D的GUI系统）
                    self._check_mouse_hover()
                    self.visualizer.vis.update_renderer()
            except Exception as e:
                # 如果出现错误，重置窗口状态但不停止更新
                print(f"更新可视化窗口时出错: {e}")
                self.visualizer.vis = None
                self.visualizer.geometries.clear()
        
        # 确保控制面板始终在Open3D窗口之上
        try:
            if self.root and self.root.winfo_exists():
                self.root.attributes('-topmost', True)
                self.root.lift()
        except:
            pass
        
        # 每16ms更新一次（约60fps）
        if self.running:
            self.root.after(16, self.update_visualizer)
    
    def _check_mouse_hover(self):
        """检查鼠标是否悬浮在点云上"""
        if self.visualizer.vis is None:
            return
        
        try:
            # 由于Open3D的限制，直接获取鼠标位置比较困难
            # 我们使用一个简化的方法：通过Open3D的GUI系统
            # 这里暂时跳过，实际检测需要GUI系统支持
            
            # 注意：Open3D的Visualizer类不直接提供鼠标位置
            # 如果需要实现鼠标悬浮检测，需要使用VisualizerWithGUI
            # 或者使用其他方法（如键盘快捷键选择点云）
            pass
        except Exception as e:
            # 忽略错误，避免影响渲染
            pass
    
    def run(self, start_frame_id: Optional[int] = None):
        """
        运行GUI
        
        Args:
            start_frame_id: 起始帧ID，如果为None则使用第一帧
        """
        if not self.available_frames:
            print("错误: 没有找到可用的数据帧")
            return
        
        # 确定起始帧
        if start_frame_id is None:
            start_frame_id = self.available_frames[0]
        elif start_frame_id not in self.available_frames:
            print(f"警告: 帧 {start_frame_id} 不存在，使用第一帧")
            start_frame_id = self.available_frames[0]
        
        # 创建控制面板（必须在创建Open3D窗口之前）
        self.create_control_panel()
        self.update_info_labels()
        
        # 加载起始帧（这会创建Open3D窗口）
        self.load_frame(start_frame_id)
        
        # 设置悬浮回调
        self.visualizer.on_hover = self.on_cloud_hover
        
        # 启动GUI更新循环（在主线程中）
        self.running = True
        self.update_visualizer()
        
        # 运行tkinter主循环
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        finally:
            self.running = False
            self.visualizer.destroy()
    
    def get_current_frame_info(self) -> dict:
        """获取当前帧信息"""
        if self.available_frames and self.current_frame_index < len(self.available_frames):
            frame_id = self.available_frames[self.current_frame_index]
            return self.visualizer.get_frame_info(frame_id)
        return {}
    
    def update_debug_info_display(self):
        """更新debug信息显示"""
        if not self.debug_info_label or not self.available_frames:
            return
        
        if self.current_frame_index >= len(self.available_frames):
            return
        
        frame_id = self.available_frames[self.current_frame_index]
        
        # 检查debug.txt和match.json是否存在（这些文件在帧数据目录下，不在frame/map子目录）
        frame_data_path = Config.get_data_frame_path(frame_id)  # 返回 data/{frame_id}/
        debug_path = frame_data_path / "debug.txt"
        match_path = frame_data_path / "match.json"
        
        debug_exists = debug_path.exists()
        match_exists = match_path.exists()
        
        # 更新状态标签文本
        debug_status = "有" if debug_exists else "无"
        match_status = "有" if match_exists else "无"
        
        status_color = "black" if (debug_exists or match_exists) else "gray"
        
        self.debug_info_label.config(
            text=f"debug.txt: {debug_status}\nmatch.json: {match_status}",
            foreground=status_color
        )
        
        # 更新右侧Debug信息面板
        self._update_debug_panel(frame_id)
    
    def _update_debug_panel(self, frame_id: int):
        """更新右侧Debug信息面板"""
        # 清除现有内容
        for widget in self.debug_info_frame.winfo_children():
            widget.destroy()
        
        for widget in self.match_frame.winfo_children():
            widget.destroy()
        
        # 清空匹配关系复选框存储
        self.match_checkboxes.clear()
        
        # 直接读取debug.txt文件内容
        debug_path = Config.get_data_frame_path(frame_id) / "debug.txt"
        match_info = self.visualizer.data_loader.load_match_info(frame_id, use_dynamic_class=False)
        
        # 更新Debug信息标签页 - 直接显示原始文件内容
        if debug_path.exists():
            try:
                with open(debug_path, 'r', encoding='utf-8') as f:
                    debug_content = f.read()
                
                # 创建文本框显示原始内容
                debug_text = tk.Text(
                    self.debug_info_frame,
                    wrap=tk.NONE,  # 不自动换行，保持原始格式
                    font=("Courier", 10),
                    bg="white",
                    fg="black"
                )
                debug_text.insert(tk.END, debug_content)
                debug_text.config(state=tk.DISABLED)  # 设置为只读
                
                # 添加垂直滚动条
                debug_vscrollbar = ttk.Scrollbar(
                    self.debug_info_frame,
                    orient=tk.VERTICAL,
                    command=debug_text.yview
                )
                debug_text.configure(yscrollcommand=debug_vscrollbar.set)
                
                # 添加水平滚动条
                debug_hscrollbar = ttk.Scrollbar(
                    self.debug_info_frame,
                    orient=tk.HORIZONTAL,
                    command=debug_text.xview
                )
                debug_text.configure(xscrollcommand=debug_hscrollbar.set)
                
                # 布局
                debug_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                debug_vscrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
                debug_hscrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
                
                # 配置网格权重
                self.debug_info_frame.columnconfigure(0, weight=1)
                self.debug_info_frame.rowconfigure(0, weight=1)
            except Exception as e:
                ttk.Label(
                    self.debug_info_frame,
                    text=f"读取debug.txt文件失败: {e}",
                    font=("Arial", 10),
                    foreground="red"
                ).pack(pady=20)
        else:
            ttk.Label(
                self.debug_info_frame,
                text="debug.txt 文件不存在",
                font=("Arial", 10)
            ).pack(pady=20)
        
        # 更新Match信息标签页
        if match_info:
            self._format_match_info(self.match_frame, match_info)
        else:
            ttk.Label(self.match_frame, text="match.json 文件不存在或无法加载", 
                     font=("Arial", 10)).pack(pady=20)
    
    def _format_debug_info(self, parent, debug_info):
        """格式化显示debug信息"""
        import json
        import numpy as np
        
        # 标题
        title_label = ttk.Label(parent, text="优化信息", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 变换矩阵信息
        if "T_init_w_b" in debug_info and "T_opt_w_b" in debug_info:
            # 初始变换
            t_init = debug_info["T_init_w_b"]
            t_opt = debug_info["T_opt_w_b"]
            
            # 创建变换矩阵显示框架
            transform_frame = ttk.LabelFrame(parent, text="变换矩阵", padding="10")
            transform_frame.pack(fill=tk.X, pady=5)
            
            # 初始变换
            init_frame = ttk.LabelFrame(transform_frame, text="初始变换 (T_init_w_b)", padding="5")
            init_frame.pack(fill=tk.X, pady=5)
            
            q_init = t_init.get("q", {})
            t_init_vec = t_init.get("t", {})
            
            ttk.Label(init_frame, text="四元数 (w, x, y, z):", font=("Arial", 9, "bold")).pack(anchor=tk.W)
            ttk.Label(init_frame, 
                     text=f"({q_init.get('w', 0):.8f}, {q_init.get('x', 0):.8f}, "
                          f"{q_init.get('y', 0):.8f}, {q_init.get('z', 0):.8f})",
                     font=("Courier", 9)).pack(anchor=tk.W, padx=20)
            
            ttk.Label(init_frame, text="平移 (a, b, c):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(init_frame, 
                     text=f"({t_init_vec.get('a', 0):.8f}, {t_init_vec.get('b', 0):.8f}, "
                          f"{t_init_vec.get('c', 0):.8f})",
                     font=("Courier", 9)).pack(anchor=tk.W, padx=20)
            
            # 优化后变换
            opt_frame = ttk.LabelFrame(transform_frame, text="优化后变换 (T_opt_w_b)", padding="5")
            opt_frame.pack(fill=tk.X, pady=5)
            
            q_opt = t_opt.get("q", {})
            t_opt_vec = t_opt.get("t", {})
            
            ttk.Label(opt_frame, text="四元数 (w, x, y, z):", font=("Arial", 9, "bold")).pack(anchor=tk.W)
            ttk.Label(opt_frame, 
                     text=f"({q_opt.get('w', 0):.8f}, {q_opt.get('x', 0):.8f}, "
                          f"{q_opt.get('y', 0):.8f}, {q_opt.get('z', 0):.8f})",
                     font=("Courier", 9)).pack(anchor=tk.W, padx=20)
            
            ttk.Label(opt_frame, text="平移 (a, b, c):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(opt_frame, 
                     text=f"({t_opt_vec.get('a', 0):.8f}, {t_opt_vec.get('b', 0):.8f}, "
                          f"{t_opt_vec.get('c', 0):.8f})",
                     font=("Courier", 9)).pack(anchor=tk.W, padx=20)
            
            # 计算差异
            diff_frame = ttk.LabelFrame(transform_frame, text="优化变化量", padding="5")
            diff_frame.pack(fill=tk.X, pady=5)
            
            q_diff_w = q_opt.get('w', 0) - q_init.get('w', 0)
            q_diff_x = q_opt.get('x', 0) - q_init.get('x', 0)
            q_diff_y = q_opt.get('y', 0) - q_init.get('y', 0)
            q_diff_z = q_opt.get('z', 0) - q_init.get('z', 0)
            
            t_diff_a = t_opt_vec.get('a', 0) - t_init_vec.get('a', 0)
            t_diff_b = t_opt_vec.get('b', 0) - t_init_vec.get('b', 0)
            t_diff_c = t_opt_vec.get('c', 0) - t_init_vec.get('c', 0)
            
            ttk.Label(diff_frame, text="四元数变化:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
            ttk.Label(diff_frame, 
                     text=f"({q_diff_w:+.8e}, {q_diff_x:+.8e}, {q_diff_y:+.8e}, {q_diff_z:+.8e})",
                     font=("Courier", 9), foreground="blue").pack(anchor=tk.W, padx=20)
            
            ttk.Label(diff_frame, text="平移变化:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(diff_frame, 
                     text=f"({t_diff_a:+.8e}, {t_diff_b:+.8e}, {t_diff_c:+.8e})",
                     font=("Courier", 9), foreground="blue").pack(anchor=tk.W, padx=20)
        
        # 迭代信息
        if "iter_infos" in debug_info and len(debug_info["iter_infos"]) > 0:
            iter_frame = ttk.LabelFrame(parent, text="迭代过程", padding="10")
            iter_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # 创建表格显示迭代信息
            tree_frame = ttk.Frame(iter_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建Treeview表格
            tree = ttk.Treeview(tree_frame, columns=("iter", "cost_a_before", "cost_b_before", "cost_c_before",
                                                      "cost_a_after", "cost_b_after", "cost_c_after",
                                                      "improvement_a", "improvement_b", "improvement_c"),
                               show="headings", height=15)
            
            # 设置列标题
            tree.heading("iter", text="迭代")
            tree.heading("cost_a_before", text="成本A(前)")
            tree.heading("cost_b_before", text="成本B(前)")
            tree.heading("cost_c_before", text="成本C(前)")
            tree.heading("cost_a_after", text="成本A(后)")
            tree.heading("cost_b_after", text="成本B(后)")
            tree.heading("cost_c_after", text="成本C(后)")
            tree.heading("improvement_a", text="改进A")
            tree.heading("improvement_b", text="改进B")
            tree.heading("improvement_c", text="改进C")
            
            # 设置列宽
            tree.column("iter", width=50)
            for col in ["cost_a_before", "cost_b_before", "cost_c_before",
                       "cost_a_after", "cost_b_after", "cost_c_after",
                       "improvement_a", "improvement_b", "improvement_c"]:
                tree.column(col, width=90)
            
            # 添加数据
            for idx, iter_info in enumerate(debug_info["iter_infos"]):
                cost_before = iter_info.get("axis_cost_before", {})
                cost_after = iter_info.get("axis_cost_after", {})
                
                cost_a_before = cost_before.get("a", 0)
                cost_b_before = cost_before.get("b", 0)
                cost_c_before = cost_before.get("c", 0)
                
                cost_a_after = cost_after.get("a", 0)
                cost_b_after = cost_after.get("b", 0)
                cost_c_after = cost_after.get("c", 0)
                
                improvement_a = cost_a_before - cost_a_after
                improvement_b = cost_b_before - cost_b_after
                improvement_c = cost_c_before - cost_c_after
                
                tree.insert("", tk.END, values=(
                    idx + 1,
                    f"{cost_a_before:.2e}",
                    f"{cost_b_before:.2e}",
                    f"{cost_c_before:.2e}",
                    f"{cost_a_after:.2e}",
                    f"{cost_b_after:.2e}",
                    f"{cost_c_after:.2e}",
                    f"{improvement_a:+.2e}",
                    f"{improvement_b:+.2e}",
                    f"{improvement_c:+.2e}"
                ))
            
            # 添加滚动条
            tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=tree_scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 统计信息
            stats_label = ttk.Label(iter_frame, 
                                   text=f"总迭代次数: {len(debug_info['iter_infos'])}",
                                   font=("Arial", 9))
            stats_label.pack(pady=5)
        
        # 原始JSON（可折叠）
        json_frame = ttk.LabelFrame(parent, text="原始JSON数据", padding="5")
        json_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        json_text = tk.Text(json_frame, wrap=tk.WORD, font=("Courier", 8), height=12)
        json_scrollbar = ttk.Scrollbar(json_frame, orient=tk.VERTICAL, command=json_text.yview)
        json_text.configure(yscrollcommand=json_scrollbar.set)
        
        json_text.insert(tk.END, json.dumps(debug_info, indent=2, ensure_ascii=False))
        json_text.config(state=tk.DISABLED)
        
        json_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        json_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _format_match_info(self, parent, match_info):
        """格式化显示plane_match_infos匹配信息，每个匹配关系可以选中/取消选中"""
        import json
        
        # 创建滚动框架
        match_canvas = tk.Canvas(parent)
        match_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=match_canvas.yview)
        match_scrollable_frame = ttk.Frame(match_canvas)
        
        match_scrollable_frame.bind(
            "<Configure>",
            lambda e: match_canvas.configure(scrollregion=match_canvas.bbox("all"))
        )
        
        match_canvas.create_window((0, 0), window=match_scrollable_frame, anchor="nw")
        match_canvas.configure(yscrollcommand=match_scrollbar.set)
        
        match_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        match_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 标题
        title_label = ttk.Label(match_scrollable_frame, text="点云匹配关系", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 提取plane_match_infos
        plane_match_infos = []
        if match_info:
            if hasattr(match_info, 'plane_match_infos'):
                plane_match_infos = match_info.plane_match_infos
            elif isinstance(match_info, dict) and 'plane_match_infos' in match_info:
                plane_match_infos = match_info['plane_match_infos']
        
        if not plane_match_infos:
            ttk.Label(match_scrollable_frame, text="未找到plane_match_infos数据", 
                     font=("Arial", 10)).pack(pady=20)
            return
        
        # 统计信息
        stats_frame = ttk.LabelFrame(match_scrollable_frame, text="统计信息", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        
        total_count = len(plane_match_infos)
        ttk.Label(stats_frame, text=f"总匹配数: {total_count}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 匹配列表框架
        list_frame = ttk.LabelFrame(match_scrollable_frame, text="匹配关系列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 存储复选框变量，用于后续控制
        self.match_checkboxes = {}  # {match_index: (var, match_data)}
        
        # 为每个匹配关系创建复选框
        for idx, match in enumerate(plane_match_infos):
            # 提取匹配信息
            if hasattr(match, 'cur_id'):
                cur_id_obj = match.cur_id
                other_id_obj = match.other_id
                axis = match.axis if hasattr(match, 'axis') else None
            elif isinstance(match, dict):
                cur_id_obj = match.get('cur_id')
                other_id_obj = match.get('other_id')
                axis = match.get('axis')
            else:
                continue
            
            # 提取cur_id和other_id的类型和id
            cur_type = None
            cur_id = None
            other_type = None
            other_id = None
            
            if isinstance(cur_id_obj, dict):
                cur_type = cur_id_obj.get('a')  # 1=plane, 2=ground
                cur_id = cur_id_obj.get('b')
            elif hasattr(cur_id_obj, 'a'):
                cur_type = cur_id_obj.a
                cur_id = cur_id_obj.b
            
            if isinstance(other_id_obj, dict):
                other_type = other_id_obj.get('a')
                other_id = other_id_obj.get('b')
            elif hasattr(other_id_obj, 'a'):
                other_type = other_id_obj.a
                other_id = other_id_obj.b
            
            if cur_type is None or cur_id is None or other_type is None or other_id is None:
                continue
            
            # 创建匹配项框架
            match_item_frame = ttk.Frame(list_frame)
            match_item_frame.pack(fill=tk.X, pady=2, padx=5)
            
            # 创建复选框变量（默认选中）
            var = tk.BooleanVar(value=True)
            self.match_checkboxes[idx] = (var, {
                'cur_type': cur_type,
                'cur_id': cur_id,
                'other_type': other_type,
                'other_id': other_id,
                'axis': axis
            })
            
            # 类型名称
            cur_type_name = "plane" if cur_type == 1 else "ground" if cur_type == 2 else "unknown"
            other_type_name = "plane" if other_type == 1 else "ground" if other_type == 2 else "unknown"
            
            # 创建复选框
            checkbox = ttk.Checkbutton(
                match_item_frame,
                text=f"轴{axis}: Frame {cur_type_name}_{cur_id} <-> Map {other_type_name}_{other_id}",
                variable=var,
                command=lambda idx=idx, var=var: self._on_match_checkbox_toggle(idx, var)
            )
            checkbox.pack(side=tk.LEFT, padx=5)
        
        # 全选/全不选按钮
        button_frame = ttk.Frame(match_scrollable_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        def select_all():
            for idx, (var, _) in self.match_checkboxes.items():
                var.set(True)
                self._on_match_checkbox_toggle(idx, var)
        
        def deselect_all():
            for idx, (var, _) in self.match_checkboxes.items():
                var.set(False)
                self._on_match_checkbox_toggle(idx, var)
        
        ttk.Button(button_frame, text="全选", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="全不选", command=deselect_all).pack(side=tk.LEFT, padx=5)
    
    def _on_match_checkbox_toggle(self, match_index: int, var: tk.BooleanVar):
        """
        当匹配关系复选框切换时调用，显示/隐藏对应的点云
        
        Args:
            match_index: 匹配关系的索引
            var: 复选框变量
        """
        if match_index not in self.match_checkboxes:
            return
        
        _, match_data = self.match_checkboxes[match_index]
        is_selected = var.get()
        
        cur_type = match_data['cur_type']
        cur_id = match_data['cur_id']
        other_type = match_data['other_type']
        other_id = match_data['other_id']
        
        # 确定类型名称
        cur_type_name = "plane" if cur_type == 1 else "ground" if cur_type == 2 else None
        other_type_name = "plane" if other_type == 1 else "ground" if other_type == 2 else None
        
        if cur_type_name is None or other_type_name is None:
            return
        
        # Frame点云名称: {type}_{id}
        frame_cloud_name = f"{cur_type_name}_{cur_id}"
        
        # Map点云名称: map_{type}_{id}
        map_cloud_name = f"map_{other_type_name}_{other_id}"
        
        # 获取当前帧ID（用于查找变换点云）
        if not self.available_frames or self.current_frame_index >= len(self.available_frames):
            return
        frame_id = self.available_frames[self.current_frame_index]
        
        # 变换点云名称: transformed_cloud_{frame_id}_{transform_name}_{type}_{id}
        # 需要检查所有可能的变换名称（T_opt_w_b, T_init_w_b等）
        transform_names = ['T_opt_w_b', 'T_init_w_b']
        
        if is_selected:
            # 显示点云
            if frame_cloud_name in self.visualizer.hidden_geometries:
                self.visualizer.show_geometry(frame_cloud_name)
            if map_cloud_name in self.visualizer.hidden_geometries:
                self.visualizer.show_geometry(map_cloud_name)
            
            # 显示变换点云
            for transform_name in transform_names:
                transformed_frame_name = f"transformed_cloud_{frame_id}_{transform_name}_{cur_type_name}_{cur_id}"
                if transformed_frame_name in self.visualizer.hidden_geometries:
                    self.visualizer.show_geometry(transformed_frame_name)
        else:
            # 隐藏点云
            if frame_cloud_name in self.visualizer.geometries:
                self.visualizer.hide_geometry(frame_cloud_name)
            if map_cloud_name in self.visualizer.geometries:
                self.visualizer.hide_geometry(map_cloud_name)
            
            # 隐藏变换点云
            for transform_name in transform_names:
                transformed_frame_name = f"transformed_cloud_{frame_id}_{transform_name}_{cur_type_name}_{cur_id}"
                if transformed_frame_name in self.visualizer.geometries:
                    self.visualizer.hide_geometry(transformed_frame_name)
        
        # 更新视图
        self.visualizer.update_view()
    
    def on_cloud_hover(self, cloud_name: Optional[str], cloud_info: Optional[dict]):
        """
        点云悬浮回调函数
        
        Args:
            cloud_name: 悬浮的点云名称，如果为None则表示没有悬浮在任何点云上
            cloud_info: 点云信息字典
        """
        if self.hover_info_label is None:
            return
        
        if cloud_name is None or cloud_info is None:
            # 没有悬浮在任何点云上
            self.hover_info_label.config(
                text="将鼠标移动到点云上查看信息",
                foreground="gray"
            )
        else:
            # 显示点云信息
            info_text = f"点云: {cloud_name}\n"
            info_text += f"类型: {cloud_info.get('type', 'unknown')}\n"
            info_text += f"点数: {cloud_info.get('point_count', 0)}\n"
            
            if cloud_info.get('has_normals'):
                info_text += "有法向量: 是\n"
            if cloud_info.get('has_colors'):
                info_text += "有颜色: 是\n"
            
            # 如果有元数据，显示更多信息
            if 'metadata' in cloud_info and cloud_info['metadata'] is not None:
                metadata = cloud_info['metadata']
                if hasattr(metadata, 'normal'):
                    normal = metadata.normal
                    info_text += f"法向量: ({normal.x:.3f}, {normal.y:.3f}, {normal.z:.3f})\n"
            
            self.hover_info_label.config(
                text=info_text,
                foreground="black"
            )
    
    def on_point_hover(self, point_info: Optional[dict]):
        """
        点悬浮回调函数，显示点的三维坐标
        
        Args:
            point_info: 点信息字典，包含点的坐标等信息，如果为None则表示没有悬浮在任何点上
        """
        if point_info is None:
            # 没有悬浮在任何点上
            if self.point_coord_label:
                self.point_coord_label.config(
                    text="坐标: -",
                    foreground="gray"
                )
        else:
            # 显示点的三维坐标
            point = point_info.get('point', None)
            if point is not None:
                coord_text = f"坐标: ({point[0]:.4f}, {point[1]:.4f}, {point[2]:.4f})"
                self.point_coord_label.config(
                    text=coord_text,
                    foreground="blue"
                )
    
    def toggle_point_cloud_visibility(self, cloud_type: str):
        """
        切换指定类型点云的显示/隐藏状态（包括原始点云和变换点云）
        
        Args:
            cloud_type: 点云类型 ('ground', 'plane', 'dense_cloud')
        """
        if self.visualizer.vis is None:
            messagebox.showinfo("提示", "请先打开可视化窗口")
            return
        
        # 切换原始点云的显示状态
        is_visible = self.visualizer.toggle_point_cloud_type(cloud_type)
        
        # 同时切换对应的变换点云
        self._toggle_transformed_clouds(cloud_type, is_visible)
        
        # 更新按钮文本
        self.update_visibility_button(cloud_type, is_visible)
        
        # 更新视图
        self.visualizer.update_view()
    
    def _toggle_transformed_clouds(self, cloud_type: str, is_visible: bool):
        """
        切换对应类型变换点云的显示/隐藏状态
        
        Args:
            cloud_type: 点云类型 ('ground', 'plane', 'dense_cloud')
            is_visible: 是否可见（True表示显示，False表示隐藏）
        """
        if self.visualizer.vis is None:
            return
        
        # 获取当前帧ID
        if not self.available_frames or self.current_frame_index >= len(self.available_frames):
            return
        
        frame_id = self.available_frames[self.current_frame_index]
        transform_name = 'T_opt_w_b'
        
        # 构建变换点云名称前缀
        prefix = f"transformed_cloud_{frame_id}_{transform_name}_"
        
        # 查找所有匹配的变换点云（包括可见和隐藏的）
        transformed_names = []
        
        # 从可见的几何体中查找
        for name in list(self.visualizer.geometries.keys()):
            if name.startswith(prefix):
                # 提取文件名部分（例如：dense_cloud, ground_0, plane_1）
                file_stem = name[len(prefix):]
                
                # 检查是否匹配cloud_type
                if cloud_type == 'dense_cloud':
                    if file_stem == 'dense_cloud':
                        transformed_names.append(name)
                else:
                    # ground或plane类型
                    if file_stem.startswith(cloud_type + '_'):
                        transformed_names.append(name)
        
        # 从隐藏的几何体中查找
        for name in list(self.visualizer.hidden_geometries.keys()):
            if name.startswith(prefix):
                # 提取文件名部分
                file_stem = name[len(prefix):]
                
                # 检查是否匹配cloud_type
                if cloud_type == 'dense_cloud':
                    if file_stem == 'dense_cloud':
                        transformed_names.append(name)
                else:
                    # ground或plane类型
                    if file_stem.startswith(cloud_type + '_'):
                        transformed_names.append(name)
        
        # 切换变换点云的显示/隐藏状态
        for name in transformed_names:
            if is_visible:
                # 如果原始点云可见，显示变换点云
                if name in self.visualizer.hidden_geometries:
                    self.visualizer.show_geometry(name)
            else:
                # 如果原始点云隐藏，隐藏变换点云
                if name in self.visualizer.geometries:
                    self.visualizer.hide_geometry(name)
    
    def update_visibility_button(self, cloud_type: str, is_visible: bool):
        """更新指定类型点云的按钮文本"""
        button_text_map = {
            'ground': ('显示Ground点云', '隐藏Ground点云'),
            'plane': ('显示Plane点云', '隐藏Plane点云'),
            'dense_cloud': ('显示Dense Cloud点云', '隐藏Dense Cloud点云')
        }
        
        if cloud_type in button_text_map:
            show_text, hide_text = button_text_map[cloud_type]
            button = {
                'ground': self.ground_button,
                'plane': self.plane_button,
                'dense_cloud': self.dense_cloud_button
            }.get(cloud_type)
            
            if button:
                button.config(text=show_text if is_visible else hide_text)
    
    def update_visibility_buttons(self):
        """更新所有可见性按钮的状态"""
        if self.visualizer.vis is None:
            return
        
        # 检查每种类型的可见性并更新按钮
        for cloud_type in ['ground', 'plane', 'dense_cloud']:
            is_visible = self.visualizer.is_point_cloud_type_visible(cloud_type)
            self.update_visibility_button(cloud_type, is_visible)
    
    def _on_spinbox_wheel(self, event, var: tk.DoubleVar, increment: float):
        """
        处理Spinbox的鼠标滚轮事件（Windows/Mac）
        
        Args:
            event: 鼠标事件
            var: DoubleVar变量
            increment: 每次滚动的增量
        """
        # Windows/Mac: delta > 0 向上滚动，delta < 0 向下滚动
        delta = event.delta
        current_value = var.get()
        if delta > 0:
            new_value = current_value + increment
        else:
            new_value = current_value - increment
        var.set(new_value)
        return "break"  # 阻止事件继续传播
    
    def _on_spinbox_wheel_linux(self, event, var: tk.DoubleVar, increment: float):
        """
        处理Spinbox的鼠标滚轮事件（Linux）
        
        Args:
            event: 鼠标事件
            var: DoubleVar变量
            increment: 每次滚动的增量
        """
        # Linux: Button-4 向上滚动，Button-5 向下滚动
        current_value = var.get()
        if event.num == 4:
            new_value = current_value + increment
        elif event.num == 5:
            new_value = current_value - increment
        else:
            return
        var.set(new_value)
        return "break"  # 阻止事件继续传播
    
    def _auto_load_transform_point_cloud(self, frame_id: int):
        """
        自动加载变换点云（如果存在debug.txt）
        
        在切换帧时，如果存在debug.txt文件，会自动加载frame文件夹中的点云，
        应用位姿变换矩阵（T_opt_w_b）和偏移量，并叠加显示到坐标系中。
        
        默认会显示所有找到的变换点云：
        - dense_cloud点云（经过变换）
        - ground点云（经过变换，所有ground_*.ply文件）
        - plane点云（经过变换，所有plane_*.ply文件）
        
        Args:
            frame_id: 帧ID
        """
        if self.visualizer.vis is None:
            return
        
        # 检查debug.txt是否存在
        debug_info = self.visualizer.data_loader.load_debug_info(frame_id, use_dynamic_class=False)
        if debug_info is None:
            return
        
        # 检查是否有T_opt_w_b变换矩阵
        if 'T_opt_w_b' not in debug_info:
            return
        
        # 从输入框获取偏移值
        x_offset = self.x_offset_var.get()
        y_offset = self.y_offset_var.get()
        z_offset = self.z_offset_var.get()
        
        # 自动加载变换点云（使用T_opt_w_b）
        try:
            self.visualizer.load_and_transform_point_cloud(
                frame_id,
                transform_name='T_opt_w_b',
                x_offset=x_offset,
                y_offset=y_offset,
                z_offset=z_offset
            )
            print(f"已自动加载变换点云（帧 {frame_id}，使用 T_opt_w_b）")
        except Exception as e:
            print(f"自动加载变换点云时出错: {e}")

