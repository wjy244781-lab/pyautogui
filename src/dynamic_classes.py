"""
动态类生成模块
根据JSON文件动态生成类，而不是使用预定义的类
使用Python的type()函数进行元编程
"""
import json
from typing import Dict, Any, Optional


def create_class_from_json(json_string: str, class_name: str = "DynamicObject"):
    """
    根据 JSON 字符串动态创建一个具有对应属性的类。
    注意：此方法不进行类型验证，所有属性都是简单赋值。
    
    Args:
        json_string: JSON字符串
        class_name: 类名称
        
    Returns:
        动态创建的类实例
    """
    data_dict = json.loads(json_string)
    return create_class_from_dict(data_dict, class_name)


def create_class_from_dict(data_dict: Dict[str, Any], class_name: str = "DynamicObject"):
    """
    根据字典动态创建一个具有对应属性的类
    
    Args:
        data_dict: 数据字典
        class_name: 类名称
        
    Returns:
        动态创建的类实例
    """
    # 1. 定义一个 __init__ 方法，自动接收并设置属性
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # 递归处理嵌套的字典，将其也转换为 DynamicObject
            if isinstance(value, dict):
                # 动态地将嵌套字典转换为一个新的 DynamicObject 实例
                nested_class_name = key.capitalize() + "Object"
                setattr(self, key, create_class_from_dict(value, nested_class_name))
            elif isinstance(value, list):
                # 处理列表，如果列表元素是字典，也转换为动态类
                processed_list = []
                for item in value:
                    if isinstance(item, dict):
                        item_class_name = key.capitalize() + "Item"
                        processed_list.append(create_class_from_dict(item, item_class_name))
                    else:
                        processed_list.append(item)
                setattr(self, key, processed_list)
            else:
                setattr(self, key, value)
    
    # 2. 定义 __repr__ 方法
    def __repr__(self):
        attrs = ', '.join(f"{k}={v}" for k, v in self.__dict__.items() if not k.startswith('_'))
        return f"<{class_name}({attrs})>"
    
    # 3. 定义 __str__ 方法
    def __str__(self):
        return self.__repr__()
    
    # 4. 定义 to_dict 方法，将对象转换回字典
    def to_dict(self):
        """将对象转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    # 5. 构造类的属性字典 (包含 __init__ 和 __repr__)
    attributes = {
        '__init__': __init__,
        '__repr__': __repr__,
        '__str__': __str__,
        'to_dict': to_dict,
    }
    
    # 6. 动态创建类
    DynamicClass = type(class_name, (object,), attributes)
    
    # 7. 创建该类的实例
    instance = DynamicClass(**data_dict)
    return instance


def load_json_to_dynamic_class(file_path: str, class_name: Optional[str] = None) -> Any:
    """
    从JSON文件加载数据并创建动态类实例
    
    Args:
        file_path: JSON文件路径
        class_name: 类名称，如果为None则从文件名生成
        
    Returns:
        动态创建的类实例
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data_dict = json.load(f)
    
    if class_name is None:
        # 从文件名生成类名
        from pathlib import Path
        file_name = Path(file_path).stem
        # 将文件名转换为类名：ground_0 -> Ground0Data
        parts = file_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts) + "Data"
    
    return create_class_from_dict(data_dict, class_name)

