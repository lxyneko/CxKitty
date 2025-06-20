#!/bin/python3
import json
import sys
import time
from os import PathLike
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.traceback import install

import config
import dialog
from cxapi import (
    ChaoXingAPI,
    ChapterContainer,
    ClassSelector,
    ExamDto,
    PointDocumentDto,
    PointVideoDto,
    PointWorkDto,
)
from cxapi.exception import ChapterNotOpened, TaskPointError, ExamCompleted
from logger import Logger
from resolver import DocumetResolver, MediaPlayResolver, QuestionResolver
from utils import __version__, ck2dict, sessions_load

api = ChaoXingAPI()
console = Console(height=config.TUI_MAX_HEIGHT)
logger = Logger("Main")

install(console=console, show_locals=False)

layout = Layout()
lay_left = Layout(name="Left")
lay_right = Layout(name="Right", size=60)
lay_right_content = Layout(name="RightContent")
lay_session_notice = Layout(name="session_notice", size=6)
lay_right.update(lay_right_content)


def task_wait(tui_ctx: Any, wait_sec: int, text: str) -> None:
    """课间等待, 防止风控"""
    tui_ctx.unsplit()
    for i in range(wait_sec):
        tui_ctx.update(
            Panel(
                Align.center(
                    f"[green]{text}, 课间等待{i}/{wait_sec}s",
                    vertical="middle",
                )
            )
        )
        time.sleep(1.0)


def on_captcha_after(times: int) -> None:
    """识别验证码开始 回调"""
    if layout.get("session_notice") is None:
        lay_right.split_column(lay_right_content, lay_session_notice)
    lay_session_notice.update(
        Panel(
            f"[yellow]正在识别验证码，第 {times} 次...",
            title="[red]接口风控",
            border_style="yellow",
        )
    )


def on_captcha_before(status: bool, code: str) -> None:
    """验证码识别成功 回调"""
    if status is True:
        lay_session_notice.update(
            Panel(
                f"[green]验证码识别成功：[yellow]{code}[green]，提交正确",
                title="[red]接口风控",
                border_style="green",
            )
        )
        time.sleep(5.0)
        lay_right.unsplit()
    else:
        lay_session_notice.update(
            Panel(
                f"[red]验证码识别成功：[yellow]{code}[red]，提交错误，10S 后重试",
                title="[red]接口风控",
                border_style="red",
            )
        )
        time.sleep(1.0)


def on_face_detection_after(orig_url: str) -> None:
    """人脸识别开始 回调"""
    if layout.get("captcha") is None:
        lay_right.split_column(lay_right_content, lay_session_notice)
    lay_session_notice.update(
        Panel(
            f"[yellow]正在准备人脸识别...\nURL:{orig_url}",
            title="[red]人脸识别",
            border_style="yellow",
        )
    )


def on_face_detection_before(object_id: str, image_path: PathLike) -> None:
    """人脸识别成功 回调"""
    lay_session_notice.update(
        Panel(
            f"[green]人脸识别提交成功：\nobjectId={object_id}\npath={image_path}",
            title="[red]人脸识别",
            border_style="green",
        )
    )
    time.sleep(5.0)
    lay_right.unsplit()


