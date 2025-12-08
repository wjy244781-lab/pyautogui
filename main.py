"""
点云可视化工具主程序入口
"""
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.gui import PointCloudGUI


def main():
    """主函数"""
    # 创建GUI实例
    gui = PointCloudGUI()
    
    # 运行GUI（可以指定起始帧ID，例如: gui.run(start_frame_id=0)）
    gui.run()


if __name__ == "__main__":
    main()






