import os

import numpy as np
import pandas as pd

from config import class_mapping, toucun_config

# 1. 根据维护的产品名称表格，筛选持仓表所需表格


def choose_my_products(my_product_codes, all_product_codes):
    """
    通过my_product_codes读取的表格，在all_product_codes文件夹内找到所有的文件名，
    如果没有找到或者找到多余1个，则报错并提示。

    Parameters
    ----------
    my_product_codes : str
        所有自己的产品名称表格对应路径

    all_product_codes : str
        所有表格所在的文件夹路径

    Returns
    -------
    my_product_paths : list of str
        根据my_product_codes筛选的文件路径列表
    """
    my_product_codes_sheet = pd.read_excel(my_product_codes)

    df = pd.DataFrame(os.listdir(all_product_codes), columns=["filename"])

    my_product_paths = []
    for my_product_code in my_product_codes_sheet["F16_产品代码"]:
        selected_items = df.loc[df["filename"].map(
            lambda x: x.startswith(my_product_code)), "filename"].tolist()
        if len(selected_items) == 1:
            my_product_paths.append(os.path.join(
                all_product_codes, selected_items[0]))
        elif len(selected_items) > 1:
            raise RuntimeError(
                f"产品选择数量错误！产品代码：{my_product_code} 找到{len(selected_items)}个匹配项：{selected_items}")
        else:
            raise RuntimeError(f"产品选择数量错误！产品代码：{my_product_code} 没有找到匹配项")
    return my_product_paths

# 2. 提取第一步选择表格的信息
# 2.1 整理为《持仓表》


def data_extraction(my_product_paths, skiprows=3, mapping=class_mapping, notna_cols=["单位成本", "科目名称"],
                    needed_cols=["科目名称", "资产类型", "数    量", "单位成本", "市价", "市值", "估值增值"]):
    """
    针对第一步选择的表格路径提取信息，整理为《持仓表》

    Parameters
    ----------
    my_product_paths : list of str
        需要处理的文件路径列表

    skiprows : int, default 3
        估值表格式，前多少行没用，目前默认3，如果不一样需要在data_extraction里面单独改

    mapping : pd.DataFrame
        资产类型对应表，通过资产的父节点名称找到资产类型。表格需要持续维护，看到没有对应内容就要补充

    notna_cols : list of str
        选择持仓信息的选择条件，目前是这两列非空，以后调整可能性不高

    needed_cols: list of str
        最终持仓表需要展示的列名，可能会需要调整，直接来改默认值吧

    Returns
    -------
    result : pd.DataFrame
        最终的《持仓表》df
    """
    result = []
    for p in my_product_paths:
        result.append(data_extraction_single(
            p, skiprows, mapping, notna_cols, needed_cols))
    result = pd.concat(result)
    result.reset_index(drop=True, inplace=True)
    return result


def data_extraction_single(path_to_df, skiprows, mapping, notna_cols, needed_cols):
    """
    针对第一步选择的表格路径提取信息，整理为《持仓表》。本函数根据一个表格路径进行提取

    Parameters
    ----------
    path_to_df : str
        需要处理的文件路径

    skiprows : int, default 3
        估值表格式，前多少行没用，目前一般为3，如果需要单独改，在data_extraction可能需要传入配置

    mapping : pd.DataFrame
        资产类型对应表，通过资产的父节点名称找到资产类型。表格需要持续维护，看到没有对应内容就要补充

    notna_cols : list of str
        选择持仓信息的选择条件，目前是这两列非空，以后调整可能性不高

    needed_cols: list of str
        最终持仓表需要展示的列名，可能会需要调整，直接来改默认值吧

    Returns
    -------
    result : pd.DataFrame
        最终的《持仓表》df
    """
    product_code = get_product_code_from_sheet_path(path_to_df)

    df = pd.read_excel(path_to_df, skiprows=skiprows)
    df = add_parent_name_and_class_tag(df, mapping)
    df = select_data_from_df(df, notna_cols, needed_cols)

    df.insert(0, "产品代码", product_code)

    return df


def get_product_code_from_sheet_path(p):
    """
    根据估值表路径得到估值表的产品代码，目前写死

    Parameters
    ----------
    p : str
        估值表完整路径

    Returns
    -------
    product_code : str
        产品代码
    """
    product_code = os.path.basename(p).split("（")[0].split("_")[-1]
    return product_code


def get_date_from_sheet_path(p):
    """
    根据估值表路径得到日期，目前写死

    Parameters
    ----------
    p : str
        估值表完整路径

    Returns
    -------
    date : str
        日期字段
    """
    date = os.path.basename(p)[-14:-4]
    return date


