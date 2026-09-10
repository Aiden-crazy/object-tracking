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

    /**
     * 上传视频/图片。
     * defer=false（默认）：上传即异步跟踪，兼容 Web 端与老版本客户端。
     * defer=true：两段式第一步，只返回任务 + 首帧图片 frameUrl/尺寸/自动识别框 autoBbox，
     *             供小程序把首帧显示出来让用户手指画框。
     */
    @PostMapping("/upload")
    public Result<TrackTask> upload(@RequestAttribute("uid") Long uid,
                                    @RequestParam("file") MultipartFile file,
                                    @RequestParam(value = "bbox", required = false)
                                        String bbox,
                                    @RequestParam(value = "defer", required = false,
                                        defaultValue = "false") boolean defer) {
        return Result.ok(taskService.upload(uid, file, bbox, defer));
    }

    /**
     * 两段式第二步：带上用户框选的目标框开始处理。
     * body 形如 {"bbox":"120,180,60,60"}；bbox 为空或缺省表示用自动识别结果。
     */
    @PostMapping("/{id}/start")
    public Result<TrackTask> start(@PathVariable Long id,
                                   @RequestBody(required = false) Map<String, String> body) {
        String bbox = body == null ? null : body.get("bbox");
        return Result.ok(taskService.start(id, bbox));
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
