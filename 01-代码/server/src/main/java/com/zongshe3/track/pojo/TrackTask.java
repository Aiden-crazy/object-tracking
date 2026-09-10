/*
 * TrackTask.java —— 视觉处理任务实体（对应表 t_task）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 */
package com.zongshe3.track.pojo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class TrackTask {
    private Long id;
    private Long userId;
    /** VIDEO / IMAGE */
    private String mediaType;
    private String fileName;
    /** 原始文件在服务器磁盘上的绝对路径 */
    private String filePath;
    /** 首帧目标框 x,y,w,h，可为空(自动取画面中央) */
    private String bbox;
    /** PENDING / PROCESSING / SUCCESS / FAILED */
    private String status;
    /** 结果视频的 Web 访问路径，如 /files/results/xxx_tracked.mp4 */
    private String resultPath;
    /** 跟踪日志 JSON 的 Web 访问路径 */
    private String logPath;
    /** 跟踪统计信息 JSON 文本 */
    private String statsJson;
    private String errorMsg;
    private LocalDateTime createTime;
    private LocalDateTime finishTime;
    /** 非表字段：冗余用户名（列表展示用） */
    private String username;

    // ---------- 以下均为非表字段：仅用于「上传首帧→画框→开始处理」两段式流程的返回 ----------
    /** 首帧图片的 Web 访问路径，如 /files/frames/12.jpg */
    private String frameUrl;
    /** 视频原始像素宽/高，客户端据此把手势坐标换算回原始像素 */
    private Integer imgWidth;
    private Integer imgHeight;
    /** 后端自动识别的建议目标框 "x,y,w,h"（运动检测结果，可能为空） */
    private String autoBbox;
}