def fuck_task_worker(chap: ChapterContainer) -> None:
    """章节任务点处理实现
    Args:
        chap: 章节容器对象
    """

    def _show_chapter(index: int) -> None:
        chap.set_tui_index(index)
        lay_right_content.update(
            Panel(
                chap,
                title=f"《{chap.name}》章节列表",
                border_style="blue",
            )
        )

    layout.split_row(lay_left, lay_right)
    lay_left.update(
        Panel(
            Align.center(
                "[yellow]正在扫描章节，请稍等...",
                vertical="middle",
            )
        )
    )

    chap.fetch_point_status()
    with Live(layout, console=console) as live:
        # 遍历章节列表
        for index in range(len(chap)):
            _show_chapter(index)
            if chap.is_finished(index) and config.WORK["export"] is False:  # 如果该章节所有任务点做完, 那么就跳过
                logger.info(
                    f"忽略完成任务点 "
                    f"[{chap.chapters[index].label}:{chap.chapters[index].name}(Id.{chap.chapters[index].chapter_id})]"
                )
                time.sleep(0.1)  # 解决强迫症, 故意添加延时, 为展示滚屏效果
                continue
            refresh_flag = True
            # 获取当前章节的所有任务点, 并遍历
            for task_point in chap[index]:
                # 拉取任务卡片 Attachment
                try:
                    task_point.fetch_attachment()
                except ChapterNotOpened:
                    if refresh_flag:
                        chap.refresh_chapter(index-1)
                        refresh_flag = False
                        continue
                    else:
                        lay_left.unsplit()
                        lay_left.update(
                            Panel(
                                Align.center(
                                    f"[red]章节【{chap.chapters[index].label}】《{chap.chapters[index].name}》未开放\n程序无法继续执行！",
                                    vertical="middle",
                                ),
                                border_style="red",
                            )
                        )
                        logger.error("\n-----*未开放章节, 程序异常退出*-----")
                        sys.exit()
                refresh_flag = True
                try:
                    # 开始分类讨论任务点类型
                    # 章节测验类型
                    if isinstance(task_point, PointWorkDto) and (
                        config.WORK_EN or config.WORK["export"] is True
                    ):
                        # 导出作业试题
                        if config.WORK["export"] is True:
                            task_point.parse_attachment()
                            # 保存 json 文件
                            task_point.export(
                                config.EXPORT_PATH / f"work_{task_point.work_id}.json"
                            )

                        # 完成章节测验
                        if config.WORK_EN:
                            if not task_point.parse_attachment():
                                continue
                            task_point.fetch_all()
                            # 实例化解决器
                            resolver = QuestionResolver(
                                exam_dto=task_point,
                                fallback_save=config.WORK["fallback_save"],
                                fallback_fuzzer=config.WORK["fallback_fuzzer"],
                            )
                            # 传递 TUI ctx
                            lay_left.update(resolver)
                            # 开始执行自动接管
                            resolver.execute()
                            # 开始等待
                            task_wait(lay_left, config.WORK_WAIT, f"试题《{task_point.title}》已结束")

                    # 视频类型
                    elif isinstance(task_point, PointVideoDto) and config.VIDEO_EN:
                        if not task_point.parse_attachment():
                            continue
                        # 拉取取任务点数据
                        if not task_point.fetch():
                            continue
                        # 实例化解决器
                        resolver = MediaPlayResolver(
                            media_dto=task_point,
                            speed=config.VIDEO["speed"],
                            report_rate=config.VIDEO["report_rate"],
                        )
                        # 传递 TUI ctx
                        lay_left.update(resolver)
                        # 开始执行自动接管
                        resolver.execute()
                        # 开始等待
                        task_wait(lay_left, config.VIDEO_WAIT, f"视频《{task_point.title}》已结束")

                    # 文档类型
                    elif isinstance(task_point, PointDocumentDto) and config.DOCUMENT_EN:
                        if not task_point.parse_attachment():
                            continue
                        # 实例化解决器
                        resolver = DocumetResolver(document_dto=task_point)
                        # 传递 TUI ctx
                        lay_left.update(resolver)
                        # 开始执行自动接管
                        resolver.execute()

                        # 开始等待
                        task_wait(lay_left, config.DOCUMENT_WAIT, f"文档《{task_point.title}》已结束")

                except (TaskPointError, NotImplementedError) as e:
                    logger.error(f"任务点自动接管执行异常 -> {e.__class__.__name__} {e.__str__()}")

                # 刷新章节任务点状态
                chap.fetch_point_status()
                _show_chapter(index)

        lay_left.unsplit()
        lay_left.update(
            Panel(
                Align.center("[green]该课程已通过", vertical="middle"),
                border_style="green",
            )
        )
        time.sleep(5.0)


def fuck_exam_worker(exam: ExamDto, export: bool = False) -> None:
    """考试处理实现
    Args:
        exam: 考试接口对象
        export: 是否开启导出模式, 默认关闭
    """
    layout.split_row(lay_left, lay_right)
    with Live(layout, console=console) as live:
        # 拉取元数据
        exam.get_meta()
        # 开始考试
        exam.start()
        # 显示考试信息
        lay_right_content.update(Panel(exam, title="考试会话", border_style="blue"))

        # 若开启导出模式, 则不执行自动接管逻辑
        if export is True:
            export_path = config.EXPORT_PATH / f"exam_{exam.exam_id}.json"
            exam.export(export_path)
            live.stop()
            console.print(
                f"[red]请注意，导出后考试已开始计时，时间仅剩 {exam.remain_time_str}！！[/]\n"
                f"[yellow]应尽快使用 本程序 / Web端 / 客户端 作答[/]\n"
                f"[green]试卷导出路径为：{export_path}"
            )
            return

        # 实例化解决器
        resolver = QuestionResolver(
            exam_dto=exam,
            fallback_save=False,  # 考试不存在临时保存特性
            fallback_fuzzer=config.EXAM["fallback_fuzzer"],
            persubmit_delay=config.EXAM["persubmit_delay"],
        )
        # 传递 TUI ctx
        lay_left.update(resolver)

        # 若开启交卷确认功能, 则注册提交回调
        if config.EXAM["confirm_submit"] is True:

            @resolver.reg_confirm_submit_cb
            def confirm(completed_cnt: int, incompleted_cnt: int, mistakes: list, exam_dto: ExamDto) -> bool:
                live.stop()
                if (
                    Prompt.ask(
                        f"答题完毕，完成 [bold green]{completed_cnt}[/] 题，"
                        f"未完成 [bold red]{incompleted_cnt}[/] 题，"
                        f"请确认是否立即交卷",
                        console=console,
                        choices=["y", "n"],
                        default="y",
                    )
                    != "y"
                ):
                    return False
                live.start()
                return True

        # 开始执行自动接管
        resolver.execute()


