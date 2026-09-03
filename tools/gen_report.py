# -*- coding: utf-8 -*-
"""
gen_report.py —— 综合实践III《单目标跟踪系统》课程设计报告生成器（入口）
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能：按《综合实践III报告参考模板》排版规则，将 report_part1/part2 内容组装为 docx。
运行：python gen_report.py   （输出到 ../../02-文档/）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import docx_lib  # noqa
import report_part1 as p1  # noqa
import report_part2 as p2  # noqa

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
p1.ROOT = ROOT
p2.ROOT = ROOT

OUT_DIR = os.path.join(ROOT, "02-文档")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_FILE = os.path.join(OUT_DIR, "综合实践III课程设计报告-单目标跟踪系统.docx")


def main():
    doc = docx_lib.new_doc()

    p1.build_cover(doc)          # 封面
    p1.build_score(doc)          # 课程设计评分表
    p1.build_team(doc)           # 团队成员
    p1.build_abstract(doc)       # 摘要
    docx_lib.add_toc(doc)        # 目录（Word 中更新域）

    p1.build_ch1(doc)            # 1 系统目标与分析
    p1.build_ch2(doc)            # 2 项目管理
    p2.build_ch3(doc)            # 3 系统设计与实现
    p2.build_ch4(doc)            # 4 系统测试
    p2.build_ch5(doc)            # 5 系统总结
    p2.build_ch6(doc)            # 6 心得体会
    p2.build_refs(doc)           # 参考文献
    p2.build_appendix(doc)       # 附录A 目录结构

    doc.save(OUT_FILE)
    print("报告已生成:", OUT_FILE)
    print("大小:", os.path.getsize(OUT_FILE), "bytes")


if __name__ == "__main__":
    main()