def add_parent_name_and_class_tag(df, mapping):
    """
    这里给标准资产估值表加上父节点名称以及对应资产类型

    Parameters
    ----------
    df : pd.DataFrame
        需要加标签的表格

    mapping : pd.DataFrame
        父节点对应类型表格，目前找父节点的逻辑是写死的

    Returns
    -------
    df : pd.DataFrame
        加完标签的表格
    """
    current_parent = ""
    dwcb = "单位成本"
    kmmc = "科目名称"

    df_nan = pd.isna(df)
    # 单位成本连续两个na，下一个不是na,且下一个科目名称notna的情况就是爸爸所在的行
    # 注意，资管计划的表格，有些不是na，是0，需要考虑应对
    for i in range(len(df)-2):
        if df_nan.loc[i, dwcb] == True and \
                df_nan.loc[i+1, dwcb] == True and \
                df_nan.loc[i+2, dwcb] == False and \
                df_nan.loc[i+2, kmmc] == False:
            current_parent = str(df.loc[i, kmmc])
        df.loc[i, "父节点名称"] = current_parent

    # merge不保险，还是做mapping
    mapping_dict = {}
    for i in range(len(mapping)):
        k, v = mapping.loc[i, ["父节点名称", "资产类型"]]
        mapping_dict[k] = v
    df["资产类型"] = df["父节点名称"].map(mapping_dict)
    return df


def select_data_from_df(df, notna_cols, needed_cols):
    """
    选择表格内容区域

    Parameters
    ----------
    notna_cols : list of str
        目前row层级的筛选标准，即这几列内容都不能为空

    needed_cols : list of str
        目前col层级的筛选标准，即最终许哟这几列

    Returns
    -------
    df : pd.DataFrame
        筛选完后的表格
    """
    for col in notna_cols:
        df = df.loc[df[col].notna()]
    return df[needed_cols]

# 2.2. 整理为《头寸表》


def generate_toucun(my_product_paths, skiprows=3, toucun_config=toucun_config):
    """
    在每张估值表里面挑字段，整理成《头寸表》

    Parameters
    ----------
    my_product_paths : list of str
        需要处理的文件路径列表

    skiprows : int
        估值表格式，前多少行没用，目前一般为3

    toucun_config : dict
        参考config.py，第一层Key是《头寸表》需要的内容列，对应value是在表中取值的配置

    Returns
    -------
    result : pd.DataFrame
        头寸表df
    """
    result = []
    for p in my_product_paths:
        product_code = get_product_code_from_sheet_path(p)
        df = pd.read_excel(p, skiprows=skiprows)

        row = [product_code]  # 一行(row)对应一张估值表
        for k in toucun_config:
            row.append(_get_single_roi(df, toucun_config[k]))
        result.append(row)
    result = pd.DataFrame(result, columns=["产品代码"]+list(toucun_config.keys()))
    return result


def _get_single_roi(df, criteria):
    """
    根据criteria字典，选择df对应字段内容。如果找到的字段数量不等于1会报错

    Parameters
    ----------
    df : pd.DataFrame
        用于选择的估值表

    criteria : dict
        选择条件，通过选择criteria["row"]["col"] == criteria["row"]["val"]的行，
        取criteria["column"]的值

    Returns
    -------
    val : ...
        对应位置的值
    """
    row_criteria = criteria["row"]
    column_name = criteria["column"]
    val = df.loc[df[row_criteria["col"]] ==
                 row_criteria["val"], column_name].tolist()
    if len(val) != 1:
        raise RuntimeError(f"根据{row_criteria}找到的{column_name}数量不为1，具体为：{val}")
    return val[0]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="自动生成《持仓表》和《头寸表》，如果输入目录中日期不止一个，会报错")
    parser.add_argument("--src", type=str, help="估值100表的母文件夹路径")
    parser.add_argument("--dest", type=str, help="持仓表和头寸表的保存路径")
    args = parser.parse_args()

    if not os.path.exists(args.dest):
        os.makedirs(args.dest)

    # 1. 拿到src文件夹中所有需要的估值表路径
    my_product_codes = os.path.join("configs", "产品选择表.xlsx")
    all_product_codes = args.src
    my_product_paths = choose_my_products(my_product_codes, all_product_codes)
    print(f"估值表筛选完成，根据《资产选择表》最终选出{len(my_product_paths)}张表用于处理")

    # 拿到并且检查估值表日期
    dates = np.unique([get_date_from_sheet_path(x) for x in my_product_paths])
    if len(dates) != 1:
        raise RuntimeError(f"日期提取有误，提取到了{dates}，请检查！")
    date = dates[0]

    # 保存持仓表
    df_ccb = data_extraction(my_product_paths)
    target = os.path.join(args.dest, f"持仓表_{date}.xlsx")
    df_ccb.to_excel(target, index=None, encoding="utf_8_sig")
    print(f"持仓表导出完成:{target}")

    # 保存头寸表
    df_tcb = generate_toucun(my_product_paths)
    target = os.path.join(args.dest, f"头寸表_{date}.xlsx")
    df_tcb.to_excel(target, index=None, encoding="utf_8_sig")
    print(f"头寸表导出完成:{target}")