if __name__ == "__main__":
    dialog.logo(console)
    acc_sessions = sessions_load()
    # 存在至少一个会话存档
    if acc_sessions:
        # 多用户, 允许进行选择
        if config.MULTI_SESS:
            dialog.select_session(console, acc_sessions, api)
        # 单用户, 默认加载第一个会话档
        else:
            ck = ck2dict(acc_sessions[0].ck)
            api.session.ck_load(ck)
            if not api.accinfo():
                console.print("[red]会话失效, 尝试重新登录")
                if not dialog.relogin(console, acc_sessions[0], api):
                    console.print("[red]重登失败，账号或密码错误")
                    sys.exit()
    # 会话存档为空
    else:
        console.print("[yellow]会话存档为空, 请登录账号")
        dialog.login(console, api)
    logger.info("\n-----*任务开始执行*-----")
    logger.info(f"Ver. {__version__}")
    dialog.accinfo(console, api)
    
    while True:
        try:
            # 拉取预先上传的人脸图片
            if config.FETCH_UPLOADED_FACE is True:
                if face_url := api.fetch_face():
                    api.save_face(face_url, config.FACE_PATH)
            # 拉取该账号下所学的课程
            classes = api.fetch_classes()
            # 课程选择交互，支持切换账号
            command = dialog.select_class(console, classes, acc_sessions, api)
            # 切换账号逻辑
            if command == "__switch_account__":
                acc_sessions = sessions_load()
                continue
            # 如果用户选择退出
            if command == "q":
                logger.info("\n-----*用户选择退出程序*-----")
                console.print("[green]感谢使用，再见！")
                break
                
            # 注册验证码 人脸 回调
            api.session.reg_captcha_after(on_captcha_after)
            api.session.reg_captcha_before(on_captcha_before)
            api.session.reg_face_after(on_face_detection_after)
            api.session.reg_face_before(on_face_detection_before)
            # 执行课程任务
            restart_course_select = False
            for task_obj in ClassSelector(command, classes):
                # 章节容器 执行章节任务
                if isinstance(task_obj, ChapterContainer):
                    fuck_task_worker(task_obj)

                # 考试对象 执行考试任务
                elif isinstance(task_obj, ExamDto):
                    fuck_exam_worker(task_obj)

                # 考试列表 进入二级选择交互
                elif isinstance(task_obj, list):
                    exam, export = dialog.select_exam(console, task_obj, api)
                    if exam is None and export is None:
                        restart_course_select = True
                        break  # 跳出 for 循环
                    fuck_exam_worker(exam, export)
            if restart_course_select:
                continue  # 跳回主循环，重新选择课程

        except ExamCompleted as e:
            console.print(f"[yellow]考试已完成：{e}，无需重复操作。")
            logger.info("考试已完成，跳过本次考试。")
            if Prompt.ask(
                "是否继续选择其他课程？",
                console=console,
                choices=["y", "n"],
                default="n"
            ) != "y":
                break
        except Exception as err:
            # 任务异常
            console.print_exception(show_locals=False)
            logger.error("\n-----*程序运行异常退出*-----", exc_info=True)
            if isinstance(err, json.JSONDecodeError):
                console.print("[red]JSON 解析失败, 可能为账号 ck 失效, 请重新登录该账号 (序号+r)")
            else:
                console.print("[bold red]程序运行出现错误, 请截图保存并附上 log 文件在 issue 提交")
            # 询问是否继续
            if Prompt.ask(
                "是否继续选择其他课程？",
                console=console,
                choices=["y", "n"],
                default="n"
            ) != "y":
                break
        except KeyboardInterrupt:
            # 手动中断程序运行
            console.print("[yellow]手动中断程序运行")
            if Prompt.ask(
                "是否继续选择其他课程？",
                console=console,
                choices=["y", "n"],
                default="n"
            ) != "y":
                break
