def _convert_str_to_int(str):#定义将字符串转换为整型
    """
    TypeError will take care the case that str is #TypeError 将处理 str 为 None 的情况
    ValueError will take care the case that str is empty #ValueError 将处理 str 为空的情况
    """
    if not str:
        return None

    try:
        return int(str)
    except ValueError:
        return int(float(str))
    except TypeError:
        return None


def _convert_str_to_float(str):#定义将字符串转化为浮点型
    """
    TypeError will take care the case that str is None #TypeError 将处理 str 为 None 的情况
    ValueError will take care the case that str is empty #ValueError 将处理 str 为空的情况
    """
    if not str:
        return None

    try:
        return float(str)
    except (TypeError, ValueError): #（类型错误，值错误）
        return None