import os

import pandas as pd

# 资产类型对应表df
class_mapping = pd.read_excel(os.path.join("configs", "资产类型对应表.xlsx"))

# 头寸表项目筛选配置
toucun_config = {
    "实收资本": {"row": {"col": "科目代码", "val": "实收资本："}, "column": "市值"},
    "单位净值": {"row": {"col": "科目代码", "val": "产品单位净值："}, "column": "科目名称"},
    "净资产": {"row": {"col": "科目代码", "val": "产品资产净值："}, "column": "市值"},
    "总资产": {"row": {"col": "科目代码", "val": "资产类合计："}, "column": "市值"},
    "现金": {"row": {"col": "科目名称", "val": "银行存款"}, "column": "市值"}
}
