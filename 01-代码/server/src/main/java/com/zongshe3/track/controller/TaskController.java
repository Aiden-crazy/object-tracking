/*
 * TaskController.java —— 任务上传与查询接口（小程序端）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：
 *   POST /api/task/upload  上传视频/图片 + 可选 bbox，异步触发视觉处理；
 *   GET  /api/task/{id}    查询任务状态（前端轮询）；
 *   GET  /api/task/list    我的任务记录（分页）。
 */
package com.zongshe3.track.controller;

import com.zongshe3.track.common.Result;
import com.zongshe3.track.pojo.TrackTask;
import com.zongshe3.track.service.TaskService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    @PostMapping("/upload")
    public Result<TrackTask> upload(@RequestAttribute("uid") Long uid,
                                    @RequestParam("file") MultipartFile file,
                                    @RequestParam(value = "bbox", required = false)
                                        String bbox) {
        return Result.ok(taskService.upload(uid, file, bbox));
    }

    @GetMapping("/{id}")
    public Result<TrackTask> get(@PathVariable Long id) {
        return Result.ok(taskService.getTask(id));
    }

    @GetMapping("/list")
    public Result<Object> list(@RequestAttribute("uid") Long uid,
                               @RequestParam(defaultValue = "1") int page,
                               @RequestParam(defaultValue = "10") int size) {
        return Result.ok(taskService.myTasks(uid, page, size));
    }
}
